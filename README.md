# ♿ MOBITE

> Encontre restaurantes acessíveis perto de você, com informações confirmadas pela própria comunidade.

---

## 📑 Sumário

- [Visão Geral e Propósito](#-visão-geral-e-propósito)
- [Funcionalidades Principais](#-funcionalidades-principais)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Identidade Visual](#-identidade-visual)
- [Pré-requisitos](#-pré-requisitos)
- [Passo a Passo para Executar](#-passo-a-passo-para-executar)
- [Estrutura de Arquivos](#-estrutura-de-arquivos)
- [Como Contribuir](#-como-contribuir)
- [Licença e Créditos](#-licença-e-créditos)

---

## 💜 Visão Geral e Propósito

O **MOBITE** é uma plataforma focada em **acessibilidade urbana** que facilita a busca por restaurantes acessíveis para pessoas com mobilidade reduzida.

**Para quem é:**

- Cadeirantes
- Idosos
- Gestantes
- Pessoas com deficiência em membros inferiores
- Pais e mães com carrinho de bebê ou crianças de colo

**Impacto social:** sair para comer não deveria exigir tentativa e erro. O MOBITE promove **inclusão** e **praticidade** ao mostrar, antes da saída de casa, quais recursos de acessibilidade cada local realmente oferece. Os dados são confirmados pela comunidade, o que mantém as informações atualizadas e confiáveis.

---

## ✨ Funcionalidades Principais

- **Menu hambúrguer institucional completo:** painel lateral com boas-vindas e links para Início, Sobre o MOBITE, Para quem é, Como funciona, Recursos de acessibilidade, Nossa proposta, Comunidade, Equipe, FAQ e Contato.
- **Perfil do usuário:** nome, idade e tipo de necessidade de acessibilidade (cadeirante, idoso, gestante, membros inferiores, mãe/pai com carrinho de bebê ou outro).
- **Listagem de restaurantes próximos:** simulação de geolocalização, com cards ordenados por **maior nível de acessibilidade + menor distância**.
- **Favoritos (❤️) e Deslike (👎):** o coração salva o restaurante na aba Favoritos; o deslike move o card para o final da fila.
- **Detalhes e avaliação interativa:** modal com nota média, lista de recursos, avaliação de **0 a 5 estrelas** e confirmação de quais recursos realmente estavam disponíveis.
- **Acessibilidade na própria interface:** navegação por teclado, foco visível, rótulos ARIA, alto contraste e respeito a `prefers-reduced-motion`.
- **Persistência local:** perfil, favoritos e itens ocultados ficam salvos no `localStorage` do navegador.

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Uso |
| --- | --- |
| **HTML5** | Estrutura semântica e elemento `<dialog>` para o modal |
| **CSS3** | Layout responsivo (Grid/Flexbox) e variáveis CSS |
| **JavaScript (Vanilla ES6+)** | Lógica, ordenação, renderização e interações |
| **Git** | Controle de versão |
| **VS Code + Live Server** | Ambiente de desenvolvimento e teste local |

---

## 🎨 Identidade Visual

Visual limpo, acolhedor e moderno, com foco em alto contraste. A paleta é aplicada por variáveis CSS:

| Cor | Hexadecimal | Variável | Uso |
| --- | --- | --- | --- |
| ![#a2ad91](https://placehold.co/20x20/a2ad91/a2ad91.png) Verde Sálvia | `#a2ad91` | `--sage` | Cabeçalho, badges, destaques |
| ![#3a2d32](https://placehold.co/20x20/3a2d32/3a2d32.png) Marrom/Grafite Escuro | `#3a2d32` | `--dark` | Textos, bordas e botões principais |
| ![#ffe3dc](https://placehold.co/20x20/ffe3dc/ffe3dc.png) Pêssego Suave | `#ffe3dc` | `--soft` | Fundo da página, cards e modal |

```css
:root {
  --sage: #a2ad91;
  --dark: #3a2d32;
  --soft: #ffe3dc;
}
```

---

## 📋 Pré-requisitos

- Navegador web moderno (Chrome, Edge, Firefox ou Safari atualizados)
- [Visual Studio Code](https://code.visualstudio.com/)
- Extensão **Live Server** (Ritwick Dey) instalada no VS Code
- [Git](https://git-scm.com/) instalado

---

## 🚀 Passo a Passo para Executar

**1. Clone o repositório**

```bash
git clone https://github.com/SEU-USUARIO/mobite.git
```

**2. Acesse a pasta do projeto**

```bash
cd mobite
```

**3. Abra no VS Code**

```bash
code .
```

**4. Rode com o Live Server**

Clique com o botão direito em `index.html` e selecione **Open with Live Server** (ou clique em **Go Live** na barra inferior do VS Code). O site abrirá no navegador, normalmente em `http://127.0.0.1:5500`.

> 💡 Como o projeto usa apenas HTML, CSS e JavaScript puros, também é possível abrir o `index.html` com dois cliques, sem instalar nada.

---

## 📁 Estrutura de Arquivos

```
mobite/
├── index.html      # Estrutura da página, menu, abas e modal
├── style.css       # Estilos, paleta de cores e responsividade
├── script.js       # Dados, ordenação, favoritos, avaliação e menu
├── assets/         # (opcional) imagens, ícones e logotipos
└── README.md       # Documentação do projeto
```

---

## 🤝 Como Contribuir

Contribuições são muito bem-vindas! Siga o fluxo padrão:

1. **Faça um Fork** do repositório.
2. **Clone** o seu fork:
   ```bash
   git clone https://github.com/SEU-USUARIO/mobite.git
   ```
3. **Crie uma branch** para a sua feature:
   ```bash
   git checkout -b feature/nome-da-feature
   ```
4. **Faça as alterações** e o **commit** com uma mensagem clara:
   ```bash
   git add .
   git commit -m "feat: descreve brevemente a sua alteração"
   ```
5. **Envie** a branch para o seu fork:
   ```bash
   git push origin feature/nome-da-feature
   ```
6. **Abra um Pull Request** descrevendo o que foi feito e por quê.

**Boas práticas:** mantenha as cores da paleta oficial, preserve o contraste e a navegação por teclado, e teste o layout em telas pequenas.

---

## 📄 Licença e Créditos

Distribuído sob a licença **MIT**. Consulte o arquivo `LICENSE` para mais informações.

**Equipe de desenvolvimento**

| Nome | Função | Contato |
| --- | --- | --- |
| _Nome do(a) integrante_ | _Design / Desenvolvimento / Pesquisa_ | _link ou e-mail_ |
| _Nome do(a) integrante_ | _Design / Desenvolvimento / Pesquisa_ | _link ou e-mail_ |

---

<p align="center">Feito com 💜 para tornar a cidade mais acessível.</p>
