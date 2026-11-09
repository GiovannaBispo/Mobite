/* app.js – núcleo do MoBite: estado, regras de acessibilidade por perfil, cards, páginas, navegação,
   ações (favoritar, dislike, avaliar), perfil e filtros. Depende de dados.js.
   Tema/fonte: tema.js · Mapas: mapa.js · Inicialização: main.js */

/* ===== 1. Utilitários e estado ===== */
const $ = (s, e = document) => e.querySelector(s), $$ = (s, e = document) => [...e.querySelectorAll(s)];
const S = { cfg: { tema: "claro", fonte: 100, contraste: false, anim: false, prio: true, datas: true },
  perfil: { nome: "", idade: "", needs: [], outra: "" }, favs: [], ocultos: [], avals: [], cep: "", pos: null }; // só "cfg" é salvo
try { Object.assign(S.cfg, JSON.parse(localStorage.getItem("mobite_cfg"))) } catch { }
const persist = () => { try { localStorage.setItem("mobite_cfg", JSON.stringify(S.cfg)) } catch { } };
let F = { q: "", nota: 0, dist: 0, cat: "", acess: "", fav: false }; // filtros da página de restaurantes
let H = "todos"; // opção ativa da descoberta na página inicial
const toggle = (arr, id) => arr.includes(id) ? arr.filter(x => x != id) : [...arr, id];

/* ===== 2. Regras de acessibilidade (o resultado muda conforme o perfil) ===== */
const PONTOS = { sim: 5, parcial: 3, nao: 1 }; // "na" e "nv" não entram na conta
const ROT = { ok: "Funciona", warn: "Funciona com ressalva", bar: "Tem barreira", nd: "Falta informação" };
const FORMA = { ok: "●", warn: "▲", bar: "◆", nd: "■" }; // círculo, triângulo, losango, quadrado
const ind = s => `<span class="ind s-${s}"><i aria-hidden="true">${FORMA[s]}</i>${ROT[s]}</span>`;

// Resposta de um item = dado de exemplo + avaliações feitas neste protótipo
function crit(r, k) {
  const d = +r.s[CRIT.findIndex(c => c.k == k)], mine = S.avals.filter(a => a.rid == r.id && PONTOS[a.resp[k]]);
  let m = d, n = d ? Math.ceil(r.v / 2) || 1 : 0;
  mine.forEach(a => { m = (m * n + PONTOS[a.resp[k]]) / (n + 1); n++ });
  return { m, n, d: mine.length ? mine.at(-1).data : r.d };
}
const status = c => !c.n ? "nd" : c.m >= 4 ? "ok" : c.m >= 2.5 ? "warn" : "bar";
const rel = () => [...new Set(S.perfil.needs.flatMap(n => NEC[n].crit))]; // itens que importam ao perfil
// Resultado para o perfil: barreira > falta informação > ressalva > funciona
function resultado(r) {
  const ks = rel(); if (!ks.length) return null;
  const st = ks.map(k => status(crit(r, k)));
  return st.includes("bar") ? "bar" : st.includes("nd") ? "nd" : st.includes("warn") ? "warn" : "ok";
}
const RANK = { ok: 3, warn: 2, nd: 1, bar: 0 };
const dist = r => S.pos ? 2 * 6371 * Math.asin(Math.sqrt(Math.sin((r.lat - S.pos.lat) * Math.PI / 360) ** 2 +
  Math.cos(S.pos.lat * Math.PI / 180) * Math.cos(r.lat * Math.PI / 180) * Math.sin((r.lng - S.pos.lng) * Math.PI / 360) ** 2)) : null;
const porDist = (a, b) => (dist(a) ?? 0) - (dist(b) ?? 0);
// Ordem: compatibilidade com o perfil (se a preferência estiver ligada) e depois distância
const ord = rs => [...rs].sort((a, b) => S.cfg.prio && S.perfil.needs.length ? RANK[resultado(b)] - RANK[resultado(a)] || porDist(a, b) : porDist(a, b));
const visitas = r => r.v + S.avals.filter(a => a.rid == r.id).length;
function atend(r) { // estrelas = SOMENTE atendimento
  let m = r.nota, n = r.v; S.avals.filter(a => a.rid == r.id && a.atend).forEach(a => { m = (m * n + a.atend) / (n + 1); n++ });
  return { m, n };
}
const estrelas = m => `<span class="est" role="img" aria-label="${m.toFixed(1)} de 5">${"★".repeat(Math.round(m))}${"☆".repeat(5 - Math.round(m))}</span>`;

