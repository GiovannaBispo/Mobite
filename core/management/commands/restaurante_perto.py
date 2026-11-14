"""Cria um restaurante FICTÍCIO perto de um CEP, para testar a distância e a foto (aceita só a até 150 m).

    python manage.py restaurante_perto --cep 08526130
    python manage.py restaurante_perto --cep 08526130 --nome "Cantina do Teste" --metros 60

Fica marcado como "demonstração": o `dados_demo` (ou `dados_demo --apagar`) também o remove.
O CEP vira posição pelo ViaCEP e pelo OpenStreetMap (Nominatim), como no app.
"""
import json
import math
import urllib.parse
import urllib.request
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core import regras
from core.models import (Auditoria, AvaliacaoAtendimento, ItemChecklist, Resposta, RespostaAuditoria, Restaurante,
                         distancia_metros)

UA = {"User-Agent": "MoBite-projeto-academico/1.0"}
# Respostas variadas, para cada perfil ver um resultado diferente (item: atende?)
SITUACAO = {"C3": Resposta.NAO, "E1": Resposta.SIM, "E2": Resposta.SIM, "E3": Resposta.SIM, "I1": Resposta.SIM,
            "I2": Resposta.NAO, "I3": Resposta.SIM, "I4": Resposta.SIM, "B1": Resposta.NAO, "B2": Resposta.SIM}


def buscar(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


class Command(BaseCommand):
    help = "Cria um restaurante fictício a poucos metros de um CEP (para testar distância e foto)."

    def add_arguments(self, parser):
        parser.add_argument("--cep", required=True)
        parser.add_argument("--nome", default="Restaurante Perto de Casa")
        parser.add_argument("--metros", type=int, default=80, help="distância do ponto do CEP (padrão 80 m)")

    @transaction.atomic
    def handle(self, *args, cep, nome, metros, **kwargs):
        n = "".join(c for c in cep if c.isdigit())
        if len(n) != 8:
            raise CommandError("O CEP precisa ter 8 números.")
        end = buscar(f"https://viacep.com.br/ws/{n}/json/")
        if end.get("erro"):
            raise CommandError("CEP não encontrado.")
        q = urllib.parse.urlencode({"street": end["logradouro"], "city": end["localidade"], "state": end["uf"],
                                    "country": "Brasil", "format": "json", "limit": 1})
        achados = buscar(f"https://nominatim.openstreetmap.org/search?{q}")
        if not achados:
            raise CommandError("Achamos o CEP, mas não a rua no mapa.")
        lat0, lon0 = float(achados[0]["lat"]), float(achados[0]["lon"])
        # desloca para nordeste, a "metros" de distância
        d = metros / math.sqrt(2)
        lat = lat0 + d / 111_320
        lon = lon0 + d / (111_320 * math.cos(math.radians(lat0)))

        r = Restaurante.objects.create(nome=nome, endereco=f"{end['logradouro']} (fictício), {end['bairro']}",
                                       latitude=lat, longitude=lon, horario="11h–22h", demonstracao=True)
        aud = Auditoria.objects.create(restaurante=r, data=timezone.now() - timedelta(days=5),
                                       observacoes="Restaurante fictício para teste perto de um CEP.")
        itens = {i.codigo: i for i in ItemChecklist.objects.all()}
        for cod, atende in SITUACAO.items():
            item = itens[cod]
            resposta = (Resposta.NAO if atende == Resposta.SIM else Resposta.SIM) if item.invertida else atende
            RespostaAuditoria.objects.create(auditoria=aud, item=item, resposta=resposta)
        for estrelas in (5, 4, 5):
            AvaliacaoAtendimento.objects.create(restaurante=r, estrelas=estrelas)
        regras.recalcular(r)
        self.stdout.write(self.style.SUCCESS(
            f"“{nome}” criado em {end['logradouro']}, {end['bairro']}, {end['localidade']} "
            f"(a {distancia_metros(lat0, lon0, lat, lon):.0f} m do ponto do CEP no mapa)."))
        self.stdout.write("Se a foto for recusada por distância, ajuste latitude e longitude no painel /equipe/.")
