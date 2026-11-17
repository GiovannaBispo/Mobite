"""Cria dados de DEMONSTRAÇÃO: os 10 restaurantes fictícios do protótipo da Giovanna, com auditorias,
avaliações, estrelas, uma pendência resolvida, uma resposta de restaurante assinante e anúncios de exemplo.

    python manage.py dados_demo                # cria (ou recria) tudo
    python manage.py dados_demo --apagar       # remove só o que é de demonstração
    python manage.py dados_demo --trocar-senha # aplica a senha do .env (MOBITE_SENHA_DEMO) às contas de teste

Os restaurantes ficam marcados como "demonstração" e as contas usam o domínio @mobite.example.
"""
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core import regras
from core.models import (LINK_EXEMPLO, Anuncio, Assinatura, Auditoria, AvaliacaoAcessibilidade, AvaliacaoAtendimento, ConsultaDiaria,
                         Confirmacao, Conta, ItemChecklist, Papel, PerfilMobilidade, Reivindicacao, Resposta,
                         RespostaAuditoria, RespostaEstabelecimento, RespostaItem, Restaurante, SituacaoItem,
                         StatusAnalise)

# Do js/dados.js da Giovanna (só restaurantes: 3 nomes de café, lanchonete e padaria foram trocados). s = um dígito por item, na ordem C3 E1 E2 E3 I1 I2 I3 I4 B1 B2:
# 0 = sem informação; 1 a 3 = não atende; 4 e 5 = atende.  d = dias desde a verificação.
RESTAURANTES = [
    ("Sabor & Cia", "5555545555", 19, 4.8, -23.5614, -46.6559, "Rua Exemplo, 100", "11h–23h"),
    ("Sabores do Mundo", "4435432335", 28, 4.6, -23.5575, -46.6620, "Av. Modelo, 250", "12h–22h"),
    ("Bistrô da Praça", "0415320254", 67, 4.5, -23.5650, -46.6500, "Praça Fictícia, 12", "10h–21h"),
    ("Restaurante Brisa", "0551500500", 42, 4.3, -23.5590, -46.6700, "Rua das Ideias, 45", "8h–19h"),
    ("Grão & Prosa", "4544455450", 10, 4.7, -23.5530, -46.6490, "Rua do Teste, 77", "7h–20h"),
    ("Prato Express", "1215120100", 86, 4.0, -23.5700, -46.6450, "Rua Protótipo, 78", "9h–22h"),
    ("Burger Largo", "5435335455", 35, 4.4, -23.5480, -46.6600, "Av. Demonstração, 300", "11h–23h"),
    ("Cozinha Pão Nosso", "3255453554", 22, 4.4, -23.5540, -46.6580, "Rua Teste, 9", "6h–20h"),
    ("Forno da Vila", "0000000000", None, 0, -23.5660, -46.6650, "Rua da Vila, 21", "6h–19h"),
    ("Cantina Nonna Rosa", "5525555255", 15, 4.9, -23.5600, -46.6420, "Rua Imaginária, 5", "12h–23h"),
]
ORDEM = ["C3", "E1", "E2", "E3", "I1", "I2", "I3", "I4", "B1", "B2"]


def resposta_crua(item, atende):
    """O que a pessoa marcaria na pergunta (numa pergunta invertida, "Sim" é o que não atende)."""
    if item.invertida:
        return Resposta.NAO if atende == Resposta.SIM else Resposta.SIM
    return atende


