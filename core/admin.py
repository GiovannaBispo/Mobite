"""Painel da equipe MoBite (RF22, RN07.3): auditoria do Concierge, moderação, restaurantes,
reivindicações, assinaturas e anúncios. A equipe oculta ou remove, mas não reescreve o que outra pessoa escreveu."""
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html

from . import regras
from .models import (AcaoModeracao, Anuncio, Assinatura, Auditoria, AvaliacaoAcessibilidade, AvaliacaoAtendimento,
                     Conta, Denuncia, FotoEntrada, ItemChecklist, PerfilMobilidade, PesoItemPerfil, Reivindicacao,
                     Resposta, RespostaAuditoria, RespostaEstabelecimento, RespostaItem, Restaurante, ResultadoPerfil,
                     SituacaoItem, StatusAnalise)


# ------------------------------------------------------------------ contas
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken  # noqa: E402

for _modelo in (SocialApp, SocialAccount, SocialToken):  # técnicos do login com Google: a equipe não usa
    if admin.site.is_registered(_modelo):
        admin.site.unregister(_modelo)

class ContaCriacaoForm(UserCreationForm):
    class Meta:
        model = Conta
        fields = ("email",)


class ContaEdicaoForm(UserChangeForm):
    class Meta:
        model = Conta
        fields = "__all__"


@admin.register(Conta)
class ContaAdmin(UserAdmin):
    form, add_form = ContaEdicaoForm, ContaCriacaoForm
    list_display = ("email", "apelido", "papel", "status", "date_joined")
    list_filter = ("papel", "status")
    search_fields = ("email", "apelido")
    ordering = ("email",)
    readonly_fields = ("date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil público", {"fields": ("apelido", "aparecer_publicamente")}),
        ("Papel e situação", {"fields": ("papel", "status", "is_superuser")}),
        ("Datas", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "papel")}),)
    actions = ["bloquear", "desbloquear"]

    @admin.action(description="Bloquear contas selecionadas")
    def bloquear(self, request, qs):
        for c in qs:
            c.bloquear("Bloqueada pela equipe", por=request.user)

    @admin.action(description="Desbloquear contas selecionadas")
    def desbloquear(self, request, qs):
        for c in qs:
            c.desbloquear(por=request.user)


# ------------------------------------------------------------------ checklist e perfis
@admin.register(ItemChecklist)
class ItemChecklistAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "zona", "invertida", "ordem")
    list_editable = ("ordem",)


class PesoInline(admin.TabularInline):
    model = PesoItemPerfil
    extra = 0


