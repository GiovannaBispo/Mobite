/* =========================================================
   1. RECURSOS DE ACESSIBILIDADE
   ========================================================= */

/*
   FEAT guarda os recursos de acessibilidade.

   A chave (ex: "ramp") é usada internamente pelo sistema.
   O texto depois dos dois pontos é o que aparece para o usuário.
*/

const FEAT = {
    ramp: "♿ Rampas",
    wc: "🚻 Banheiro acessível",
    elev: "🛗 Elevador",
    rail: "🪜 Corrimão",
    kid: "🪑 Cadeiras infantis",
    wide: "↔️ Corredores largos"
};


/* =========================================================
   2. LISTA DE RESTAURANTES
   ========================================================= */

/*
   R = lista de restaurantes.

   Cada restaurante possui:
   id  = identificador
   n   = nome
   d   = distância em km
   r   = nota
   c   = quantidade de avaliações
   f   = recursos de acessibilidade disponíveis
*/

const R = [

    {
        id: 1,
        n: "Casa Verde Bistrô",
        d: 0.4,
        r: 4.6,
        c: 32,
        f: ["ramp", "wc", "elev", "rail", "kid", "wide"]
    },

    {
        id: 2,
        n: "Cantina da Vó Lia",
        d: 0.9,
        r: 4.2,
        c: 18,
        f: ["ramp", "wc", "rail", "kid"]
    },

    {
        id: 3,
        n: "Sabor de Praça",
        d: 0.2,
        r: 3.4,
        c: 11,
        f: ["ramp"]
    },

    {
        id: 4,
        n: "Pizzaria Bella Rota",
        d: 1.5,
        r: 4.8,
        c: 40,
        f: ["ramp", "wc", "elev", "rail", "wide"]
    },

    {
        id: 5,
        n: "Café do Largo",
        d: 0.6,
        r: 3.9,
        c: 9,
        f: ["ramp", "kid", "rail"]
    },

    {
        id: 6,
        n: "Churrascaria Serra Alta",
        d: 2.8,
        r: 4.1,
        c: 25,
        f: ["ramp", "wc", "elev"]
    },

    {
        id: 7,
        n: "Boteco do Zé",
        d: 0.3,
        r: 2.8,
        c: 14,
        f: []
    },

    {
        id: 8,
        n: "Sushi Sakura",
        d: 1.1,
        r: 4.4,
        c: 21,
        f: ["wc", "elev", "wide"]
    }

];


/* =========================================================
   3. LOCALSTORAGE
   ========================================================= */

/*
   O localStorage permite salvar informações no navegador.

   Exemplo:
   - restaurantes favoritos
   - perfil do usuário
   - restaurantes ocultados
*/


const store = {

    /*
       Recupera uma informação salva.

       k = nome da informação
       d = valor padrão caso não exista
    */
    get(k, d) {

        try {

            const v = localStorage.getItem(k);

            return v
                ? JSON.parse(v)
                : d;

        } catch (e) {

            return d;

        }
    },


    /*
       Salva uma informação no navegador.
    */
    set(k, v) {

        try {

            localStorage.setItem(
                k,
                JSON.stringify(v)
            );

        } catch (e) {

            // Caso o navegador não permita salvar.
        }
    }

};


/* =========================================================
   4. VARIÁVEIS DO SISTEMA
   ========================================================= */

/*
   favs = restaurantes favoritos
   hidden = restaurantes que o usuário ocultou
   profile = perfil do usuário
   rating = nota que está sendo dada
   cur = restaurante atualmente selecionado
*/

let favs = store.get("mb_favs", []);

let hidden = store.get("mb_hidden", []);

let profile = store.get("mb_profile", null);

let rating = 0;

let cur = null;


/* =========================================================
   5. FUNÇÃO $ PARA BUSCAR ELEMENTOS
   ========================================================= */

/*
   Essa função é um atalho para:

   document.querySelector()

   Em vez de escrever:

   document.querySelector("#feed")

   podemos escrever:

   $("#feed")
*/

const $ = s => document.querySelector(s);


/* =========================================================
   6. FUNÇÃO DE SEGURANÇA PARA TEXTOS
   ========================================================= */

