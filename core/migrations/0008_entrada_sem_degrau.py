"""E1: "A entrada tem degrau ou escada?" virou "Dá para entrar sem subir degrau ou escada?".

Com degrau e rampa ao lado, a pessoa respondia "Sim" (tem degrau) e o lugar ficava com barreira para cadeira de
rodas, mesmo dando para entrar pela rampa. A pergunta nova também deixa de ser ao contrário: "Sim" passa a ser o
que atende, como nas outras. As respostas já dadas trocam de lado junto, então o resultado dos lugares não muda."""
from django.db import migrations

NOVO = {"pergunta": "Dá para entrar sem subir degrau ou escada?",
        "ajuda": "Vale rampa, elevador ou outra porta que o cliente pode usar.", "invertida": False}
ANTIGO = {"pergunta": "A entrada tem degrau ou escada?",
          "ajuda": "Olhe a porta principal a partir da calçada.", "invertida": True}
TROCA = {"SIM": "NAO", "NAO": "SIM"}


def aplicar(textos):
    def rodar(apps, schema_editor):
        Item = apps.get_model("core", "ItemChecklist")
        e1 = Item.objects.filter(codigo="E1").first()
        if not e1:
            return
        for campo, valor in textos.items():
            setattr(e1, campo, valor)
        e1.save()
        for modelo in ("RespostaItem", "RespostaAuditoria"):
            Modelo = apps.get_model("core", modelo)
            for r in Modelo.objects.filter(item=e1, resposta__in=TROCA):
                r.resposta = TROCA[r.resposta]
                r.save(update_fields=["resposta"])
    return rodar


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_consultas_no_dia"),
    ]

    operations = [migrations.RunPython(aplicar(NOVO), aplicar(ANTIGO))]
