/* lista.js – cards de restaurante (Início, Encontrar restaurantes, Favoritos e o botão de favoritar dos detalhes)
   e as abas Lista | Mapa. O servidor manda o resultado dos 5 perfis em data-res; aqui se mostra só o do
   perfil guardado no aparelho. */

const dadosCard = c => ({
  id: +c.dataset.id, nome: c.dataset.nome, busca: c.dataset.busca.toLowerCase(),
  lat: +c.dataset.lat, lng: +c.dataset.lng, nota: +c.dataset.nota, itensOk: c.dataset.itensOk.split(","),
  res: JSON.parse(c.dataset.res || "{}"), motivos: JSON.parse(c.dataset.motivos || "{}")
});
const resDo = (d, p) => p ? (d.res[p] || "nd") : null;

/* ===== 1. Pinta o resultado do perfil e a distância em cada card ===== */
function pintarCards() {
  const p = Perfil.get();
  $$(".card[data-res]").forEach(c => {
    const d = dadosCard(c), res = resDo(d, p), motivo = p && d.motivos[p];
    const pre = { bar: "Barreira: ", warn: "Ressalva: ", nd: "Falta saber: " }[res] || "";
    const caixa = $(".res-perfil", c);
    caixa.innerHTML = res
      ? `<span class="meta">Para o seu perfil:</span><br>${ind(res)}${motivo ? `<br><small>${esc(pre + motivo)}</small>` : ""}`
      : "";
    caixa.hidden = !res; // sem perfil, um aviso só acima da lista (#aviso-sem-perfil)
    const km = distKm(d.lat, d.lng), dist = $(".dist", c); if (dist) dist.textContent = km == null ? "" : fmtKm(km);
    $$(".data-verif", c).forEach(x => x.hidden = !S.cfg.datas);
  });
  const aviso = $("#aviso-sem-perfil"); if (aviso) aviso.hidden = !!p;
}

/* Ordem: resultado para o perfil (se a preferência estiver ligada), depois distância, depois nome.
   Assinatura e anúncio não entram na ordem (RI04). */
function ordenar(cards, modo) {
  const p = Perfil.get();
  const chave = c => { const d = dadosCard(c); return { d, r: RANK[resDo(d, p)] ?? 0, km: distKm(d.lat, d.lng) } };
  return cards.map(c => [c, chave(c)]).sort(([, a], [, b]) => {
    if (modo == "top") return b.d.nota - a.d.nota || a.d.nome.localeCompare(b.d.nome);
    if (modo != "perto" && S.cfg.prio && p && b.r != a.r) return b.r - a.r;
    if (a.km != null && b.km != null && a.km != b.km) return a.km - b.km;
    return a.d.nome.localeCompare(b.d.nome);
  }).map(([c]) => c);
}

/* ===== 2. Ordem: Todos, Mais bem avaliados, Mais próximos (opções da Giovanna) ===== */
let H = "todos";
document.addEventListener("click", e => { const h = e.target.closest("[data-h]"); if (h) { H = h.dataset.h; atualizarListas() } });

/* CEP: vira posição no navegador e a lista se reordena aqui mesmo */
$("#form-cep")?.addEventListener("submit", async e => {
  e.preventDefault();
  const b = $("button", e.target); b.disabled = true;
  try {
    const pos = await buscarCep($("#cep").value);
    toast(`Mostrando os restaurantes perto de ${pos.rotulo || "o CEP informado"}.`);
    H = "perto"; document.dispatchEvent(new CustomEvent("posicao-mudou"));
    $("#titulo-lista")?.scrollIntoView({ behavior: S.cfg.anim ? "auto" : "smooth" });
  }
  catch (err) { toast(err.message || "Não conseguimos usar esse CEP agora.") }
  finally { b.disabled = false }
});
/* A busca do topo é o campo "Buscar" dos filtros: Enter não recarrega, só leva até a lista */
$("#filtros")?.addEventListener("submit", e => e.preventDefault());
document.addEventListener("click", e => { if (e.target.closest("[data-ir-lista]")) $("#titulo-lista")?.scrollIntoView({ behavior: S.cfg.anim ? "auto" : "smooth" }) });

/* ===== 3. Filtros da lista ===== */
function lerFiltros() {
  const f = $("#filtros"); if (!f) return null;
  return {
    q: f.q.value.trim().toLowerCase(), nota: +f.nota.value, dist: +f.dist.value, acess: f.acess.value,
    fav: f.fav?.checked, res: $$("[name=res]:checked", f).map(i => i.value)
  };
}
function desenharRestaurantes() {
  const grade = $("#lista-rest"), F = lerFiltros(); if (!grade || !F) return;
  const p = Perfil.get();
  $$("[name=res]").forEach(i => i.disabled = !p);
  $("#sem-perfil-filtro").hidden = !!p;
  const cards = $$(".card", grade);
  $$("[data-h]").forEach(b => b.setAttribute("aria-pressed", b.dataset.h == H));
  if ($("#aviso-loc")) $("#aviso-loc").hidden = H != "perto" || !!Pos.get();
  let n = 0;
  ordenar(cards, H).forEach(c => {
    const d = dadosCard(c), km = distKm(d.lat, d.lng);
    const ok = (!F.q || d.busca.includes(F.q)) && d.nota >= F.nota
      && (!F.dist || km == null || km <= F.dist) && (!F.acess || d.itensOk.includes(F.acess))
      && (!F.fav || PREFS.favoritos.includes(d.id)) && (!p || F.res.includes(resDo(d, p)));
    c.hidden = !ok; c.dataset.combina = ok ? "1" : "0"; grade.append(c); if (ok) n++;
  });
  $$("#lista-ocultos .card").forEach(c => c.dataset.combina = "0");
  $("#contador").textContent = `Mostrando ${n} de ${cards.length}`;
  $("#vazio-lista").hidden = n > 0;
  const ocultos = $$("#lista-ocultos .card");
  $("#ocultos").hidden = !ocultos.length; $("#n-ocultos").textContent = ocultos.length;
}
$("#filtros")?.addEventListener("input", atualizarListas);
$("#busca")?.addEventListener("input", atualizarListas); // fica fora do <form>, ligado a ele por form="filtros"
$("#filtros")?.addEventListener("reset", () => setTimeout(atualizarListas));
if ($("#caixa-filtros") && innerWidth < 800) $("#caixa-filtros").open = false;