/* ===== 3. Cards e listas ===== */
function card(r) {
  const f = S.favs.includes(r.id), o = S.ocultos.includes(r.id), d = dist(r), res = resultado(r), a = atend(r);
  return `<article class="card"><img class="foto" src="${r.img}" alt="Ilustração de ${r.nome}" loading="lazy">
  <div class="corpo"><h3>${r.nome}</h3>
  <p class="meta">${r.tipo} · ${d == null ? "distância indisponível" : d.toFixed(1) + " km"}</p>
  <p>${res ? `<span class="meta">Para o seu perfil:</span><br>${ind(res)}` : '<span class="meta">Escolha seu perfil para ver a resposta de acessibilidade.</span>'}</p>
  <p class="meta">${S.cfg.datas ? `Verificado em ${r.d || "—"} · ` : ""}<span class="est">★</span> ${a.n ? a.m.toFixed(1) + " atendimento" : "sem avaliação de atendimento"}</p>
  <div class="acoes"><button class="btn" data-a="ver" data-id="${r.id}">Ver detalhes</button>
  <button class="ic ${f ? "on" : ""}" data-a="fav" data-id="${r.id}" aria-pressed="${f}" aria-label="${f ? "Remover dos favoritos" : "Favoritar"}: ${r.nome}">${f ? "♥" : "♡"}</button>
  <button class="ic" data-a="dis" data-id="${r.id}" aria-label="${o ? "Restaurar" : "Não recomendar"}: ${r.nome}">${o ? "↩" : "👎"}</button></div></div></article>`;
}
const lista = (rs, el) => el.innerHTML = rs.map(card).join("") || '<p class="vazio">Nenhum resultado por aqui ainda.</p>';
const filtrados = () => { const q = F.q.toLowerCase();
  return RESTAURANTES.filter(r => !S.ocultos.includes(r.id) && (!q || (r.nome + r.end + r.tipo).toLowerCase().includes(q)) && atend(r).m >= F.nota &&
    (!F.cat || r.tipo == F.cat) && (!F.dist || dist(r) == null || dist(r) <= F.dist) && (!F.acess || status(crit(r, F.acess)) == "ok") && (!F.fav || S.favs.includes(r.id))) };