/*
   Escapa caracteres especiais do HTML.

   Isso evita que um texto inserido pelo usuário
   seja interpretado como código HTML.
*/

const esc = s =>
    String(s).replace(
        /[&<>"]/g,
        c => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;"
        }[c])
    );


/* =========================================================
   7. MOSTRAR ESTRELAS
   ========================================================= */

/*
   Recebe uma nota.

   Exemplo:

   stars(4)

   retorna:

   ★★★★☆

*/

const stars = v =>
    "★".repeat(Math.round(v)) +
    "☆".repeat(5 - Math.round(v));


/* =========================================================
   8. NOTIFICAÇÃO TOAST
   ========================================================= */

/*
   Mostra uma pequena mensagem na parte inferior
   da tela.

   Exemplo:

   "Perfil salvo! 💜"
*/

function toast(m) {

    const t = $("#toast");

    t.textContent = m;

    t.hidden = false;

    clearTimeout(t._t);

    t._t = setTimeout(
        () => t.hidden = true,
        2500
    );

}


/* =========================================================
   9. CÁLCULO DE ACESSIBILIDADE
   ========================================================= */

/*
   Cria uma pontuação para cada restaurante.

   O sistema considera:

   - quantidade de recursos de acessibilidade
   - distância
   - avaliação

   Quanto maior o resultado,
   melhor será a posição na lista.
*/

function score(r) {

    return (
        r.f.length / 6 * 0.65
        -
        (r.d / 3) * 0.35
        +
        r.r / 5 * 0.05
    );

}


/* =========================================================
   10. ORDENAÇÃO DOS RESTAURANTES
   ========================================================= */

/*
   Organiza os restaurantes.

   Primeiro ficam os restaurantes normais.

   Os restaurantes ocultados pelo usuário
   são enviados para o final.

   Depois disso, os restaurantes são
   organizados pela pontuação.
*/

function sorted() {

    return [...R].sort(

        (a, b) =>

            (
                hidden.includes(a.id)
                -
                hidden.includes(b.id)
            )

            ||

            score(b) - score(a)

    );

}


/* =========================================================
   11. CRIAÇÃO DOS CARDS
   ========================================================= */

/*
   Essa função transforma os dados de um restaurante
   em HTML.

   É ela que cria visualmente cada card.
*/

function card(r) {

    /*
       Verifica se o restaurante está favoritado.
    */
    const isF = favs.includes(r.id);


    /*
       Verifica se o restaurante foi ocultado.
    */
    const isH = hidden.includes(r.id);


    /*
       Retorna o HTML do card.
    */

    return `
        <li class="card ${isH ? "dim" : ""}">

            <h3>
                ${esc(r.n)}
            </h3>


            <div class="meta">

                <span aria-label="Nota ${r.r.toFixed(1)} de 5">

                    ${stars(r.r)}

                    ${r.r.toFixed(1)}

                </span>


                <span>
                    ${r.d.toFixed(1)} km
                </span>

            </div>


            <ul class="tags" aria-label="Recursos">

                ${
                    r.f.length

                    ?

                    r.f
                        .map(
                            k =>
                                `<li class="tag">
                                    ${FEAT[k]}
                                </li>`
                        )
                        .join("")

                    :

                    `<li class="tag">
                        Sem recursos informados
                    </li>`
                }

            </ul>


            ${
                isH
                ?
                "<em>Movido para o fim da fila</em>"
                :
                ""
            }


            <div class="actions">


                <!-- Botão de favorito -->

                <button
                    class="btn alt ${isF ? "on" : ""}"
                    data-a="fav"
                    data-id="${r.id}"
                    aria-pressed="${isF}"
                    aria-label="Favoritar ${esc(r.n)}"
                >
                    ${isF ? "❤️" : "🤍"}
                </button>


                <!-- Botão de descurtir -->

                <button
                    class="btn alt"
                    data-a="dis"
                    data-id="${r.id}"
                    aria-label="Descurtir ${esc(r.n)}"
                >
                    👎
                </button>


                <!-- Botão de detalhes -->

                <button
                    class="btn"
                    data-a="det"
                    data-id="${r.id}"
                >
                    Detalhes
                </button>


            </div>

        </li>
    `;

}


