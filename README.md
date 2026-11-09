# MoBite

Protótipo front-end de um mapa colaborativo de acessibilidade em restaurantes. Ele ajuda pessoas com mobilidade reduzida a responder uma pergunta: **dá para chegar, entrar e usar o banheiro deste restaurante com a minha mobilidade?**

> **Projeto acadêmico.** Todos os restaurantes, notas, endereços, datas e contagens são **fictícios**. Nada é enviado a um servidor.

---

## Como executar

O projeto é HTML, CSS e JavaScript puro (Vanilla JS). Não precisa instalar nada.

1. Abra a pasta `mobite` no VS Code.
2. Instale a extensão **Live Server**.
3. Clique com o botão direito em `index.html` e escolha **Open with Live Server**.

É necessária conexão com a internet, porque o **Leaflet** (biblioteca do mapa) e os **mapas do OpenStreetMap** são carregados pela internet. Sem conexão, o site funciona, mas o mapa mostra um aviso.

---

## Funcionalidades

- **Página inicial:** CEP, busca rápida e uma área de descoberta com filtros (Todos, Restaurantes, Cafeterias, Lanchonetes, Padarias, Mais bem avaliados e Mais próximos) que atualizam a lista sem trocar de página.
- **Encontrar restaurantes:** lista com filtros (nota de atendimento, distância, categoria, item do checklist e favoritos), favoritar e "não recomendar" com opção de desfazer.
- **Detalhes do restaurante:** resultado para o seu perfil, os 10 itens do checklist com data de verificação e número de respostas, "Quem já foi", atendimento em estrelas e mini mapa.
- **Avaliar acessibilidade:** checklist com as respostas Sim, Parcialmente, Não, Não se aplica e Não consegui verificar, além de estrelas de atendimento opcionais.
- **Favoritos, Minhas avaliações e Meu perfil** (seleção de uma ou mais necessidades de mobilidade).
- **Mapa:** todos os restaurantes, com zoom pelos botões **+** e **−** e popup com resumo e acesso aos detalhes.
- **Configurações:** tema claro/escuro, tamanho da fonte (80% a 140%), alto contraste, redução de animações, preferências da lista e contato de suporte.
- **Sobre o MoBite e Perguntas frequentes.**
- **Botão "Voltar ao início"** em todas as páginas internas.

### Indicadores de acessibilidade

Cada resultado usa **forma, cor e texto**, para não depender só da cor:

| Símbolo | Significado |
|---|---|
| ● Círculo | Funciona |
| ▲ Triângulo | Funciona com ressalva |
| ◆ Losango | Tem barreira |
| ■ Quadrado | Falta informação |

### Como o resultado muda conforme o perfil

Cada perfil de mobilidade (`NEC` em `dados.js`) considera apenas os itens do checklist que importam para ele. O resultado do restaurante para o perfil segue esta prioridade:

1. Se algum item relevante tem **barreira** → ◆ Tem barreira.
2. Senão, se algum item relevante não tem informação → ■ Falta informação.
3. Senão, se algum item relevante tem ressalva → ▲ Funciona com ressalva.
4. Senão → ● Funciona.

Cada item vira um resultado pela média das respostas: **Sim = 5**, **Parcialmente = 3**, **Não = 1**. "Não se aplica" e "Não consegui verificar" não entram na conta.

- Média **4 ou mais**: funciona.
- Média de **2,5 a 3,9**: ressalva.
- Média **abaixo de 2,5**: barreira.
- **Sem respostas**: falta informação.

Quando há mais de um perfil selecionado, valem os itens de todos eles. A ordem das listas prioriza o resultado do perfil e depois a distância (essa prioridade pode ser desligada em **Configurações**).

**Estrelas são só atendimento** e nunca entram no resultado de acessibilidade.

---

## Estrutura de arquivos

```
mobite/
├── index.html              Todas as páginas (seções com data-page) e a ordem dos scripts
├── README.md
├── css/
│   ├── style.css           Variáveis de cor, base, cabeçalho/menu, botões, cards e formulários
│   ├── paginas.css         Estilos de cada página e responsividade
│   └── temas.css           Tema escuro, alto contraste, campos, indicadores, mapa e configurações
├── js/
│   ├── dados.js            Dados fictícios: restaurantes, checklist (CRIT), perfis (NEC) e FAQ
│   ├── app.js              Núcleo: estado, regras de acessibilidade, cards, páginas, rotas e ações
│   ├── tema.js             Tema, tamanho da fonte, alto contraste, animações e preferências
│   ├── mapa.js             Leaflet: mini mapa dos detalhes e página Mapa
│   └── main.js             Inicialização (preenche listas e abre a página da URL)
└── assets/
    └── images/
        ├── logo.png        Logotipo oficial (não alterar cores nem proporção)
        └── restaurantes/   r1.svg … r10.svg (ilustrações dos restaurantes)
```

