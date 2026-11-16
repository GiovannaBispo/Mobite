#!/bin/bash
# Instala ou atualiza o MoBite numa conta do PythonAnywhere.
#
# Antes da primeira vez: aba Web > Add a new web app > Manual configuration > Python 3.11.
# Depois, no console Bash do PythonAnywhere:
#
#   unzip -oq mobite-site.zip && bash mobite/deploy/pythonanywhere.sh
#
# Na primeira vez ele cria o ambiente, o .env com uma chave nova, o banco com a demonstração
# e pede uma senha nova para a conta da equipe. Nas próximas, só atualiza: não mexe no banco,
# nas fotos nem no .env.
set -e

USUARIO=$(whoami)
APP="$HOME/mobite"
HOST="${MOBITE_HOST:-$USUARIO.pythonanywhere.com}"
PY="${PYTHON:-python3.11}"
WSGI="/var/www/${HOST//./_}_wsgi.py"

cd "$APP"

if ! command -v "$PY" > /dev/null; then
  echo "Não achei o $PY. Rode de novo indicando a versão escolhida na aba Web, por exemplo:"
  echo "  PYTHON=python3.12 bash mobite/deploy/pythonanywhere.sh"
  exit 1
fi

echo "1/5 Ambiente Python ($PY)"
[ -d .venv ] || "$PY" -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -q -r requirements.txt

echo "2/5 Configuração"
if [ ! -f .env ]; then
  SEGREDO=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
  cat > .env << FIM
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$SEGREDO
DJANGO_ALLOWED_HOSTS=$HOST

# E-mail pelo Gmail do projeto (senha de app). Vazio = os e-mails vão para o log do servidor.
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# 1 = precisa confirmar o e-mail para avaliar. 0 = a conta nova já entra e avalia (sem e-mail configurado).
MOBITE_CONFIRMAR_EMAIL=1
FIM
  chmod 600 .env
  echo "   .env criado"
else
  echo "   .env já existe (mantido)"
fi
# Senha das contas de teste neste site: sorteada uma vez, diferente da mobite2026 que está no código
SENHA_NOVA=0
if ! grep -q '^MOBITE_SENHA_DEMO=.' .env; then
  sed -i '/^MOBITE_SENHA_DEMO=/d' .env
  echo "MOBITE_SENHA_DEMO=mobite-$(python -c "import secrets; print(secrets.token_hex(4))")" >> .env
  echo "   Senha nova sorteada para as contas de teste"
  SENHA_NOVA=1
fi
SENHA_DEMO=$(grep '^MOBITE_SENHA_DEMO=' .env | cut -d= -f2-)

NOVO=0
[ -f db.sqlite3 ] || NOVO=1

echo "3/5 Banco de dados"
python manage.py migrate --noinput
# Só quando a senha acabou de ser sorteada. Nas outras atualizações, senha trocada depois continua valendo.
if [ "$SENHA_NOVA" = 1 ]; then python manage.py dados_demo --trocar-senha; fi
mkdir -p media

for f in dados/osm-*.json; do  # restaurantes reais guardados no PC com importar_osm --salvar
  if [ -f "$f" ]; then python manage.py importar_osm --arquivo "$f" --so-novos; fi
done

echo "4/5 Arquivos do site"
# --clear copia tudo de novo: o unzip pode deixar os arquivos com data mais antiga que a da cópia anterior,
# e sem ele o collectstatic pula o arquivo achando que não mudou.
python manage.py collectstatic --noinput --clear -v 0

if [ "$NOVO" = 1 ]; then
  echo "   Criando a demonstração"
  python manage.py dados_demo
  echo
  echo "O painel da equipe fica aberto na internet. Escolha agora uma senha só para equipe@mobite.example."
  python manage.py changepassword equipe@mobite.example || \
    echo "Senha não trocada. Rode depois: cd ~/mobite && .venv/bin/python manage.py changepassword equipe@mobite.example"
fi

echo "5/5 Ligando o site"
if [ -f "$WSGI" ]; then
  cat > "$WSGI" << FIM
# Gerado por mobite/deploy/pythonanywhere.sh
import os
import sys

caminho = "$APP"
if caminho not in sys.path:
    sys.path.insert(0, caminho)
os.environ["DJANGO_SETTINGS_MODULE"] = "mobite.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
FIM
  echo "   Arquivo WSGI atualizado (isso também recarrega o site)"
else
  echo "   Não achei $WSGI."
  echo "   Crie o site na aba Web (Manual configuration, mesma versão do Python) e rode este script de novo."
fi

echo
echo "Senha sorteada para as outras contas de teste: $SENHA_DEMO (guardada em mobite/.env; não vale para conta que teve a senha trocada)"
echo "Pronto. Na aba Web, confira:"
echo "  Virtualenv:   $APP/.venv"
echo "  Static files: /static/ -> $APP/staticfiles"
echo "                /media/  -> $APP/media"
echo "  Force HTTPS ligado, e clique em Reload."
echo "Endereço: https://$HOST"
