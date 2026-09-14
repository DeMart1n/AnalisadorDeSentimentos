import json
from pathlib import Path

from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .classificador import classificar_conversas
from .importacao import ErroDeImportacao, importar
from .indicadores import indicadores
from .models import USUARIO, Conversa, Mensagem, Users
from .dtos.create_user_dto import CreateUserDTO, UserOutputDTO
from .dtos.login_dto import LoginUserDTO, LoginOutputDTO
from .dtos.analise_dto import AnalisarConversasDTO, AnalisarConversasOutputDTO
from django.contrib.auth.hashers import make_password, check_password
from .auth import token_generator, jwt_required, admin_required

METRICAS = Path(__file__).resolve().parents[1] / "models" / "metricas.json"


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
    except ValueError as e:
        return JsonResponse({"erro": e.args[0]}, status=400)
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)

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
    except ValueError as e:
        return JsonResponse({"erro": e.args[0]}, status=400)
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)

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

        ids = list(qs.values_list("id", flat=True))
        if not ids:
            return JsonResponse({"erro": "Nenhuma conversa encontrada para os critérios informados."}, status=404)

        classificadas = classificar_conversas(
            ids=ids,
            nome=dto.modelo,
            apenas_nao_classificadas=dto.apenas_nao_classificadas,
        )

        output = AnalisarConversasOutputDTO(
            fonte=dto.fonte,
            total_conversas=len(ids),
            mensagens_classificadas=classificadas,
            modelo_utilizado=dto.modelo,
        )
        return JsonResponse(output.to_dict(), status=200)

    except ValueError as e:
        return JsonResponse({"erro": e.args[0]}, status=400)
    except json.JSONDecodeError as e:
        return JsonResponse({"erro": f"JSON inválido: {e}"}, status=400)


@require_GET
def conversas(request):
    qs = Conversa.objects.all()
    if fonte := request.GET.get("fonte"):
        qs = qs.filter(fonte=fonte)
    limite = min(int(request.GET.get("limite", 100)), 500)

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
