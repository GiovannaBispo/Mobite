"""Painel da equipe MoBite: o admin do Django, organizado pelo trabalho da equipe (RF22, RN07.3)."""
from django.contrib import admin, messages
from django.contrib.admin.apps import AdminConfig
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST


class MoBiteAdminSite(admin.AdminSite):
    site_header = "Painel da equipe"
    site_title = "Equipe MoBite"
    index_title = "Painel da equipe"

    # Seções do painel, na ordem em que a equipe usa (nome do modelo em minúsculas)
    GRUPOS = [
        ("Moderação", ["denuncia", "avaliacaoacessibilidade", "fotoentrada", "avaliacaoatendimento",
                       "respostaestabelecimento", "acaomoderacao"]),
        ("Restaurantes e Concierge", ["restaurante", "auditoria"]),
        ("Restaurantes clientes", ["reivindicacao", "assinatura"]),
        ("Anúncios", ["anuncio"]),
        ("Contas", ["conta", "emailaddress"]),
        ("Checklist e perfis", ["itemchecklist", "perfilmobilidade"]),
    ]

    def get_app_list(self, request, app_label=None):
        apps = super().get_app_list(request, app_label)
        if app_label:
            return apps
        modelos = {m["object_name"].lower(): m for a in apps for m in a["models"]}
        grupos = []
        for nome, chaves in self.GRUPOS:
            itens = [modelos.pop(k) for k in chaves if k in modelos]
            if itens:
                ancora = nome.lower().replace(" ", "-")
                grupos.append({"name": nome, "app_label": ancora, "app_url": reverse("admin:index") + "#" + ancora,
                               "has_module_perms": True, "models": itens})
        if modelos:
            grupos.append({"name": "Outros", "app_label": "outros", "app_url": reverse("admin:index") + "#outros",
                           "has_module_perms": True, "models": list(modelos.values())})
        return grupos


    def login(self, request, extra_context=None):
        """O painel usa o login do site, que bloqueia depois de várias senhas erradas (o do admin não bloqueia)."""
        if request.user.is_authenticated:  # entrou, mas a conta não é da equipe
            messages.error(request, "O painel é só para a Equipe MoBite.")
            return redirect("inicio")
        destino = request.GET.get("next") or reverse("admin:index")
        return redirect(f"{reverse('account_login')}?{urlencode({'next': destino})}")

    def get_urls(self):
        return [path("demonstracao/", self.admin_view(self.alternar_demonstracao), name="alternar_demonstracao"),
                *super().get_urls()]

    @staticmethod
    @require_POST
    def alternar_demonstracao(request):
        """Botão "Restaurantes fictícios" do início do painel: mostra ou esconde a demonstração para o público."""
        from .models import ConfiguracaoSite
        if not request.user.has_perm("core.change_configuracaosite"):
            messages.error(request, "Só a Equipe MoBite pode mudar isso.")
            return redirect("admin:index")
        config = ConfiguracaoSite.atual()
        config.alternar_demonstracao(por=request.user)
        messages.success(request, "Pronto: os restaurantes fictícios voltaram a aparecer no app." if config.mostrar_demonstracao
                         else "Pronto: os restaurantes fictícios não aparecem mais no app. Dá para religar aqui quando quiser.")
        return redirect("admin:index")


class MoBiteAdminConfig(AdminConfig):
    """Usa este painel no lugar do admin padrão (settings.INSTALLED_APPS)."""
    default_site = "core.admin_site.MoBiteAdminSite"
