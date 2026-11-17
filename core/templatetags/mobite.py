from django import template
from django.utils import timezone
from django.utils.html import format_html, format_html_join

register = template.Library()

ROTULO = {"ok": "Funciona", "warn": "Funciona com ressalva", "bar": "Tem barreira", "nd": "Falta informação"}
ROTULO_ITEM = {"ok": "Sim", "bar": "Não", "nd": "Falta informação"}


@register.simple_tag
def icone(nome, classe=""):
    """Ícone do sprite (templates/icones.html). Decorativo: o texto ao lado ou o aria-label diz o que é."""
    return format_html('<svg class="icone {}" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>',
                       classe, nome)


@register.simple_tag(takes_context=True)
def endereco_site(context):
    """Começo do endereço do site (https://mobite.pythonanywhere.com). No e-mail só funciona endereço completo."""
    from django.conf import settings
    request = context.get("request")
    if request:
        return f"{settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL}://{request.get_host()}"
    return f"https://{settings.ALLOWED_HOSTS[0]}" if settings.ALLOWED_HOSTS else ""


@register.simple_tag
def forma(css):
    """Forma do resultado: círculo, triângulo, losango ou quadrado (forma além da cor)."""
    return format_html('<svg class="forma" aria-hidden="true" focusable="false"><use href="#f-{}"></use></svg>', css)


@register.simple_tag
def indicador(css, item=False, rotulo=None):
    rotulo = rotulo or (ROTULO_ITEM if item else ROTULO).get(css, "")
    return format_html('<span class="ind s-{}">{}{}</span>', css, forma(css), rotulo)


@register.simple_tag
def estrelas(media):
    """5 estrelas de atendimento, cheias ou vazias, com o número para leitor de tela."""
    if media is None:
        return ""
    cheias = round(media)
    numero = f"{media:.1f}".replace(".", ",")
    return format_html('<span class="est" role="img" aria-label="{} de 5 estrelas">{}</span>', numero,
                       format_html_join("", "{}", ((icone("star", "cheia" if i < cheias else ""),) for i in range(5))))


@register.filter
def ha_dias(valor):
    """RN05.3: nunca a data e a hora; só há quantos dias. Aceita datetime ou número de dias."""
    if valor is None or valor == "":
        return ""
    dias = valor if isinstance(valor, int) else (timezone.now() - valor).days
    if dias <= 0:
        return "hoje"
    if dias == 1:
        return "ontem"
    if dias < 60:
        return f"há {dias} dias"
    meses = dias // 30
    return f"há {meses} meses" if meses < 24 else f"há {dias // 365} anos"


@register.simple_tag
def fila_equipe():
    """Contagens do "Para fazer agora" do painel da equipe."""
    from datetime import timedelta

    from core.models import (Assinatura, ConfiguracaoSite, Denuncia, Reivindicacao, Restaurante, StatusAnalise,
                             StatusAssinatura)
    hoje = timezone.localdate()
    return {
        "config": ConfiguracaoSite.atual(),
        "n_demo": Restaurante.objects.filter(demonstracao=True).count(),
        "denuncias": Denuncia.objects.filter(status=StatusAnalise.PENDENTE).count(),
        "reivindicacoes": Reivindicacao.objects.filter(status=StatusAnalise.PENDENTE).count(),
        "vencendo": Assinatura.objects.filter(status=StatusAssinatura.ATIVA, data_fim__gte=hoje,
                                              data_fim__lte=hoje + timedelta(days=7)).count(),
        "sem_auditoria": Restaurante.objects.filter(visivel=True, demonstracao=False, auditorias__isnull=True).count(),
    }


@register.filter
def nota(valor):
    return "" if valor is None else f"{valor:.1f}".replace(".", ",")