function atualizarListas() { pintarCards(); desenharRestaurantes(); window.atualizarMapas?.() }
window.atualizarListas = atualizarListas;
document.addEventListener("perfil-mudou", atualizarListas);
document.addEventListener("posicao-mudou", () => { if (H == "todos") H = "perto"; atualizarListas() });

/* ===== 4. Abas Lista | Mapa (no celular e no computador) ===== */
function abrirAba(qual, foco) {
  const vistas = $("[data-vistas]"); if (!vistas) return;
  $$('[role="tab"]', vistas).forEach(t => {
    const ativa = t.id == "aba-" + qual;
    t.setAttribute("aria-selected", ativa); t.tabIndex = ativa ? 0 : -1;
    $("#" + t.getAttribute("aria-controls")).hidden = !ativa;
    if (ativa && foco) t.focus();
  });
  window.desenharMapaLista?.(true);
}
$$('[data-vistas] [role="tab"]').forEach(t => {
  t.addEventListener("click", () => abrirAba(t.id.replace("aba-", "")));
  t.addEventListener("keydown", e => { // setas trocam de aba, como pede o padrão de abas acessíveis
    if (e.key == "ArrowRight" || e.key == "ArrowLeft") abrirAba(t.id == "aba-lista" ? "mapa" : "lista", true);
  });
});
addEventListener("resize", () => window.desenharMapaLista?.(false));

/* ===== 5. Favoritar e esconder (com desfazer) ===== */
function marcarFav(id, ligado) {
  $$(`[data-a=fav][data-id="${id}"]`).forEach(b => {
    b.classList.toggle("on", ligado); b.setAttribute("aria-pressed", ligado);
    if (b.classList.contains("ic")) b.setAttribute("aria-label", `${ligado ? "Remover dos favoritos" : "Favoritar"}: ${b.closest(".card")?.dataset.nome || ""}`);
    const t = $(".txt-fav", b); if (t) t.textContent = ligado ? "Favoritado" : "Favoritar";
  });
  $$(`.card[data-id="${id}"]`).forEach(c => c.dataset.fav = ligado ? "1" : "0");
}
function moverEscondido(id, escondido) {
  $$(`.card[data-id="${id}"]`).forEach(c => {
    const b = $("[data-a=esc]", c);
    b.innerHTML = icone(escondido ? "undo-2" : "eye-off");
    b.setAttribute("aria-label", `${escondido ? "Mostrar de novo na minha lista" : "Esconder da minha lista"}: ${c.dataset.nome}`);
    b.title = escondido ? "Mostrar de novo" : "Esconder da minha lista";
    const destino = escondido ? $("#lista-ocultos") : $("#lista-rest");
    if (destino) destino.append(c); else c.hidden = escondido; // em Favoritos, só some
  });
  atualizarListas();
}
document.addEventListener("click", async e => {
  const b = e.target.closest("button[data-a]"); if (!b) return;
  const id = +b.dataset.id, a = b.dataset.a;
  if (a != "fav" && a != "esc") return;
  e.preventDefault();
  const estado = await preferencia(id, a == "fav" ? "FAVORITO" : "ESCONDIDO");
  if (estado === undefined) return;
  marcarFav(id, estado == "FAVORITO");
  if (a == "fav") {
    toast(estado == "FAVORITO" ? "Adicionado aos favoritos." : "Removido dos favoritos.");
    if (!estado && $("#lista-favs")) $(`#lista-favs .card[data-id="${id}"]`)?.remove();
  } else {
    const escondido = estado == "ESCONDIDO";
    moverEscondido(id, escondido);
    const onde = $("#lista-ocultos") ? " Ele fica em “Escondidos por você”, no fim da lista." : "";
    toast(escondido ? "Restaurante escondido da sua lista." + onde : "Restaurante de volta na sua lista.",
      escondido && { rotulo: "Desfazer", fazer: async () => { if (await preferencia(id, "ESCONDIDO") !== undefined) moverEscondido(id, false) } });
  }
});

atualizarListas();
if (new URLSearchParams(location.search).get("vista") == "mapa") abrirAba("mapa");

/* Quem tocou em favoritar ou esconder antes de entrar na conta: depois do login, a ação é feita aqui
   (o pedido fica guardado por 5 minutos pela função preferencia, em comum.js). */
(() => {
  let p = null;
  try { p = JSON.parse(sessionStorage.getItem("mobite_pendente")); sessionStorage.removeItem("mobite_pendente") } catch { }
  if (!LOGADO || !p || Date.now() - p.t > 5 * 60000) return;
  const fav = p.tipo == "FAVORITO";
  if ((fav ? PREFS.favoritos : PREFS.escondidos).includes(p.id)) return; // já estava feito
  $(`button[data-a="${fav ? "fav" : "esc"}"][data-id="${p.id}"]`)?.click();
})();
