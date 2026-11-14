from django.conf import settings

from .models import (Anuncio, ConfiguracaoSite, ItemChecklist, PerfilMobilidade, PreferenciaRestaurante, Restaurante,
                     StatusAnalise, TipoPreferencia)


def restaurantes_do_dono(user):
    return Restaurante.objects.filter(reivindicacoes__conta=user, reivindicacoes__status=StatusAnalise.APROVADA).distinct()


def _uma_vez(fn):
    """O template chama a função quando precisa; o resultado fica guardado durante a requisição."""
    guardado = []

    def chamar():
        if not guardado:
            guardado.append(fn())
        return guardado[0]
    return chamar


def _dados_publicos():
    """Perfis, matriz de pesos e itens: o navegador precisa disso para mostrar o resultado do perfil local."""
    perfis = []
    for p in PerfilMobilidade.objects.prefetch_related("pesos__item"):
        perfis.append({"codigo": p.codigo, "nome": p.nome, "descricao": p.descricao,
                       "pesos": {peso.item.codigo: peso.peso for peso in p.pesos.all()}})
    itens = [{"codigo": i.codigo, "nome": i.nome, "zona": i.get_zona_display()} for i in ItemChecklist.objects.all()]
    return {"perfis": perfis, "itens": itens}


def _anuncios():
    return [{"a": a, "perfis": ",".join(p.codigo for p in a.perfis.all())} for a in Anuncio.ativos()]


def mobite(request):
    user = getattr(request, "user", None)
    logado = bool(user and user.is_authenticated)

    def prefs():
        if not logado:
            return {"favoritos": [], "escondidos": []}
        pares = PreferenciaRestaurante.objects.filter(conta=user).values_list("restaurante_id", "tipo")
        return {"favoritos": [r for r, t in pares if t == TipoPreferencia.FAVORITO],
                "escondidos": [r for r, t in pares if t == TipoPreferencia.ESCONDIDO]}

    return {
        "CFG": settings.MOBITE,
        "MODO_DEV": settings.DEBUG,
        "GOOGLE_ATIVO": bool(settings.SOCIALACCOUNT_PROVIDERS.get("google", {}).get("APPS")),
        "dados_publicos": _uma_vez(_dados_publicos),
        # Faixa do rodapé só para quem não entrou na conta (RN06.3).
        "anuncios_rodape": _uma_vez(lambda: [] if logado else _anuncios()),
        "anuncios_todos": _uma_vez(_anuncios),
        "prefs_js": _uma_vez(prefs),
        "demo_visivel": _uma_vez(ConfiguracaoSite.demonstracao_visivel),
        "restaurantes_do_dono": _uma_vez(lambda: list(restaurantes_do_dono(user)) if logado else []),
    }