/* =========================================================
   12. RENDERIZAÇÃO DA PÁGINA
   ========================================================= */

/*
   Atualiza o conteúdo da tela.

   Essa função é chamada sempre que alguma informação
   muda, como:

   - favoritar restaurante
   - ocultar restaurante
   - salvar perfil
   - avaliar restaurante
*/

function render() {

    /*
       Mostra os restaurantes na tela principal.
    */

    $("#feed").innerHTML =
        sorted()
            .map(card)
            .join("");


    /*
       Filtra apenas os restaurantes favoritos.
    */

    const fl =
        R.filter(
            r => favs.includes(r.id)
        );


    /*
       Mostra os favoritos.
    */

    $("#favList").innerHTML =
        fl
            .map(card)
            .join("");


    /*
       Mostra ou esconde a mensagem
       "Nenhum favorito".
    */

    $("#favEmpty").hidden =
        fl.length > 0;


    /*
       Mostra a quantidade de favoritos.
    */

    $("#favCount").textContent =
        fl.length
        ? `(${fl.length})`
        : "";


    /*
       Mensagem do perfil.
    */

    $("#perfilMsg").textContent =

        profile

        ?

        `Olá, ${profile.nome || "visitante"}! Priorizamos os locais mais acessíveis e próximos.`

        :

        "Ordenados por maior acessibilidade e menor distância.";

}


/* =========================================================
   13. CLIQUES NOS BOTÕES DOS CARDS
   ========================================================= */

/*
   Captura os cliques feitos nos botões dos restaurantes.
*/

document.addEventListener("click", e => {

    /*
       Procura um elemento que tenha
       o atributo data-a.
    */

    const b =
        e.target.closest("[data-a]");


    /*
       Se não encontrou, não faz nada.
    */

    if (!b) return;


    /*
       Pega o ID do restaurante.
    */

    const id =
        +b.dataset.id;


    /*
       Descobre qual ação foi clicada.

       fav = favorito
       dis = descurtir
       det = detalhes
    */

    const a =
        b.dataset.a;


    /* -------------------------
       FAVORITAR
       ------------------------- */

    if (a === "fav") {

        /*
           Se já é favorito, remove.

           Se não é, adiciona.
        */

        favs = favs.includes(id)

            ?

            favs.filter(x => x !== id)

            :

            [...favs, id];


        /*
           Salva no navegador.
        */

        store.set(
            "mb_favs",
            favs
        );


        /*
           Atualiza a tela.
        */

        render();
    }


    /* -------------------------
       DESCURTIR / OCULTAR
       ------------------------- */

    if (a === "dis") {

        /*
           Adiciona o restaurante
           à lista de ocultados.
        */

        if (!hidden.includes(id)) {

            hidden.push(id);

        }


        /*
           Salva no navegador.
        */

        store.set(
            "mb_hidden",
            hidden
        );


        /*
           Atualiza a tela.
        */

        render();


        /*
           Mostra mensagem.
        */

        toast(
            "Restaurante movido para o fim da lista."
        );
    }


    /* -------------------------
       DETALHES
       ------------------------- */

    if (a === "det") {

        openDetail(id);

    }

});


/* =========================================================
   14. SISTEMA DE ABAS
   ========================================================= */

/*
   Existem três visualizações:

   home   = página inicial
   perfil = perfil do usuário
   fav    = favoritos
*/

function show(v) {

    /*
       Esconde todas as páginas
       menos a selecionada.
    */

    ["home", "perfil", "fav"].forEach(
        x => {

            $("#v-" + x).hidden =
                x !== v;

        }
    );


    /*
       Atualiza o botão ativo do menu.
    */

    document
        .querySelectorAll("#tabs button")
        .forEach(b => {

            if (b.dataset.view === v) {

                b.setAttribute(
                    "aria-current",
                    "page"
                );

            } else {

                b.removeAttribute(
                    "aria-current"
                );

            }

        });

}


