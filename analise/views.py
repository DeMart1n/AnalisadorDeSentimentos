import json
from itertools import batched
from pathlib import Path

from celery import group
from celery.result import GroupResult
from kombu.exceptions import OperationalError

from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .classificador import verificar
from .importacao import ErroDeImportacao, importar
from .indicadores import indicadores
from .modelos import ModeloNaoTreinado
from .models import USUARIO, Conversa, Mensagem, Users
from .dtos.user.create_user_dto import CreateUserDTO, UserOutputDTO
from .dtos.user.login_dto import LoginUserDTO, LoginOutputDTO
from .dtos.user.refresh_token_dto import RefreshTokenDTO, RefreshTokenOutputDTO
from .dtos.analise_dto import AnalisarConversasDTO, AnalisarConversasOutputDTO
from django.contrib.auth.hashers import make_password, check_password
from .auth import token_generator, decode_refresh_token, jwt_required, admin_required
from .tasks import classificar_lote

METRICAS = Path(__file__).resolve().parents[1] / "models" / "metricas.json"
OPENAPI_PATH = Path(__file__).resolve().parents[1] / "docs" / "openapi.yaml"
LOTE_CONVERSAS = 50  # conversas por tarefa: unidade que os workers dividem entre si

@csrf_exempt
@require_POST
def create(request):
    try:
        if not request.body:
            return JsonResponse({"erro": "Corpo da requisição vazio."}, status=400)
        data = json.loads(request.body)
        dto = CreateUserDTO.from_dict(data)
        user = Users.objects.create(
            name=dto.name,
            email=dto.email,
            password=make_password(dto.password),
            role=dto.role,
        )
        return JsonResponse(UserOutputDTO.from_model(user).to_dict(), status=201)
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)
    except ValueError as e:
        return JsonResponse({"erro": e.args[0]}, status=400)

@csrf_exempt
@require_POST
def login(request):
    try:
        if not request.body:
            return JsonResponse({"erro": "Corpo da requisição vazio."}, status=400)
        data = json.loads(request.body)
        dto = LoginUserDTO.from_dict(data)
        user = Users.objects.filter(email=dto.email).first()
        if not user or not check_password(dto.password, user.password):
            return JsonResponse({"erro": "E-mail ou senha inválidos."}, status=401)
        access_token, refresh_token = token_generator(user)
        return JsonResponse(
            LoginOutputDTO.from_user(user, access_token, refresh_token).to_dict(),
            status=200
        )
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)
    except ValueError as e:
        return JsonResponse({"erro": e.args[0]}, status=400)

@csrf_exempt
@require_POST
def refresh(request):
    try:
        if not request.body:
            return JsonResponse({"erro": "Corpo da requisição vazio."}, status=400)
        data = json.loads(request.body)
        dto = RefreshTokenDTO.from_dict(data)

        payload, erro = decode_refresh_token(dto.refresh_token)
        if erro:
            return JsonResponse({"erro": erro}, status=401)

        user = Users.objects.filter(id=payload.get("user_id")).first()
        if not user:
            return JsonResponse({"erro": "Usuário não encontrado."}, status=404)

        access_token, new_refresh_token = token_generator(user)
        output = RefreshTokenOutputDTO(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )
        return JsonResponse(output.to_dict(), status=200)
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)
    except ValueError as e:
        return JsonResponse({"erro": e.args[0]}, status=400)


@csrf_exempt  # ponytail: app local sem autenticação nem sessão. Reativar CSRF quando entrar auth ou dado real de empresa.
@require_POST
@admin_required
def upload(request):
    arquivo = request.FILES.get("arquivo")
    if not arquivo:
        return JsonResponse({"erro": "envie o arquivo no campo 'arquivo'"}, status=400)
    fonte = request.POST.get("fonte") or Path(arquivo.name).stem
    formato = "json" if arquivo.name.lower().endswith(".json") else "csv"
    try:
        conteudo = arquivo.read().decode("utf-8")
    except UnicodeDecodeError:
        return JsonResponse({"erro": "arquivo precisa estar em UTF-8"}, status=400)

    try:
        n_conversas, n_mensagens = importar(conteudo, fonte, formato)
    except ErroDeImportacao as e:
        return JsonResponse({"erro": "arquivo inválido", "detalhes": e.erros[:20]}, status=400)
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)

    return JsonResponse({
        "fonte": fonte,
        "conversas": n_conversas,
        "mensagens": n_mensagens,
        "status": "importado",
    }, status=201)