@admin.register(PerfilMobilidade)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "descricao")
    inlines = [PesoInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        for r in Restaurante.objects.all():  # mudou a matriz: recalcula todos os resultados
            regras.calcular_resultados(r)


# ------------------------------------------------------------------ restaurantes
class SituacaoInline(admin.TabularInline):
    model = SituacaoItem
    extra = 0
    can_delete = False
    fields = ("item", "resposta", "data_ultima_verificacao", "confirmacoes")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class ResultadoInline(admin.TabularInline):
    model = ResultadoPerfil
    extra = 0
    can_delete = False
    fields = ("perfil", "classificacao", "data_calculo")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    list_display = ("nome", "endereco", "visivel", "demonstracao", "tem_assinatura")
    list_filter = ("visivel", "demonstracao")
    search_fields = ("nome", "endereco")
    readonly_fields = ("osm_tipo", "osm_id", "data_importacao")
    inlines = [SituacaoInline, ResultadoInline]
    actions = ["recalcular", "ocultar", "reexibir"]

    @admin.display(boolean=True, description="Assinatura ativa")
    def tem_assinatura(self, obj):
        return obj.assinatura_ativa()

    @admin.action(description="Recalcular situação e resultados")
    def recalcular(self, request, qs):
        for r in qs:
            regras.recalcular(r)
        messages.success(request, f"{qs.count()} restaurante(s) recalculado(s).")

    @admin.action(description="Ocultar do app")
    def ocultar(self, request, qs):
        for r in qs:
            r.ocultar("Ocultado pela equipe", por=request.user)

    @admin.action(description="Reexibir no app")
    def reexibir(self, request, qs):
        for r in qs:
            r.reexibir(por=request.user)


# ------------------------------------------------------------------ auditoria do Concierge
NAO_CONFERIDO = ""


class AuditoriaForm(forms.ModelForm):
    """Uma pergunta por item do checklist, como na visita do Concierge."""

    class Meta:
        model = Auditoria
        fields = ("restaurante", "data", "observacoes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        atuais = {}
        if self.instance.pk:
            atuais = {r.item.codigo: r.resposta for r in self.instance.respostas.select_related("item")}
        for item in ItemChecklist.objects.all():
            self.fields[f"item_{item.codigo}"] = forms.ChoiceField(
                label=f"{item.codigo} – {item.pergunta}", required=False, initial=atuais.get(item.codigo, ""),
                choices=[(NAO_CONFERIDO, "Não conferido")] + list(Resposta.choices), widget=forms.RadioSelect)


class RecalculaAoExcluir:
    """Excluir uma auditoria ou avaliação pelo painel (uma ou várias) refaz o resultado do restaurante."""

    def delete_model(self, request, obj):
        restaurante = obj.restaurante
        super().delete_model(request, obj)
        regras.recalcular(restaurante)

    def delete_queryset(self, request, queryset):
        restaurantes = list(Restaurante.objects.filter(pk__in=queryset.values("restaurante")))
        super().delete_queryset(request, queryset)
        for r in restaurantes:
            regras.recalcular(r)


@admin.register(Auditoria)
class AuditoriaAdmin(RecalculaAoExcluir, admin.ModelAdmin):
    form = AuditoriaForm
    list_display = ("restaurante", "data", "autor")
    autocomplete_fields = ("restaurante",)

    def get_fields(self, request, obj=None):
        return ["restaurante", "data", "observacoes"] + [f"item_{i.codigo}" for i in ItemChecklist.objects.all()]

    def get_form(self, request, obj=None, **kwargs):
        kwargs["fields"] = ["restaurante", "data", "observacoes"]  # os itens são criados no __init__ do form
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.autor_id:
            obj.autor = request.user
        super().save_model(request, obj, form, change)
        for item in ItemChecklist.objects.all():
            valor = form.cleaned_data.get(f"item_{item.codigo}")
            if valor:
                RespostaAuditoria.objects.update_or_create(auditoria=obj, item=item, defaults={"resposta": valor})
            else:
                RespostaAuditoria.objects.filter(auditoria=obj, item=item).delete()
        regras.recalcular(obj.restaurante)


# ------------------------------------------------------------------ contribuições e moderação
class RespostaItemInline(admin.TabularInline):
    model = RespostaItem
    extra = 0
    can_delete = False
    readonly_fields = ("item", "resposta")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AvaliacaoAcessibilidade)
class AvaliacaoAdmin(RecalculaAoExcluir, admin.ModelAdmin):
    list_display = ("restaurante", "data", "visivel", "tem_foto")
    list_filter = ("visivel",)
    search_fields = ("restaurante__nome",)
    readonly_fields = ("autor", "restaurante", "data", "visivel", "foto_previa")
    inlines = [RespostaItemInline]
    actions = ["ocultar", "reexibir"]

    def has_add_permission(self, request):
        return False

    @admin.display(boolean=True, description="Foto")
    def tem_foto(self, obj):
        return hasattr(obj, "foto")

    @admin.display(description="Foto da entrada")
    def foto_previa(self, obj):
        foto = getattr(obj, "foto", None)
        return format_html('<img src="{}" style="max-width:320px">', foto.arquivo.url) if foto else "—"

    @admin.action(description="Ocultar (recalcula o restaurante)")
    def ocultar(self, request, qs):
        for a in qs:
            a.ocultar("Ocultada pela equipe", por=request.user)

    @admin.action(description="Reexibir (recalcula o restaurante)")
    def reexibir(self, request, qs):
        for a in qs:
            a.reexibir(por=request.user)


@admin.register(FotoEntrada)
class FotoAdmin(admin.ModelAdmin):
    list_display = ("previa", "restaurante", "data_envio", "proximidade_confirmada", "visivel")
    list_filter = ("visivel",)
    readonly_fields = ("avaliacao", "arquivo", "data_envio", "proximidade_confirmada", "visivel", "previa")
    actions = ["ocultar", "reexibir"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Restaurante")
    def restaurante(self, obj):
        return obj.avaliacao.restaurante

    @admin.display(description="Prévia")
    def previa(self, obj):
        return format_html('<img src="{}" style="max-height:80px">', obj.arquivo.url)

    @admin.action(description="Ocultar fotos")
    def ocultar(self, request, qs):
        for f in qs:
            f.ocultar("Ocultada pela equipe", por=request.user)

    @admin.action(description="Reexibir fotos")
    def reexibir(self, request, qs):
        for f in qs:
            f.reexibir(por=request.user)


@admin.register(AvaliacaoAtendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ("restaurante", "estrelas", "data", "visivel")
    list_filter = ("visivel", "estrelas")
    readonly_fields = ("autor", "restaurante", "estrelas", "data", "visivel")
    actions = ["remover"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Ocultar avaliações de atendimento")
    def remover(self, request, qs):
        for a in qs:
            a.remover("Ocultada pela equipe", por=request.user)


@admin.register(RespostaEstabelecimento)
class RespostaEstabelecimentoAdmin(admin.ModelAdmin):
    list_display = ("situacao", "data", "visivel")
    readonly_fields = ("autor", "situacao", "texto", "data", "data_edicao", "visivel")
    actions = ["ocultar"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Ocultar respostas")
    def ocultar(self, request, qs):
        for r in qs:
            r.ocultar("Ocultada pela equipe", por=request.user)


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ("data", "motivo", "status", "alvo_resumo")
    list_filter = ("status", "motivo")
    readonly_fields = ("autor", "motivo", "descricao", "data", "status", "analisada_por", "avaliacao", "foto",
                       "resposta_estabelecimento", "alvo_resumo")
    actions = ["aprovar", "rejeitar"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Conteúdo denunciado")
    def alvo_resumo(self, obj):
        if obj.foto:
            return format_html('Foto de {}<br><img src="{}" style="max-height:120px">',
                               obj.foto.avaliacao.restaurante, obj.foto.arquivo.url)
        if obj.avaliacao:
            itens = ", ".join(f"{r.item.nome}: {r.get_resposta_display()}" for r in obj.avaliacao.respostas.all())
            return f"Avaliação de {obj.avaliacao.restaurante} – {itens}"
        if obj.resposta_estabelecimento:
            return f"Resposta de {obj.resposta_estabelecimento.situacao.restaurante}: {obj.resposta_estabelecimento.texto}"
        return "—"

    @admin.action(description="Aprovar denúncia (oculta o conteúdo)")
    def aprovar(self, request, qs):
        for d in qs.filter(status=StatusAnalise.PENDENTE):
            d.resolver(StatusAnalise.APROVADA, por=request.user)

    @admin.action(description="Rejeitar denúncia (mantém o conteúdo)")
    def rejeitar(self, request, qs):
        for d in qs.filter(status=StatusAnalise.PENDENTE):
            d.resolver(StatusAnalise.REJEITADA, por=request.user)


@admin.register(AcaoModeracao)
class AcaoModeracaoAdmin(admin.ModelAdmin):
    """Histórico: só leitura."""
    list_display = ("data", "tipo", "alvo", "id_alvo", "motivo", "executada_por")
    list_filter = ("tipo", "alvo")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ------------------------------------------------------------------ restaurante como cliente
@admin.register(Reivindicacao)
class ReivindicacaoAdmin(admin.ModelAdmin):
    list_display = ("restaurante", "conta", "cnpj", "data_solicitacao", "status")
    list_filter = ("status",)
    readonly_fields = ("conta", "restaurante", "cnpj", "data_solicitacao", "status", "verificada_por")
    actions = ["aprovar", "rejeitar"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Aprovar (a conta passa a administrar a página)")
    def aprovar(self, request, qs):
        for r in qs:
            r.aprovar(por=request.user)

    @admin.action(description="Rejeitar")
    def rejeitar(self, request, qs):
        for r in qs:
            r.rejeitar(por=request.user)


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ("restaurante", "plano", "data_inicio", "data_fim", "status")
    list_filter = ("status",)
    autocomplete_fields = ("restaurante",)
    readonly_fields = ("ativada_por",)
    actions = ["ativar", "cancelar"]

    def save_model(self, request, obj, form, change):
        if not obj.ativada_por_id:
            obj.ativada_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Ativar por 1 mês a partir de hoje")
    def ativar(self, request, qs):
        for a in qs:
            a.ativar(por=request.user)

    @admin.action(description="Cancelar")
    def cancelar(self, request, qs):
        for a in qs:
            a.cancelar()


@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = ("titulo", "data_inicio", "data_fim", "cliques")
    filter_horizontal = ("perfis",)
    readonly_fields = ("cliques", "cadastrado_por")
    autocomplete_fields = ("restaurante",)

    def save_model(self, request, obj, form, change):
        if not obj.cadastrado_por_id:
            obj.cadastrado_por = request.user
        super().save_model(request, obj, form, change)
