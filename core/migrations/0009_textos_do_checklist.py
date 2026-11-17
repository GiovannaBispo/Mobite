"""Textos do checklist revistos com casos que aparecem na rua:
- E3: entrada plana não tem corrimão porque não precisa; antes isso virava "não atende" para muleta e escada.
- I2: a dica do pé central não vale sempre (base larga também trava); o que importa é o vão livre embaixo do tampo.
- B1 e B2: lugar sem banheiro para clientes, ou com banheiro só de funcionários, é "Não".
- I4: banco ou cadeira presos no chão (comum em lanchonete) não contam como cadeira solta.
- I1 e I3: basta chegar a algumas mesas e a um salão sem escada.
As respostas já dadas ficam como estão."""
from django.db import migrations

TEXTOS = {
    "E3": {"nome": "Corrimão ou entrada plana", "pergunta": "Se a entrada tem degrau ou rampa, tem corrimão?",
           "ajuda": "Se não tem degrau nem rampa, responda Sim."},
    "I1": {"ajuda": "Olhe o corredor entre as mesas ocupadas. Basta dar para chegar a algumas mesas."},
    "I2": {"ajuda": "Precisa sobrar espaço embaixo do tampo para os joelhos e os pés, sem pé da mesa no caminho. "
                    "Basta uma mesa assim."},
    "I3": {"ajuda": "Pode ser tudo no térreo ou com elevador ou rampa que o cliente pode usar. "
                    "Se tem mais de um salão, basta um sem escada."},
    "I4": {"ajuda": "Banco ou cadeira presos no chão ou na parede não contam."},
    "B1": {"pergunta": "Tem banheiro acessível para clientes, com barras de apoio?",
           "ajuda": "Box maior, com barras de ferro ao lado do vaso. Se não tem banheiro para clientes, responda Não."},
    "B2": {"ajuda": "Pode ser no térreo ou com elevador ou rampa que o cliente pode usar. "
                    "Se não tem banheiro para clientes, responda Não."},
}
ANTES = {
    "E3": {"nome": "Corrimão", "pergunta": "Há corrimão ou apoio na rampa ou no degrau?",
           "ajuda": "É o que segura quem usa bengala ou muleta."},
    "I1": {"ajuda": "Olhe o corredor entre as mesas ocupadas."},
    "I2": {"ajuda": "Mesa de pé central encaixa; pé nas quinas trava."},
    "I3": {"ajuda": "Pode ser tudo no térreo ou com elevador ou rampa que o cliente pode usar."},
    "I4": {"ajuda": "E não só banco fixo preso na parede."},
    "B1": {"pergunta": "Tem banheiro acessível, com barras de apoio?",
           "ajuda": "Box maior, com barras de ferro ao lado do vaso."},
    "B2": {"ajuda": "Pode ser no térreo ou com elevador ou rampa que o cliente pode usar."},
}


def aplicar(textos):
    def _rodar(apps, schema_editor):
        Item = apps.get_model("core", "ItemChecklist")
        for codigo, campos in textos.items():
            Item.objects.filter(codigo=codigo).update(**campos)
    return _rodar


class Migration(migrations.Migration):
    dependencies = [("core", "0008_entrada_sem_degrau")]
    operations = [migrations.RunPython(aplicar(TEXTOS), aplicar(ANTES))]