/* =========================================================
   15. CLIQUE NAS ABAS
   ========================================================= */

$("#tabs").addEventListener(
    "click",
    e => {

        const b =
            e.target.closest("button");

        if (b) {

            show(
                b.dataset.view
            );

        }

    }
);


/* =========================================================
   16. ATUALIZAÇÃO DA LOCALIZAÇÃO
   ========================================================= */

/*
   Quando o usuário clica para atualizar a localização,
   o sistema altera as distâncias dos restaurantes.

   Neste protótipo, a localização é SIMULADA.
*/

$("#relocate").onclick = () => {


    /*
       Altera aleatoriamente as distâncias.
    */

    R.forEach(r => {

        r.d = Math.max(

            0.1,

            +(
                r.d +
                (Math.random() - 0.5) * 1.6
            ).toFixed(1)

        );

    });


    /*
       Lista de locais fictícios.
    */

    const ruas = [

        "Av. Paulista",

        "Rua Augusta",

        "Pça. da República",

        "Parque Ibirapuera"

    ];


    /*
       Escolhe uma localização aleatória.
    */

    $("#locText").textContent =

        "📍 " +

        ruas[
            Math.floor(
                Math.random() * ruas.length
            )
        ] +

        ", São Paulo (simulada)";


    /*
       Atualiza os restaurantes.
    */

    render();


    /*
       Mostra mensagem.
    */

    toast(
        "Localização atualizada; lista reordenada."
    );

};


/* =========================================================
   17. CARREGAR PERFIL SALVO
   ========================================================= */

/*
   Se o usuário já possui um perfil salvo,
   preenche automaticamente os campos.
*/

if (profile) {

    $("#nome").value =
        profile.nome || "";

    $("#idade").value =
        profile.idade || "";


    /*
       Marca as necessidades que já estavam selecionadas.
    */

    document
        .querySelectorAll("[name=need]")
        .forEach(c => {

            c.checked =
                (profile.needs || [])
                    .includes(c.value);

        });

}


/* =========================================================
   18. SALVAR PERFIL
   ========================================================= */

$("#perfilForm").onsubmit = e => {

    /*
       Impede o formulário de recarregar a página.
    */

    e.preventDefault();


    /*
       Cria o objeto do perfil.
    */

    profile = {

        nome:
            $("#nome")
                .value
                .trim(),

        idade:
            $("#idade")
                .value,

        needs:
            [
                ...document
                    .querySelectorAll(
                        "[name=need]:checked"
                    )
            ]
            .map(c => c.value)

    };


    /*
       Salva o perfil no navegador.
    */

    store.set(
        "mb_profile",
        profile
    );


    /*
       Atualiza a página.
    */

    render();


    /*
       Mostra confirmação.
    */

    toast(
        "Perfil salvo! 💜"
    );

};


/* =========================================================
   19. SISTEMA DE ESTRELAS
   ========================================================= */

const stEl = $("#stars");


/*
   Cria os botões das estrelas.

   O sistema cria de 0 a 5.
*/

for (let i = 0; i <= 5; i++) {

    stEl.insertAdjacentHTML(

        "beforeend",

        `
        <button
            type="button"
            class="star"
            role="radio"
            aria-checked="false"
            data-v="${i}"
            aria-label="${i} estrela${i === 1 ? "" : "s"}"
        >
            ${i === 0 ? "0" : "★" + (i > 1 ? i : "")}
        </button>
        `

    );

}


/* =========================================================
   20. CLIQUE NAS ESTRELAS
   ========================================================= */

stEl.onclick = e => {

    const b =
        e.target.closest(".star");


    if (!b) return;


    /*
       Guarda a nota escolhida.
    */

    rating =
        +b.dataset.v;


    /*
       Atualiza visualmente a estrela selecionada.
    */

    stEl
        .querySelectorAll(".star")
        .forEach(s => {

            s.setAttribute(

                "aria-checked",

                +s.dataset.v === rating

            );

        });

};


/* =========================================================
   21. ABRIR DETALHES DO RESTAURANTE
   ========================================================= */

