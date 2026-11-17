"""Configurações do MoBite (Django 5.2 LTS).

Tudo o que é segredo ou muda entre o PC e o servidor vem de variável de ambiente.
Em desenvolvimento, dá para pôr essas variáveis num arquivo .env na raiz (veja .env.exemplo).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _carregar_env(caminho):
    """Lê um .env simples (CHAVE=valor por linha), sem depender de biblioteca extra."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env(BASE_DIR / ".env")


def env(chave, padrao=""):
    return os.environ.get(chave, padrao)


def env_bool(chave, padrao=False):
    return env(chave, str(padrao)).lower() in ("1", "true", "sim", "yes")


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = env("DJANGO_SECRET_KEY") or ("dev-inseguro-troque-em-producao" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("Defina DJANGO_SECRET_KEY no servidor.")
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in ("localhost", "127.0.0.1")]

INSTALLED_APPS = [
    "core.admin_site.MoBiteAdminConfig",  # o admin do Django, como "Painel da equipe"
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "mobite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.mobite",
            ],
        },
    },
]

WSGI_APPLICATION = "mobite.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "core.Conta"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- Contas (django-allauth) ----------
# RF08–RF10: e-mail e senha ou Google; e-mail confirmado antes de avaliar; recuperação de senha.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]  # senha uma vez só: o olhinho mostra o que foi digitado
ACCOUNT_SESSION_REMEMBER = True  # continua conectado, sem a caixa "Lembrar de mim"
# Textos do MoBite nas telas de conta ("E-mail", regra da senha numa frase)
ACCOUNT_FORMS = {
    "signup": "core.forms_conta.CadastroForm", "login": "core.forms_conta.EntrarForm",
    "reset_password": "core.forms_conta.EsqueciSenhaForm", "reset_password_from_key": "core.forms_conta.NovaSenhaForm",
    "change_password": "core.forms_conta.AlterarSenhaForm", "add_email": "core.forms_conta.NovoEmailForm",
}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
# Confirmar o e-mail antes de avaliar (RN03.1). Enquanto o envio de e-mail não estiver configurado no servidor
# (ex.: na feira), dá para desligar com MOBITE_CONFIRMAR_EMAIL=0 no .env: a conta nova já entra e avalia.
# Padrão: ligado.
CONFIRMAR_EMAIL = env_bool("MOBITE_CONFIRMAR_EMAIL", True)
ACCOUNT_EMAIL_VERIFICATION = "mandatory" if CONFIRMAR_EMAIL else "none"
# Senha das contas de teste do dados_demo (@mobite.example). No PC, mobite2026; no site publicado,
# o script de publicação sorteia outra e guarda no .env.
MOBITE_SENHA_DEMO = env("MOBITE_SENHA_DEMO") or "mobite2026"
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[MoBite] "
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http" if DEBUG else "https"
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "inicio"
ACCOUNT_LOGOUT_REDIRECT_URL = "inicio"

SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # quem entra com Google usa a mesma conta do e-mail
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_PROVIDERS = {"google": {"SCOPE": ["email"], "AUTH_PARAMS": {"prompt": "select_account"}}}
if env("GOOGLE_CLIENT_ID"):
    # Credencial gratuita criada no Google Cloud Console.
    SOCIALACCOUNT_PROVIDERS["google"]["APPS"] = [
        {"client_id": env("GOOGLE_CLIENT_ID"), "secret": env("GOOGLE_CLIENT_SECRET"), "key": ""}
    ]

# ---------- E-mail ----------
# Sem senha configurada, os e-mails aparecem no terminal (bom para testar no PC).
if env("EMAIL_HOST_PASSWORD"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(env("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", f"MoBite <{EMAIL_HOST_USER}>")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "MoBite <nao-responda@mobite.example>"

# ---------- Segurança em produção (RNF08: HTTPS) ----------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
# O OpenStreetMap exige saber de que site vem o pedido do mapa (só a origem, nunca a página visitada).
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---------- Fotos ----------
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024

# ---------- Regras do MoBite ----------
def _versao_dos_arquivos():
    """Muda sozinha quando algum CSS, JS ou imagem muda. Assim, depois de uma atualização do site,
    o celular de quem já abriu o MoBite troca a cópia guardada pela nova (service worker)."""
    import hashlib
    h = hashlib.md5(usedforsecurity=False)
    for f in sorted((BASE_DIR / "static").rglob("*")):
        if f.is_file():
            h.update(f.relative_to(BASE_DIR).as_posix().encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:10]


MOBITE = {
    "RAIO_FOTO_METROS": 150,       # RN03.3
    "DIAS_ITEM_DESATUALIZADO": 180,  # item desatualizado depois de 180 dias
    "MAX_PERGUNTAS": 5,            # RN03.2
    "MIN_SEM_RESPOSTA_FALTA_INFO": 3,  # "falta informação" com 3 ou mais itens relevantes sem resposta
    "ANUNCIO_A_CADA_AVALIACOES": 3,  # bloco de anúncio na tela de agradecimento (1 a cada 3)
    "FOTO_LADO_MAXIMO": 1280,
    "FOTO_TAMANHO_MAXIMO_MB": 10,
    "CONTATO_EMAIL": env("MOBITE_CONTATO_EMAIL", "contato@mobite.example"),
    "CONFIRMAR_EMAIL": CONFIRMAR_EMAIL,
    "VERSAO": _versao_dos_arquivos(),  # cache do app instalado (service worker)
}
