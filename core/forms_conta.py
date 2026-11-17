"""Formulários das telas de conta (django-allauth) com os textos do MoBite: "E-mail" em vez de "Email",
sem dois-pontos depois do rótulo e a regra da senha numa frase só (as regras continuam valendo)."""
from allauth.account.forms import (AddEmailForm, ChangePasswordForm, LoginForm, ResetPasswordForm,
                                   ResetPasswordKeyForm, SignupForm)
from django.urls import reverse
from django.utils.html import format_html

DICA_SENHA = "Pelo menos 8 caracteres, sem ser só números nem uma senha fácil de adivinhar."


class _TextosMoBite:
    rotulos = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""
        for nome, rotulo in self.rotulos.items():
            if nome in self.fields:
                self.fields[nome].label = rotulo
                self.fields[nome].widget.attrs.pop("placeholder", None)  # o rótulo já diz o que é
        for nome in ("password1",):
            if nome in self.fields:
                self.fields[nome].help_text = DICA_SENHA


class CadastroForm(_TextosMoBite, SignupForm):
    rotulos = {"email": "E-mail", "password1": "Senha"}


class EntrarForm(_TextosMoBite, LoginForm):
    rotulos = {"login": "E-mail", "password": "Senha"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].help_text = format_html('<a href="{}">Esqueci a senha</a>',
                                                        reverse("account_reset_password"))


class EsqueciSenhaForm(_TextosMoBite, ResetPasswordForm):
    rotulos = {"email": "E-mail"}


class NovaSenhaForm(_TextosMoBite, ResetPasswordKeyForm):
    rotulos = {"password1": "Nova senha", "password2": "Repita a nova senha"}


class AlterarSenhaForm(_TextosMoBite, ChangePasswordForm):
    rotulos = {"oldpassword": "Senha atual", "password1": "Nova senha", "password2": "Repita a nova senha"}


class NovoEmailForm(_TextosMoBite, AddEmailForm):
    rotulos = {"email": "E-mail"}