function openDetail(id) {

    /*
       Procura o restaurante pelo ID.
    */

    cur =
        R.find(
            r => r.id === id
        );


    /*
       Zera a avaliação anterior.
    */

    rating = 0;


    /*
       Desmarca todas as estrelas.
    */

    stEl
        .querySelectorAll(".star")
        .forEach(s => {

            s.setAttribute(
                "aria-checked",
                "false"
            );

        });


    /*
       Mostra o nome do restaurante.
    */

    $("#dTitle").textContent =
        cur.n;


    /*
       Mostra nota, quantidade de avaliações
       e distância.
    */

    $("#dMeta").innerHTML = `

        <strong>
            ${stars(cur.r)}
            ${cur.r.toFixed(1)}
        </strong>

        (${cur.c} avaliações)

        ·

        ${cur.d.toFixed(1)} km

    `;


    /*
       Mostra as características de acessibilidade.
    */

    $("#dTags").innerHTML =

        cur.f.length

        ?

        cur.f
            .map(
                k =>
                    `<li class="tag">
                        ${FEAT[k]}
                    </li>`
            )
            .join("")

        :

        "<li>Nenhum recurso informado.</li>";


    /*
       Cria os checkboxes para o usuário
       confirmar os recursos.
    */

    $("#dChecks").innerHTML =

        cur.f.length

        ?

        cur.f
            .map(
                k => `
                    <label>
                        <input
                            type="checkbox"
                            name="conf"
                            value="${k}"
                            checked
                        >

                        ${FEAT[k]}

                    </label>
                `
            )
            .join("")

        :

        "<p>Sem recursos para confirmar.</p>";


    /*
       Abre a janela de detalhes.
    */

    $("#detail").showModal();

}


/* =========================================================
   22. FECHAR JANELA DE DETALHES
   ========================================================= */

$("#dClose").onclick = () => {

    $("#detail").close();

};


/* =========================================================
   23. ENVIAR AVALIAÇÃO
   ========================================================= */

$("#rateForm").onsubmit = e => {

    /*
       Evita recarregar a página.
    */

    e.preventDefault();


    /*
       Calcula uma nova média.

       Exemplo:

       nota antiga = 4.5
       avaliações = 10
       nova nota = 5

       O sistema recalcula a média.
    */

    cur.r =

        (
            cur.r * cur.c
            +
            rating
        )
        /
        (cur.c + 1);


    /*
       Aumenta o número de avaliações.
    */

    cur.c++;


    /*
       Descobre quais recursos
       foram desmarcados pelo usuário.
    */

    const missing =

        cur.f.filter(

            k =>

                !document.querySelector(
                    `[name=conf][value=${k}]`
                ).checked

        );


    /*
       Fecha a janela.
    */

    $("#detail").close();


    /*
       Atualiza os cards.
    */

    render();


    /*
       Mostra uma mensagem.
    */

    toast(

        missing.length

        ?

        `Avaliação enviada. ${missing.length} recurso(s) marcado(s) como indisponível(is).`

        :

        "Avaliação enviada. Obrigado! 💜"

    );

};


/* =========================================================
   24. MENU LATERAL
   ========================================================= */

const dr = $("#drawer");

const sc = $("#scrim");

const mb = $("#menuBtn");


/* -------------------------
   ABRIR MENU
   ------------------------- */

function openMenu() {

    /*
       Adiciona a classe que abre o menu.
    */

    dr.classList.add("open");


    /*
       Mostra o fundo escuro.
    */

    sc.classList.add("show");


    /*
       Informa aos leitores de tela
       que o menu está aberto.
    */

    mb.setAttribute(
        "aria-expanded",
        "true"
    );


    /*
       Coloca o foco no botão de fechar.
    */

    $("#closeBtn").focus();

}


/* -------------------------
   FECHAR MENU
   ------------------------- */

function closeMenu() {

    dr.classList.remove("open");

    sc.classList.remove("show");


    mb.setAttribute(
        "aria-expanded",
        "false"
    );


    /*
       Devolve o foco ao botão do menu.
    */

    mb.focus();

}


/* -------------------------
   EVENTOS DO MENU
   ------------------------- */

mb.onclick = openMenu;