**A ordem dos scripts em `index.html` importa:** `dados.js` → `app.js` → `tema.js` → `mapa.js` → `main.js`.

### Navegação

A navegação usa o hash da URL, sem recarregar a página:

`#inicio` · `#restaurantes` · `#detalhes-ID` · `#favoritos` · `#avaliacoes` · `#perfil` · `#sobre` · `#faq` · `#configuracoes` · `#mapa`

Cada rota chama uma função em `PAGES`, em `app.js`. As páginas Configurações (`tema.js`) e Mapa (`mapa.js`) registram a sua própria função em `PAGES`.

---

## Como alterar

| Quero… | Onde mexer |
|---|---|
| Mudar cores | Variáveis em `:root` no início de `css/style.css` (e o tema escuro em `css/temas.css`) |
| Adicionar um restaurante | Novo objeto em `RESTAURANTES` (`js/dados.js`) e a imagem `assets/images/restaurantes/rID.svg` |
| Trocar as ilustrações por fotos | Substitua os arquivos `r1.svg` … `r10.svg` (ou ajuste o campo `img` em `dados.js`) |
| Alterar itens do checklist | `CRIT` em `dados.js` |
| Alterar quais itens importam para cada perfil | `NEC` em `dados.js` |
| Mudar as regras de resultado | Funções `status` e `resultado` em `js/app.js` |
| Mudar textos de Sobre e Configurações | `index.html` |
| Mudar perguntas frequentes | `FAQ` em `dados.js` |

**Atenção ao campo `s` de cada restaurante.** É uma string de 10 dígitos, um por item de `CRIT`, **na mesma ordem**. O dígito `0` significa sem informação, `1` e `2` barreira, `3` ressalva, `4` e `5` funciona. Se você adicionar ou remover itens em `CRIT`, ajuste a string `s` de todos os restaurantes.

---

## Dados, armazenamento e privacidade

- Somente o **tema e as configurações** são salvos no `localStorage` do navegador (chave `mobite_cfg`).
- Perfil, favoritos, restaurantes ocultados e avaliações ficam **apenas na memória** e voltam ao começo ao recarregar a página.
- A **localização** só é pedida quando você clica em "Usar minha localização" e **não é salva**. Sem ela, as distâncias aparecem como indisponíveis e o mapa usa o centro de São Paulo apenas como referência.
- As avaliações feitas no protótipo atualizam os indicadores na tela, mas não representam avaliações reais de estabelecimentos.

---

## O que depende de backend ou de serviços externos

Estas funcionalidades não existem no protótipo e exigem implementação futura:

| Funcionalidade | O que será necessário |
|---|---|
| Contas e login (avaliar, favoritar e ocultar exigem conta) | Autenticação e banco de dados de usuários |
| Salvar perfil, favoritos e avaliações entre sessões | API e banco de dados |
| Distância e busca por CEP | API de CEP (ex.: ViaCEP) e geocodificação |
| Fotos reais dos estabelecimentos | Armazenamento de imagens e moderação |
| Direito de resposta do restaurante | Perfil verificado de estabelecimento e moderação |
| Contagem real de visitas ("Quem já foi") e datas de verificação | Registro de visitas e avaliações no servidor |
| Proteção contra avaliação em massa | Regras antiabuso e verificação de contas |

---

## Acessibilidade da interface

- Navegação por teclado e link "Pular para o conteúdo".
- Foco visível, botões grandes e descrições alternativas nas imagens.
- Indicadores que não dependem apenas de cor.
- Tema escuro, alto contraste, ajuste de fonte e redução de animações.
- Layout responsivo para computador, tablet e celular.

---

## Equipe

| Integrante | Papel |
|---|---|
| José Henrique Guimarães Galvão Silva | Produto e desenvolvimento |
| Giovanna Bispo Da Silva | Front-end e design |
| Gabriella Pereira Rodrigues | Qualidade e testes |
| Diego Azevedo Dias Inacio | Dados e pesquisa |

Contato (fictício): contato@mobite.example

---

## Créditos e referências

- Mapas: [Leaflet](https://leafletjs.com/) e [OpenStreetMap](https://www.openstreetmap.org/copyright) (© colaboradores do OpenStreetMap).
- Checklist baseado em pontos da **ABNT NBR 9050** que podem ser conferidos sem equipamento.