/* ===== 4. Páginas (cada função desenha uma página; configuracoes e mapa ficam em tema.js e mapa.js) ===== */
const PAGES = {
  inicio() { // descoberta: categorias, mais bem avaliados e mais próximos na mesma listagem
    $$("[data-h]").forEach(b => b.setAttribute("aria-pressed", b.dataset.h == H));
    let rs = RESTAURANTES.filter(r => !S.ocultos.includes(r.id) && (H == "todos" || H == "top" || H == "perto" || r.tipo == H));
    rs = H == "top" ? rs.sort((a, b) => atend(b).m - atend(a).m) : H == "perto" ? rs.sort(porDist) : ord(rs);
    $("#aviso-loc").hidden = H != "perto" || !!S.pos;
    lista(rs, $("#descoberta"));
  },
  restaurantes(_, keep) {
    if (!keep) ["q", "nota", "dist", "cat", "acess"].forEach(n => $("#filtros")[n].value = F[n]), $("#filtros").fav.checked = F.fav;
    lista(ord(filtrados()), $("#lista-rest"));
    const o = RESTAURANTES.filter(r => S.ocultos.includes(r.id));
    $("#ocultos").hidden = !o.length; $("#ocultos h2").textContent = `Ocultados por você (${o.length})`; lista(o, $("#lista-ocultos"));
  },
  favoritos() { lista(RESTAURANTES.filter(r => S.favs.includes(r.id)), $("#lista-favs")) },
  avaliacoes() {
    const O = Object.fromEntries(OPC);
    $("#lista-av").innerHTML = S.avals.map(a => { const r = RESTAURANTES.find(x => x.id == a.rid);
      return `<article class="card corpo"><h3>${r.nome}</h3><p class="meta">Avaliado em ${a.data}</p>
      <ul>${Object.entries(a.resp).filter(([, v]) => v != "nv").map(([k, v]) => `<li>${NOME[k]}: <b>${O[v]}</b></li>`).join("")}</ul>
      ${a.atend ? `<p>Atendimento: ${estrelas(a.atend)}</p>` : ""}<div class="acoes"><button class="btn sec" data-a="edit" data-id="${r.id}" data-av="${a.id}">Editar</button>
      <button class="btn sec" data-a="del" data-av="${a.id}">Excluir</button></div></article>` }).join("") || '<p class="vazio">Você ainda não avaliou nenhum local.</p>';
  },
  perfil(_, keep) {
    const p = S.perfil, f = $("#form-perfil");
    if (!keep) { f.nome.value = p.nome; f.idade.value = p.idade; f.outra.value = p.outra; $$("[name=need]", f).forEach(i => i.checked = p.needs.includes(i.value)) }
    $("#perfil-favs").innerHTML = S.favs.map(id => `<a class="chip" href="#detalhes-${id}">♥ ${RESTAURANTES.find(r => r.id == id).nome}</a>`).join("") || "Nenhum favorito ainda.";
  },
  detalhes(id) {
    quitarMapa("mapa-mini");
    const r = RESTAURANTES.find(x => x.id == id); if (!r) return location.hash = "restaurantes";
    const f = S.favs.includes(r.id), d = dist(r), ks = rel(), res = resultado(r), a = atend(r);
    $("#det").innerHTML = `<img class="foto grande" src="${r.img}" alt="Ilustração de ${r.nome}">
    <h1>${r.nome}</h1><p class="meta">${r.tipo} · ${d == null ? "distância indisponível" : d.toFixed(1) + " km"} · 📍 ${r.end} · 🕒 ${r.hor} (dados fictícios)</p>
    <div class="acoes"><button class="btn" data-a="aval" data-id="${r.id}">Avaliar acessibilidade</button>
    <button class="btn sec" data-a="fav" data-id="${r.id}" aria-pressed="${f}">${f ? "♥ Favoritado" : "♡ Favoritar"}</button></div>
    <h2>Acessibilidade</h2>
    <p>${res ? `Para o seu perfil: ${ind(res)}` : 'Escolha seu perfil em “Meu perfil” para ver a resposta personalizada.'}</p>
    <ul class="lista-crit">${CRIT.map(c => { const x = crit(r, c.k), imp = ks.includes(c.k);
      return `<li class="crit ${imp ? "destaque" : ""}"><span>${c.nome}${imp ? " <small>(importa para você)</small>" : ""}</span>${ind(status(x))}
      <small>${x.n ? `Verificado em ${x.d} · ${x.n} respostas` : "Sem respostas"}</small></li>` }).join("")}</ul>
    <h2>Quem já foi (${visitas(r)})</h2>
    <p class="meta">${visitas(r)} pessoas registraram visita ou avaliação neste local (dados fictícios).</p>
    <h2>Atendimento</h2>
    <p>${a.n ? `${estrelas(a.m)} ${a.m.toFixed(1)}` : "Ainda sem avaliações de atendimento."}</p>
    <p class="meta">As estrelas medem só o atendimento e não entram no resultado de acessibilidade.</p>
    <h2>Localização</h2><div id="mapa-mini" aria-label="Mapa com a localização de ${r.nome}"></div>`;
    mapaEm("mapa-mini", [r], [r.lat, r.lng]);
  },
  sobre() { }, faq() { }
};

/* ===== 5. Navegação por hash (#pagina ou #detalhes-id) ===== */
function rota(keep) {
  const [p, id] = (location.hash.slice(1) || "inicio").split("-"), pg = PAGES[p] ? p : "inicio";
  $$("[data-page]").forEach(s => s.hidden = s.dataset.page != pg);
  $$("#menu a").forEach(a => a.toggleAttribute("aria-current", a.dataset.nav == (pg == "detalhes" ? "restaurantes" : pg)));
  $("#voltar").hidden = pg == "inicio"; // botão "Voltar ao início" em todas as páginas internas
  PAGES[pg](id, keep);
  if (!keep) { fecharMenu(); scrollTo(0, 0); $("main").focus() }
}
window.addEventListener("hashchange", () => rota());
const fecharMenu = () => { $("#menu").classList.remove("aberto"); $("#burger").setAttribute("aria-expanded", false) };
$("#burger").onclick = () => $("#burger").setAttribute("aria-expanded", $("#menu").classList.toggle("aberto"));
document.addEventListener("keydown", e => e.key == "Escape" && fecharMenu());

