from django.db import models

POSITIVO, NEGATIVO, NEUTRO = "positivo", "negativo", "neutro"
ROTULOS = [(POSITIVO, "Positivo"), (NEGATIVO, "Negativo"), (NEUTRO, "Neutro")]

USUARIO, ATENDENTE, SISTEMA = "usuario", "atendente", "sistema"
AUTORES = [(USUARIO, "Usuário"), (ATENDENTE, "Atendente"), (SISTEMA, "Sistema")]


class Conversa(models.Model):
    origem_id = models.CharField(max_length=120)
    fonte = models.CharField(max_length=60)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        # mesma conversa reimportada da mesma fonte é atualizada, não duplicada
        constraints = [
            models.UniqueConstraint(fields=["fonte", "origem_id"], name="conversa_unica_por_fonte")
        ]

    def __str__(self):
        return f"{self.fonte}:{self.origem_id}"


class Mensagem(models.Model):
    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    ordem = models.PositiveIntegerField()
    autor = models.CharField(max_length=10, choices=AUTORES)
    texto = models.TextField()
    enviada_em = models.DateTimeField(null=True, blank=True)
    rotulo_pred = models.CharField(max_length=10, choices=ROTULOS, null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    rotulo_real = models.CharField(max_length=10, choices=ROTULOS, null=True, blank=True)

    class Meta:
        ordering = ["conversa_id", "ordem"]
        constraints = [
            models.UniqueConstraint(fields=["conversa", "ordem"], name="ordem_unica_por_conversa")
        ]

    def __str__(self):
        return f"{self.conversa_id}#{self.ordem} {self.autor}"

EMOCOES = ["alegria", "raiva", "tristeza", "medo", "surpresa", "nojo"]  # Ekman; neutro = nenhuma
HUMANO, LLM, ORIGINAL_DATASET = "humano", "llm", "original_dataset"
ORIGENS_ROTULO = [(HUMANO, "Humano"), (LLM, "LLM"), (ORIGINAL_DATASET, "Dataset original")]


class RotuloEmocao(models.Model):
    """Rótulo multi-rótulo de emoção de UMA mensagem, separado da polaridade.

    Uma mensagem pode ter vários (dois anotadores, duas passadas de LLM): é daí que sai o Kappa.
    Fonte, texto, autor e ordem vêm da Mensagem/Conversa; texto já anonimizado na importação.
    """

    # PROTECT: reimportar conversa apaga as mensagens; anotação humana não pode sumir junto
    mensagem = models.ForeignKey(Mensagem, on_delete=models.PROTECT, related_name="rotulos_emocao")
    origem = models.CharField(max_length=20, choices=ORIGENS_ROTULO)
    anotador = models.CharField(max_length=60, blank=True, help_text="pessoa, ou modelo+prompt da LLM")
    alegria = models.BooleanField(default=False)
    raiva = models.BooleanField(default=False)
    tristeza = models.BooleanField(default=False)
    medo = models.BooleanField(default=False)
    surpresa = models.BooleanField(default=False)
    nojo = models.BooleanField(default=False)
    intensidades = models.JSONField(null=True, blank=True, help_text='opcional, 0-3: {"raiva": 2}')
    semente_id = models.CharField(max_length=60, blank=True, help_text="só para dados sintéticos")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mensagem", "origem", "anotador"], name="rotulo_emocao_unico")
        ]

    @property
    def emocoes(self):
        return [e for e in EMOCOES if getattr(self, e)]

    def __str__(self):
        return f"{self.mensagem} {self.origem}:{self.anotador} {self.emocoes or ['neutro']}"


# Users model
ROLE_ADMIN = "ADMIN"
ROLE_USER = "USER"
ROLE_CHOICES = [
    (ROLE_ADMIN, "Admin"),
    (ROLE_USER, "User"),
]

class Users(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, unique=True, db_index=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.role}"