@csrf_exempt
@require_POST
@jwt_required
def analisar(request):
    try:
        if not request.body:
            return JsonResponse({"erro": "Corpo da requisição vazio. Envie um JSON com 'fonte' ou 'conversa_ids'."}, status=400)
        data = json.loads(request.body)
        dto = AnalisarConversasDTO.from_dict(data)

        qs = Conversa.objects.all()
        if dto.fonte:
            qs = qs.filter(fonte=dto.fonte)
        if dto.conversa_ids:
            qs = qs.filter(id__in=dto.conversa_ids)

        verificar(dto.modelo)
        # só ids trafegam: o texto das mensagens é lido pelo worker, lote a lote
        ids = qs.order_by("id").values_list("id", flat=True).iterator(chunk_size=2000)
        lotes = [list(lote) for lote in batched(ids, LOTE_CONVERSAS)]
        if not lotes:
            return JsonResponse({"erro": "Nenhuma conversa encontrada para os critérios informados."}, status=404)

        tarefa = group(
            classificar_lote.s(lote, dto.modelo, dto.apenas_nao_classificadas) for lote in lotes
        ).apply_async()
        tarefa.save()  # sem isso GroupResult.restore não acha o grupo no status

        output = AnalisarConversasOutputDTO(
            tarefa_id=tarefa.id,
            fonte=dto.fonte,
            total_conversas=sum(map(len, lotes)),
            lotes=len(lotes),
            modelo_utilizado=dto.modelo,
        )
        return JsonResponse(output.to_dict(), status=202)

    except ModeloNaoTreinado as e:
        return JsonResponse({"erro": str(e)}, status=503)
    except OperationalError:
        return JsonResponse({"erro": "Fila de classificação indisponível. Tente novamente em instantes."}, status=503)
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)
    except ValueError as e:
        return JsonResponse({"erro": e.args[0]}, status=400)


@require_GET
@jwt_required
def status_analise(request, tarefa_id):
    tarefa = GroupResult.restore(tarefa_id)
    if tarefa is None:
        return JsonResponse({"erro": "tarefa não encontrada ou expirada"}, status=404)
    falhas = [r for r in tarefa.results if r.failed()]
    concluidos = [r for r in tarefa.results if r.successful()]
    if len(falhas) + len(concluidos) < len(tarefa.results):
        estado = "processando"  # mesmo com falha: "erro" antes da hora faria o cliente reenfileirar lotes ainda rodando
    elif falhas:
        estado = "erro"
    else:
        estado = "concluido"
    return JsonResponse({
        "tarefa_id": tarefa.id,
        "estado": estado,
        "lotes": len(tarefa.results),
        "lotes_concluidos": len(concluidos),
        "lotes_falhos": len(falhas),
        "mensagens_classificadas": sum(r.result for r in concluidos),
        "erro": str(falhas[0].result) if falhas else None,
    })


@require_GET
def conversas(request):
    qs = Conversa.objects.all()
    if fonte := request.GET.get("fonte"):
        qs = qs.filter(fonte=fonte)
    try:
        limite = min(int(request.GET.get("limite", 100)), 500)
    except ValueError:
        limite = 0
    if limite < 1:
        return JsonResponse({"erro": "limite deve ser um inteiro positivo"}, status=400)

    itens = []
    for conversa in qs.prefetch_related("mensagens")[:limite]:
        rotulos = [m.rotulo_pred for m in conversa.mensagens.all() if m.autor == USUARIO]
        itens.append({
            "id": conversa.id,
            "origem_id": conversa.origem_id,
            "fonte": conversa.fonte,
            "indicadores": indicadores(rotulos),
        })
    return JsonResponse({"total": qs.count(), "conversas": itens})


@require_GET
def conversa(request, conversa_id):
    try:
        obj = Conversa.objects.prefetch_related("mensagens").get(pk=conversa_id)
    except Conversa.DoesNotExist:
        return JsonResponse({"erro": "conversa não encontrada"}, status=404)
    mensagens = list(obj.mensagens.all())
    return JsonResponse({
        "id": obj.id,
        "origem_id": obj.origem_id,
        "fonte": obj.fonte,
        "indicadores": indicadores([m.rotulo_pred for m in mensagens if m.autor == USUARIO]),
        "mensagens": [
            {"ordem": m.ordem, "autor": m.autor, "texto": m.texto,
             "rotulo": m.rotulo_pred, "score": m.score, "rotulo_real": m.rotulo_real}
            for m in mensagens
        ],
    })


@require_GET
def metricas(request):
    distribuicao = dict(
        Mensagem.objects.filter(autor=USUARIO, rotulo_pred__isnull=False)
        .values_list("rotulo_pred")
        .annotate(n=Count("id"))
    )
    # a comparação entre modelos vem do último `manage.py avaliar --salvar`
    modelos = json.loads(METRICAS.read_text()) if METRICAS.exists() else None
    return JsonResponse({
        "distribuicao": distribuicao,
        "total_conversas": Conversa.objects.count(),
        "modelos": modelos,
    })


# DOCUMENTACAO
def _obter_openapi_conteudo():
    if OPENAPI_PATH.exists():
        return OPENAPI_PATH.read_text(encoding="utf-8")
    fallback = Path("/app/docs/openapi.yaml")
    if fallback.exists():
        return fallback.read_text(encoding="utf-8")
    return None

@require_GET
def openapi_spec(request):
    conteudo = _obter_openapi_conteudo()
    if not conteudo:
        return JsonResponse({"erro": "Arquivo de especificação OpenAPI não encontrado."}, status=404)
    return HttpResponse(
        conteudo,
        content_type="text/yaml; charset=utf-8",
    )

@require_GET
def docs(request):
    html = """<!doctype html>
<html>
  <head>
    <title>API Reference — Analisador de Sentimentos</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body {
        margin: 0;
        padding: 0;
      }
    </style>
  </head>
  <body>
    <div id="app"></div>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    <script>
      Scalar.createApiReference('#app', {
        url: '/api/openapi.yaml',
        theme: 'purple',
        layout: 'modern',
        darkMode: true
      })
    </script>
  </body>
</html>"""
    return HttpResponse(html, content_type="text/html; charset=utf-8")