/* ===== 6. Ações: favoritar, dislike (com desfazer), avaliar, excluir ===== */
function toast(msg, undoId) {
  const t = $("#toast"); t.innerHTML = msg + (undoId ? ` <button class="btn sec" data-a="dis" data-id="${undoId}">Desfazer</button>` : "");
  t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => t.hidden = true, 6000);
}
document.addEventListener("click", e => {
  const h = e.target.closest("[data-h]"); if (h) { H = h.dataset.h; return rota(true) }
  const b = e.target.closest("button[data-a]"); if (!b) return;
  const a = b.dataset.a, id = +b.dataset.id, av = +b.dataset.av;
  if (a == "ver") return location.hash = "detalhes-" + id;
  if (a == "aval" || a == "edit") return abrirAvaliacao(id, av);
  if (a == "fav") S.favs = toggle(S.favs, id);
  if (a == "dis") { S.ocultos = toggle(S.ocultos, id); toast(S.ocultos.includes(id) ? "Restaurante ocultado." : "Restaurante restaurado.", S.ocultos.includes(id) && id) }
  if (a == "del") S.avals = S.avals.filter(x => x.id != av);
  rota(true);
});

/* ===== 7. Filtros ===== */
$("#filtros").addEventListener("input", e => { const f = e.target.form;
  F = { q: f.q.value, nota: +f.nota.value, dist: +f.dist.value, cat: f.cat.value, acess: f.acess.value, fav: f.fav.checked }; rota(true) });
$("#filtros").addEventListener("reset", () => setTimeout(() => { F = { q: "", nota: 0, dist: 0, cat: "", acess: "", fav: false }; rota(true) }));

/* ===== 8. Início: CEP, busca e geolocalização ===== */
$("#form-cep").onsubmit = e => { e.preventDefault(); S.cep = $("#cep").value;
  toast("CEP salvo. Para calcular distâncias pelo CEP será necessária uma API (ex.: ViaCEP + geocodificação)."); location.hash = "restaurantes" };
$("#form-busca").onsubmit = e => { e.preventDefault(); F.q = $("#busca").value; location.hash = "restaurantes"; rota() };
function localizar() {
  if (!navigator.geolocation) return toast("Seu navegador não oferece geolocalização. Use o CEP.");
  navigator.geolocation.getCurrentPosition(p => { S.pos = { lat: p.coords.latitude, lng: p.coords.longitude }; toast("Localização obtida."); rota(true) },
    () => toast("Localização não autorizada. Informe seu CEP na página inicial."));
}
$$("#btn-loc, #btn-loc2").forEach(b => b.onclick = localizar);

/* ===== 9. Perfil (seleção múltipla de necessidades) ===== */
$("#form-perfil").onsubmit = e => { e.preventDefault(); const f = e.target;
  S.perfil = { nome: f.nome.value, idade: f.idade.value, outra: f.outra.value, needs: $$("[name=need]:checked", f).map(i => i.value) };
  toast("Perfil salvo! Os resultados agora seguem o seu perfil."); rota(true) };

/* ===== 10. Avaliação: checklist de acessibilidade (separado) + estrelas de atendimento (opcional) ===== */
function abrirAvaliacao(rid, avId) {
  const r = RESTAURANTES.find(x => x.id == rid), a = S.avals.find(x => x.id == avId) || { resp: {}, atend: 0 }, f = $("#form-av");
  f.innerHTML = `<h2>Avaliar acessibilidade</h2><p>${r.nome} <small>(protótipo: nada é enviado a um servidor)</small></p>` +
    CRIT.map(c => `<fieldset><legend>${c.q}</legend>${OPC.map(([v, t]) => `<label class="check"><input type="radio" name="${c.k}" value="${v}" ${(a.resp[c.k] || "nv") == v ? "checked" : ""}>${t}</label>`).join("")}</fieldset>`).join("") +
    `<fieldset><legend>Atendimento (opcional, separado da acessibilidade)</legend>${[0, 1, 2, 3, 4, 5].map(n => `<label class="check"><input type="radio" name="atend" value="${n}" ${a.atend == n ? "checked" : ""}>${n ? n + " ★" : "Não avaliar"}</label>`).join("")}</fieldset>
    <div class="acoes"><button class="btn">Enviar avaliação</button><button type="button" class="btn sec" onclick="$('#dlg').close()">Cancelar</button></div>`;
  f.dataset.rid = rid; f.dataset.av = avId || ""; $("#dlg").showModal();
}
$("#form-av").onsubmit = e => { e.preventDefault(); const f = e.target, fd = new FormData(f), resp = {}, id = +f.dataset.av || Date.now();
  CRIT.forEach(c => resp[c.k] = fd.get(c.k));
  S.avals = S.avals.filter(x => x.id != id).concat({ id, rid: +f.dataset.rid, data: new Date().toLocaleDateString("pt-BR"), resp, atend: +fd.get("atend") });
  $("#dlg").close(); toast("Obrigado pela contribuição! 💜 Sua avaliação ajuda toda a comunidade."); rota(true) };
