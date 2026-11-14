# MoBite

Mapa colaborativo de acessibilidade em restaurantes. Ele ajuda pessoas com mobilidade reduzida a responder uma pergunta: **dá para chegar, entrar e usar o banheiro deste restaurante com a minha mobilidade?**

Projeto acadêmico do Grupo 01, Laboratório de Software e Projetos, FMU.

Site: <https://mobite.pythonanywhere.com>

---

## Como executar

Precisa do Python 3.11.

```bat
cd Mobite
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py dados_demo
python manage.py importar_osm --arquivo dados/osm-liberdade.json
python manage.py runserver
```

Abra <http://127.0.0.1:8000>. O painel da equipe fica em <http://127.0.0.1:8000/equipe/>.

Sem o arquivo `.env`, os e-mails aparecem no terminal e o login com Google não aparece. Para configurar, copie `.env.exemplo` para `.env` e preencha.

Para rodar os testes: `python manage.py test`.

---

## Contas de teste

O `dados_demo` cria os 10 restaurantes fictícios do protótipo (marcados como "demonstração") e estas contas. A senha aparece no terminal quando o comando termina:

| Conta | Para testar |
|---|---|
| `mobite@mobite.example` | Avaliador que aparece com apelido e selo |
| `equipe@mobite.example` | Painel da equipe |
| `restaurante@mobite.example` | Responsável pelo "Sabores do Mundo", que responde às pendências |
| `avaliador1@mobite.example`, `avaliador2@mobite.example` | Avaliadores anônimos |

Os e-mails são de mentira e só servem para entrar. No site publicado, as senhas são outras e ficam com a equipe.

No painel da equipe, o botão "Esconder do público" tira os fictícios do app sem apagar. Para apagar de vez: `python manage.py dados_demo --apagar`.

---

## Restaurantes reais

Os restaurantes reais vêm do OpenStreetMap: são os que ficam a até 500 m do campus Taguá da FMU, na Liberdade, incluindo lanchonetes e redes como McDonald's e Habib's. A lista está em `dados/osm-liberdade.json`. Para buscar de novo:

```bat
python manage.py importar_osm --perto=-23.5612,-46.6366,500 --salvar dados/osm-liberdade.json
```

Eles entram sem informação de acessibilidade. As respostas aparecem depois que alguém visita o lugar: a equipe registra a visita no painel, em "Auditorias (Concierge)".

---

## Como o resultado é calculado

| Símbolo | Significado |
|---|---|
| ● Círculo | Funciona |
| ▲ Triângulo | Funciona com ressalva |
| ◆ Losango | Tem barreira |
| ■ Quadrado | Falta informação |

Para cada perfil, um item do checklist pode bloquear ou só importar. O resultado segue esta ordem:

1. Algum item que bloqueia está "não": Tem barreira.
2. Falta resposta num item que bloqueia, ou em 3 ou mais itens do perfil: Falta informação.
3. Algum item que só importa está "não": Funciona com ressalva.
4. Senão: Funciona.

As estrelas são só do atendimento e não entram no resultado.

---

## Privacidade

- O perfil de mobilidade fica só no aparelho e não vai para o servidor.
- A foto da entrada é guardada sem metadados, e a localização usada para conferir a distância não é salva.
- As avaliações são anônimas, a não ser que a pessoa escolha aparecer com apelido.

---

## Publicar no PythonAnywhere

**Primeira vez**

1. Aba **Web**: *Add a new web app* > *Manual configuration* > Python 3.11.
2. Aba **Files**: envie o `.zip` do projeto, sem `.venv`, `db.sqlite3`, `media/` e `.env`.
3. Console **Bash**: `unzip -oq mobite-site.zip && bash mobite/deploy/pythonanywhere.sh`. O script instala tudo, cria o banco com os restaurantes e pede uma senha para `equipe@mobite.example`. As outras contas de teste ganham uma senha sorteada, que aparece no fim e fica no `.env`.
4. Aba **Web**: Virtualenv `/home/<usuario>/mobite/.venv`; Static files `/static/` > `/home/<usuario>/mobite/staticfiles` e `/media/` > `/home/<usuario>/mobite/media`; ligue o **Force HTTPS** e clique em **Reload**.

**Atualizar:** envie o `.zip` novo e rode o mesmo comando do passo 3. O banco, as fotos e o `.env` continuam como estão.

**Cuidados**

- A conta grátis desliga o site depois de 1 mês sem renovar. Renove na aba Web antes de cada apresentação.
- Para criar conta sem confirmar o e-mail (numa feira, por exemplo), ponha `MOBITE_CONFIRMAR_EMAIL=0` no `.env` e clique em Reload.

O branch `prototipo-supabase` guarda a versão do protótipo com Supabase.

---

## Equipe

| Integrante | Papel |
|---|---|
| José Henrique Guimarães Galvão Silva | Produto e desenvolvimento |
| Giovanna Bispo Da Silva | Front-end e design |
| Gabriella Pereira Rodrigues | Qualidade e testes |
| Diego Azevedo Dias Inacio | Dados e pesquisa |

---

## Créditos

- Feito com Django, SQLite e django-allauth.
- Mapas: [Leaflet](https://leafletjs.com/) e [OpenStreetMap](https://www.openstreetmap.org/copyright) (© colaboradores do OpenStreetMap).
- Ícones: [Lucide](https://lucide.dev).
- Checklist baseado em pontos da **ABNT NBR 9050** que podem ser conferidos sem equipamento.
