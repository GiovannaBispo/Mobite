"""Guarda, em cada avaliação, quantas consultas o lugar já tinha no dia. Assim, as consultas do mesmo dia que
vieram depois da avaliação também contam em "pessoas que viram este lugar depois da sua avaliação".

Avaliações antigas: a consulta de quem avaliou (feita antes de avaliar) já estava no total do dia, então ela
fica descontada. Consultas de outras pessoas antes da avaliação, no mesmo dia, não dá para saber."""
from django.db import migrations, models
from django.utils import timezone


def preencher(apps, schema_editor):
    Avaliacao = apps.get_model("core", "AvaliacaoAcessibilidade")
    ConsultaDiaria = apps.get_model("core", "ConsultaDiaria")
    for av in Avaliacao.objects.select_related("autor").order_by("data"):
        autor = av.autor
        if not autor or autor.is_staff:
            continue  # a equipe não entra na contagem
        if Avaliacao.objects.filter(autor=autor, restaurante_id=av.restaurante_id, data__lt=av.data).exists():
            continue  # quem já tinha avaliado o lugar não entra na contagem
        dia = timezone.localdate(av.data)
        total = ConsultaDiaria.objects.filter(restaurante_id=av.restaurante_id, data=dia).values_list(
            "total", flat=True).first() or 0
        av.consultas_no_dia = min(1, total)
        av.save(update_fields=["consultas_no_dia"])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_elevador_conta'),
    ]

    operations = [
        migrations.AddField(
            model_name='avaliacaoacessibilidade',
            name='consultas_no_dia',
            field=models.PositiveIntegerField(default=0, editable=False),
        ),
        migrations.AlterField(
            model_name='configuracaosite',
            name='mostrar_demonstracao',
            field=models.BooleanField(default=True, help_text='Desligado, os restaurantes fictícios somem do app para o público.', verbose_name='mostrar a demonstração'),
        ),
        migrations.RunPython(preencher, migrations.RunPython.noop),
    ]
