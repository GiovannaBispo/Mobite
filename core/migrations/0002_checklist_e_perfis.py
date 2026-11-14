"""Dados fixos do MoBite: os 10 itens do checklist (ABNT NBR 9050, conferíveis a olho),
os 5 perfis de mobilidade e a matriz BLOQUEIA/IMPORTA."""
from django.db import migrations

ITENS = [
    # codigo, zona, nome, pergunta, ajuda, invertida
    ("C3", "CHEGADA", "Vaga reservada", "Tem vaga reservada perto, com espaço livre ao lado?",
     "O espaço ao lado é onde a pessoa passa do carro para a cadeira.", False),
    ("E1", "ENTRADA", "Entrada sem degrau", "A entrada tem degrau ou escada?",
     "Olhe a porta principal a partir da calçada.", True),
    ("E2", "ENTRADA", "Porta larga", "A porta é larga o bastante para uma cadeira de rodas?",
     "Cerca de 80 cm, quase o dobro de um ombro.", False),
    ("E3", "ENTRADA", "Corrimão", "Há corrimão ou apoio na rampa ou no degrau?",
     "É o que segura quem usa bengala ou muleta.", False),
    ("I1", "INTERIOR", "Circulação entre mesas", "Dá para circular entre as mesas com cadeira ou carrinho?",
     "Olhe o corredor entre as mesas ocupadas.", False),
    ("I2", "INTERIOR", "Mesa que encaixa", "A cadeira de rodas encaixa embaixo da mesa?",
     "Mesa de pé central encaixa; pé nas quinas trava.", False),
    ("I3", "INTERIOR", "Tudo no térreo", "O atendimento é todo no térreo, sem escada obrigatória?",
     "Salão, caixa e banheiro no mesmo andar da entrada.", False),
    ("I4", "INTERIOR", "Cadeira sem braço", "Há mesa com cadeira solta e sem braço?",
     "E não só banco fixo preso na parede.", False),
    ("B1", "BANHEIRO", "Banheiro acessível", "Tem banheiro acessível, com barras de apoio?",
     "Box maior, com barras de ferro ao lado do vaso.", False),
    ("B2", "BANHEIRO", "Banheiro sem escada", "Dá para chegar ao banheiro sem escada?",
     "Sem degrau, sem subsolo e sem andar de cima.", False),
]

B, I = "BLOQUEIA", "IMPORTA"
PERFIS = [
    # codigo, nome, descricao (escrita como necessidade), pesos
    ("cadeira", "Cadeira de rodas", "Uso cadeira de rodas",
     {"E1": B, "E2": B, "I3": B, "I1": I, "I2": I, "B1": I, "B2": I, "C3": I}),
    ("muleta", "Muleta, andador ou bengala", "Uso muleta, andador ou bengala",
     {"E1": I, "E3": I, "I1": I, "I3": I, "B1": I, "B2": I, "C3": I}),
    ("carrinho", "Carrinho de bebê", "Estou com carrinho de bebê",
     {"E1": B, "E2": I, "I1": I, "I3": I, "C3": I}),
    ("escada", "Dificuldade com escada", "Tenho dificuldade com escada",
     {"I3": B, "E1": I, "E3": I, "B1": I, "B2": I, "C3": I}),
    ("assento", "Assento largo ou sem braço", "Preciso de assento largo ou sem braço",
     {"I4": B, "E1": I, "I1": I, "I3": I, "B1": I, "B2": I, "C3": I}),
]


def criar(apps, schema_editor):
    Item = apps.get_model("core", "ItemChecklist")
    Perfil = apps.get_model("core", "PerfilMobilidade")
    PesoItemPerfil = apps.get_model("core", "PesoItemPerfil")
    itens = {}
    for ordem, (codigo, zona, nome, pergunta, ajuda, invertida) in enumerate(ITENS, 1):
        itens[codigo], _ = Item.objects.update_or_create(codigo=codigo, defaults=dict(
            zona=zona, nome=nome, pergunta=pergunta, ajuda=ajuda, invertida=invertida, ordem=ordem))
    for ordem, (codigo, nome, descricao, pesos) in enumerate(PERFIS, 1):
        perfil, _ = Perfil.objects.update_or_create(codigo=codigo, defaults=dict(
            nome=nome, descricao=descricao, ordem=ordem))
        for cod_item, peso in pesos.items():
            PesoItemPerfil.objects.update_or_create(perfil=perfil, item=itens[cod_item], defaults={"peso": peso})


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(criar, migrations.RunPython.noop)]
