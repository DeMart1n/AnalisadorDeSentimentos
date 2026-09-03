import json
from pathlib import Path

from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .classificador import classificar_conversas
from .importacao import ErroDeImportacao, importar
from .indicadores import indicadores
from .models import USUARIO, Conversa, Mensagem

METRICAS = Path(__file__).resolve().parents[1] / "models" / "metricas.json"


@csrf_exempt  # ponytail: app local sem autenticação nem sessão. Reativar CSRF quando entrar auth ou dado real de empresa.
@require_POST
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

    ids = list(Conversa.objects.filter(fonte=fonte).values_list("id", flat=True))
    classificadas = classificar_conversas(ids)
    return JsonResponse({
        "fonte": fonte,
        "conversas": n_conversas,
        "mensagens": n_mensagens,
        "mensagens_classificadas": classificadas,
    })


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