def estrelas_para(nota, n=5):
    total = round(nota * n)
    base = [total // n] * n
    for i in range(total % n):
        base[i] += 1
    return [max(1, min(5, x)) for x in base]


class Command(BaseCommand):
    help = "Cria ou apaga os dados de demonstração (restaurantes fictícios da Giovanna)."

    def add_arguments(self, parser):
        parser.add_argument("--apagar", action="store_true")
        parser.add_argument("--trocar-senha", action="store_true",
                            help="Só troca a senha das contas de teste (menos a da equipe) pela do .env")

    def apagar(self):
        Restaurante.objects.filter(demonstracao=True).delete()
        Conta.objects.filter(email__endswith="@mobite.example").delete()
        Anuncio.objects.filter(link__startswith=LINK_EXEMPLO).delete()

    def conta(self, email, apelido="", publico=False, papel=Papel.MEMBRO):
        c = Conta.objects.create_user(email=email, password=settings.MOBITE_SENHA_DEMO, apelido=apelido, aparecer_publicamente=publico,
                                      papel=papel)
        EmailAddress.objects.create(user=c, email=email, verified=True, primary=True)
        return c

    @transaction.atomic
    def handle(self, *args, apagar=False, trocar_senha=False, **kwargs):
        if trocar_senha:  # a conta da equipe tem senha própria, escolhida na instalação
            contas = Conta.objects.filter(email__endswith="@mobite.example").exclude(email="equipe@mobite.example")
            for c in contas:
                c.set_password(settings.MOBITE_SENHA_DEMO)
                c.save(update_fields=["password"])
            self.stdout.write(f"   Senha das contas de teste aplicada ({contas.count()} contas).")
            return
        self.apagar()
        if apagar:
            self.stdout.write(self.style.SUCCESS("Dados de demonstração apagados."))
            return
        agora = timezone.now()
        itens = {i.codigo: i for i in ItemChecklist.objects.all()}
        equipe = self.conta("equipe@mobite.example", "Equipe MoBite", papel=Papel.EQUIPE_MOBITE)
        ana = self.conta("mobite@mobite.example", "Avaliador de teste", publico=True)
        bruno = self.conta("avaliador1@mobite.example")
        carla = self.conta("avaliador2@mobite.example")
        dono = self.conta("restaurante@mobite.example", "Responsável Sabores do Mundo")
        avaliadores = [ana, bruno, carla]

        criados = []
        for nome, s, dias, nota, lat, lng, end, hor in RESTAURANTES:
            r = Restaurante.objects.create(nome=nome, latitude=lat, longitude=lng, endereco=end,
                                           horario=hor, demonstracao=True)
            criados.append(r)
            if dias is not None:
                aud = Auditoria.objects.create(restaurante=r, autor=equipe, data=agora - timedelta(days=dias),
                                               observacoes="Visita de demonstração.")
                for cod, dig in zip(ORDEM, s):
                    if dig != "0":
                        atende = Resposta.SIM if int(dig) >= 4 else Resposta.NAO
                        RespostaAuditoria.objects.create(auditoria=aud, item=itens[cod],
                                                         resposta=resposta_crua(itens[cod], atende))
            for i, estrelas in enumerate(estrelas_para(nota) if nota else []):
                AvaliacaoAtendimento.objects.create(restaurante=r, autor=avaliadores[i % 3], estrelas=estrelas,
                                                    data=agora - timedelta(days=(dias or 30) + i))
            regras.recalcular(r)

        sabor, sabores, nonna = criados[0], criados[1], criados[-1]

        # O avaliador de teste confirma itens e avalia vários lugares (vira "Colaborador" e aparece com apelido).
        for r in criados[:6]:
            av = AvaliacaoAcessibilidade.objects.create(autor=ana, restaurante=r, data=agora - timedelta(days=3))
            for cod in ("E2", "I1"):
                sit = SituacaoItem.objects.get(restaurante=r, item=itens[cod])
                if sit.tem_informacao:
                    RespostaItem.objects.create(avaliacao=av, item=itens[cod],
                                                resposta=resposta_crua(itens[cod], sit.resposta))
            if not av.respostas.exists():
                RespostaItem.objects.create(avaliacao=av, item=itens["E2"], resposta=Resposta.NAO_SEI)
            regras.recalcular(r)
        for cod in ("E1", "B1"):
            Confirmacao.objects.create(situacao=SituacaoItem.objects.get(restaurante=sabor, item=itens[cod]),
                                       autor=bruno, data=agora - timedelta(days=2))
        regras.recalcular(sabor)

        # Item em dúvida: a porta larga do Sabor & Cia foi confirmada pela equipe e pelo avaliador de teste,
        # e uma pessoa sozinha disse que não. Fica "em dúvida" até mais alguém responder.
        av = AvaliacaoAcessibilidade.objects.create(autor=carla, restaurante=sabor, data=agora - timedelta(days=1))
        RespostaItem.objects.create(avaliacao=av, item=itens["E2"], resposta=Resposta.NAO)
        regras.recalcular(sabor)

        # Pendência resolvida: a Cantina só tinha cadeira com braço; uma nova visita viu cadeiras soltas sem braço.
        av = AvaliacaoAcessibilidade.objects.create(autor=carla, restaurante=nonna, data=agora - timedelta(days=4))
        RespostaItem.objects.create(avaliacao=av, item=itens["I4"], resposta=Resposta.SIM)
        regras.recalcular(nonna)

        # Restaurante assinante com resposta a uma pendência aberta.
        Reivindicacao.objects.create(conta=dono, restaurante=sabores, cnpj="11.222.333/0001-81",
                                     status=StatusAnalise.APROVADA, verificada_por=equipe)
        Assinatura.objects.create(restaurante=sabores, data_inicio=timezone.localdate() - timedelta(days=5),
                                  data_fim=timezone.localdate() + timedelta(days=25), ativada_por=equipe)
        RespostaEstabelecimento.objects.create(
            autor=dono, situacao=SituacaoItem.objects.get(restaurante=sabores, item=itens["I3"]),
            texto="O salão de cima ainda tem só escada. Estamos orçando uma plataforma elevatória para o 1º semestre.",
            data=agora - timedelta(days=6))

        # Consultas de exemplo nos últimos 12 dias, para o "pessoas ajudadas" não começar em zero.
        hoje = timezone.localdate()
        for r in criados:
            for d in range(12):
                ConsultaDiaria.objects.create(restaurante=r, data=hoje - timedelta(days=d), total=(r.pk * 7 + d * 3) % 9 + 1)

        # Anúncios de exemplo: dois por perfil e um geral.
        perfis = {p.codigo: p for p in PerfilMobilidade.objects.all()}
        for titulo, alvo in [
            ("Oficina de cadeiras de rodas (exemplo): manutenção no bairro", ["cadeira"]),
            ("Loja de carrinhos de bebê (exemplo)", ["carrinho"]),
            ("Feira gastronômica do bairro (exemplo): sábado, na praça", []),
        ]:
            a = Anuncio.objects.create(titulo=titulo, link=LINK_EXEMPLO, cadastrado_por=equipe)
            a.perfis.set([perfis[c] for c in alvo])

        self.stdout.write(self.style.SUCCESS(f"{len(criados)} restaurantes de demonstração criados."))
        for linha in [f"Contas de teste, todas com a senha {settings.MOBITE_SENHA_DEMO}:",
                      "  mobite@mobite.example       avaliador que aparece com apelido e selo",
                      "  equipe@mobite.example       painel da equipe em /equipe/",
                      "  restaurante@mobite.example  responsável pelo Sabores do Mundo, com assinatura ativa",
                      "  avaliador1@ e avaliador2@mobite.example  avaliadores anônimos"]:
            self.stdout.write(linha)
