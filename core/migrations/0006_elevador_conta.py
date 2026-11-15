"""I3 e B2: elevador ou rampa que o cliente pode usar contam como "sem escada"
(um restaurante com salão no andar de cima e elevador não tem barreira para quem não sobe escada)."""
from django.db import migrations

TEXTOS = {
    "I3": {"nome": "Salão sem escada", "pergunta": "Dá para chegar ao salão e ao caixa sem escada?",
           "ajuda": "Pode ser tudo no térreo ou com elevador ou rampa que o cliente pode usar."},
    "B2": {"ajuda": "Pode ser no térreo ou com elevador ou rampa que o cliente pode usar."},
}
ANTES = {
    "I3": {"nome": "Tudo no térreo", "pergunta": "O atendimento é todo no térreo, sem escada obrigatória?",
           "ajuda": "Salão, caixa e banheiro no mesmo andar da entrada."},
    "B2": {"ajuda": "Sem degrau, sem subsolo e sem andar de cima."},
}


def aplicar(textos):
    def _rodar(apps, schema_editor):
        Item = apps.get_model("core", "ItemChecklist")
        for codigo, campos in textos.items():
            Item.objects.filter(codigo=codigo).update(**campos)
    return _rodar


class Migration(migrations.Migration):
    dependencies = [("core", "0005_configuracao_do_app")]
    operations = [migrations.RunPython(aplicar(TEXTOS), aplicar(ANTES))]
