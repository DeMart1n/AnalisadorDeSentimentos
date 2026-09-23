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