$("#closeBtn").onclick = closeMenu;

sc.onclick = closeMenu;


/*
   Permite fechar o menu
   pressionando ESC.
*/

document.addEventListener(
    "keydown",
    e => {

        if (
            e.key === "Escape" &&
            dr.classList.contains("open")
        ) {

            closeMenu();

        }

    }
);


/* =========================================================
   25. INFORMAÇÕES INSTITUCIONAIS
   ========================================================= */

/*
   Aqui ficam os textos que aparecem no
   menu institucional do MOBITE.

   Cada item possui:

   [0] = identificador
   [1] = título
   [2] = conteúdo
*/

const INFO = [

    [
        "sobre",
        "Sobre o MOBITE",
        "O MOBITE reúne informações de acessibilidade de restaurantes, coletadas e confirmadas pela própria comunidade."
    ],

    [
        "publico",
        "Para quem é",
        "Cadeirantes, idosos, gestantes, pessoas com deficiência em membros inferiores, mães e pais com carrinho de bebê e qualquer pessoa com mobilidade reduzida."
    ],

    [
        "como",
        "Como funciona",
        "Você vê os restaurantes mais próximos, ordenados por acessibilidade e distância. Favorite, oculte e avalie para melhorar as recomendações."
    ],

    [
        "recursos",
        "Recursos de acessibilidade",
        "Rampas, banheiro acessível, elevador, corrimão, cadeiras infantis e corredores largos, além de navegação por teclado, alto contraste e leitores de tela."
    ],

    [
        "proposta",
        "Nossa proposta",
        "Tornar a busca por lugares acessíveis rápida, confiável e colaborativa, sem depender de tentativa e erro."
    ],

    [
        "comunidade",
        "Comunidade",
        "Cada avaliação confirma se os recursos informados realmente existem, mantendo os dados atualizados por quem usa."
    ],

    [
        "equipe",
        "Equipe",
        "Equipe do projeto MOBITE: pessoas de design, desenvolvimento e pesquisa unidas por inclusão. (Adicione aqui os nomes.)"
    ],

    [
        "faq",
        "FAQ",
        "<strong>O MOBITE é gratuito?</strong> Sim, neste protótipo. <strong>Meus dados ficam salvos?</strong> Apenas no seu navegador. <strong>Como oculto um local?</strong> Use o botão 👎 no card."
    ],

    [
        "contato",
        "Contato",
        "Escreva para contato@mobite.example (endereço fictício do protótipo)."
    ]

];


/* =========================================================
   26. CRIAÇÃO DO MENU INSTITUCIONAL
   ========================================================= */

/*
   Cria os links do menu.

   O primeiro link é "Início".
*/

$("#menuList").innerHTML =

    `
    <li>
        <a href="#main" data-h="home">
            Início
        </a>
    </li>
    `

    +

    INFO
        .map(
            i => `
                <li>
                    <a href="#s-${i[0]}">
                        ${i[1]}
                    </a>
                </li>
            `
        )
        .join("");


/* =========================================================
   27. CRIAÇÃO DAS SEÇÕES INSTITUCIONAIS
   ========================================================= */

/*
   Cria as seções "Sobre", "Para quem é",
   "Como funciona", "Equipe", etc.
*/

$("#info").innerHTML =

    INFO
        .map(
            i => `

                <section id="s-${i[0]}">

                    <h2>
                        ${i[1]}
                    </h2>

                    <p>
                        ${i[2]}
                    </p>

                </section>

            `
        )
        .join("");


/* =========================================================
   28. CLIQUE NOS LINKS DO MENU
   ========================================================= */

$("#menuList").onclick = e => {

    const a =
        e.target.closest("a");


    if (!a) return;


    /*
       Se clicou em "Início",
       volta para a página inicial.
    */

    if (a.dataset.h) {

        show("home");

    }


    /*
       Fecha o menu lateral.
    */

    closeMenu();

};


/* =========================================================
   29. INICIALIZAÇÃO DO SITE
   ========================================================= */

/*
   Quando o JavaScript termina de carregar,
   chama render() para montar os restaurantes
   na tela.
*/

render();