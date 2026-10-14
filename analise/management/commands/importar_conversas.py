import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analise.importacao import ErroDeImportacao, importar


class Command(BaseCommand):
    help = "Importa conversas de um CSV/JSON no esquema do projeto"

    def add_arguments(self, parser):
        parser.add_argument("arquivo", type=Path)
        parser.add_argument("--fonte", required=True, help="identificador da base, ex: b2w-reviews")

    def handle(self, *args, **opts):
        arquivo = opts["arquivo"]
        formato = "json" if arquivo.suffix.lower() == ".json" else "csv"
        try:
            conteudo = arquivo.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"arquivo não encontrado: {arquivo}")
        except UnicodeDecodeError:
            raise CommandError("arquivo precisa estar em UTF-8")
        try:
            conversas, mensagens = importar(conteudo, opts["fonte"], formato)
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON inválido: {e}")
        except ErroDeImportacao as e:
            for erro in e.erros[:20]:
                self.stderr.write(erro)
            if len(e.erros) > 20:
                self.stderr.write(f"... e mais {len(e.erros) - 20} erro(s)")
            raise CommandError("nada foi importado")
        self.stdout.write(self.style.SUCCESS(f"{conversas} conversa(s), {mensagens} mensagem(ns)"))
