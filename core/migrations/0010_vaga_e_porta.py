"""C3 (vaga) e E2 (porta).

- A vaga com espaço ao lado é a de pessoa com deficiência com comprometimento de mobilidade (LBI, art. 47).
  Ela passa a contar só para cadeira de rodas e para muleta, andador ou bengala. Carrinho de bebê,
  dificuldade com escada e assento largo não têm direito a ela, e um lugar sem vaga ficava com ressalva
  para eles.
- E2: a dica comparava 80 cm com "quase o dobro de um ombro", o que não fecha (os ombros de um adulto,
  por fora, têm uns 45 a 51 cm). Entrou o caso da porta de duas folhas em que só uma abre."""
from django.db import migrations

SEM_VAGA = ("carrinho", "escada", "assento")
E2_NOVO = "Cerca de 80 cm livres para passar. Se a porta tem duas folhas e só uma abre, conte só a que abre."
E2_ANTIGO = "Cerca de 80 cm, quase o dobro de um ombro."


def recalcular_resultados(apps):
    from core.regras import classificar  # função pura: recebe dicionários

    Restaurante = apps.get_model("core", "Restaurante")
    Peso = apps.get_model("core", "PesoItemPerfil")
    Resultado = apps.get_model("core", "ResultadoPerfil")
    Situacao = apps.get_model("core", "SituacaoItem")
    matriz = {}
    for p in Peso.objects.select_related("perfil", "item"):
        matriz.setdefault(p.perfil_id, {})[p.item.codigo] = p.peso
    for r in Restaurante.objects.all():
        respostas = {s.item.codigo: ("NAO_SEI" if s.em_duvida else s.resposta)
                     for s in Situacao.objects.filter(restaurante=r).select_related("item")}
        for perfil_id, pesos in matriz.items():
            classe, _ = classificar(pesos, respostas)
            Resultado.objects.filter(restaurante=r, perfil_id=perfil_id).update(classificacao=classe)


def aplicar(apps, schema_editor):
    Item = apps.get_model("core", "ItemChecklist")
    Peso = apps.get_model("core", "PesoItemPerfil")
    Item.objects.filter(codigo="E2").update(ajuda=E2_NOVO)
    Peso.objects.filter(item__codigo="C3", perfil__codigo__in=SEM_VAGA).delete()
    recalcular_resultados(apps)


def desfazer(apps, schema_editor):
    Item = apps.get_model("core", "ItemChecklist")
    Perfil = apps.get_model("core", "PerfilMobilidade")
    Peso = apps.get_model("core", "PesoItemPerfil")
    Item.objects.filter(codigo="E2").update(ajuda=E2_ANTIGO)
    c3 = Item.objects.filter(codigo="C3").first()
    if c3:
        for perfil in Perfil.objects.filter(codigo__in=SEM_VAGA):
            Peso.objects.get_or_create(perfil=perfil, item=c3, defaults={"peso": "IMPORTA"})
    recalcular_resultados(apps)


class Migration(migrations.Migration):
    dependencies = [("core", "0009_textos_do_checklist")]
    operations = [migrations.RunPython(aplicar, desfazer)]
