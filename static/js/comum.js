/* comum.js – usado em todas as páginas: utilitários, configurações, perfil e localização locais,
   avisos (toast), menu hambúrguer, favoritar/esconder e anúncios. Adaptado do app.js da Giovanna.

   PRIVACIDADE (RN01): o perfil de mobilidade fica no localStorage e a localização no sessionStorage.
   Nenhum dos dois é enviado ao servidor: não entram em formulário, URL nem fetch. */

/* ===== 1. Utilitários e dados da página ===== */
const $ = (s, e = document) => e.querySelector(s), $$ = (s, e = document) => [...e.querySelectorAll(s)];
const DADOS = JSON.parse($("#dados-mobite").textContent);   // perfis, pesos e itens (informação pública)
const PREFS = JSON.parse($("#prefs-mobite").textContent);   // favoritos e escondidos da conta (se logado)
const LOGADO = document.body.dataset.logado === "1";
const csrf = () => $("input[name=csrfmiddlewaretoken]")?.value || "";
const ROT = { ok: "Funciona", warn: "Funciona com ressalva", bar: "Tem barreira", nd: "Falta informação" };
const RANK = { ok: 3, warn: 2, nd: 1, bar: 0 };
const forma = s => `<svg class="forma" aria-hidden="true" focusable="false"><use href="#f-${s}"></use></svg>`;
const ind = s => `<span class="ind s-${s}">${forma(s)}${ROT[s]}</span>`; // forma + cor + texto
const icone = (n, c = "") => `<svg class="icone ${c}" aria-hidden="true" focusable="false"><use href="#i-${n}"></use></svg>`;
const esc = t => String(t).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

/* ===== 2. Configurações da interface (só no aparelho) ===== */
const S = { cfg: { tema: "claro", fonte: 100, contraste: false, anim: false, prio: true, datas: true } };
try { Object.assign(S.cfg, JSON.parse(localStorage.getItem("mobite_cfg"))) } catch { }
const persist = () => { try { localStorage.setItem("mobite_cfg", JSON.stringify(S.cfg)) } catch { } };

/* ===== 3. Perfil de mobilidade: SÓ neste aparelho ===== */
const Perfil = {
  get() { try { const c = localStorage.getItem("mobite_perfil") || ""; return DADOS.perfis.some(p => p.codigo == c) ? c : "" } catch { return "" } },
  set(c) {
    try { c ? localStorage.setItem("mobite_perfil", c) : localStorage.removeItem("mobite_perfil") } catch { }
    $$("[data-perfil-sel]").forEach(s => s.value = c);
    document.dispatchEvent(new CustomEvent("perfil-mudou")); // listas, mapa, detalhes e anúncio se redesenham
  },
  dados() { return DADOS.perfis.find(p => p.codigo == this.get()) || null }
};
/* Seletor "Do que você precisa?" (início, lista e restaurante). Não tem name: nunca vai em formulário. */
$$("[data-perfil-sel]").forEach(s => {
  s.value = Perfil.get();
  s.addEventListener("change", () => {
    Perfil.set(s.value);
    toast(s.value ? "Perfil salvo." : "Perfil removido.");
  });
});

/* ===== 4. Localização ou CEP: só nesta aba, para calcular a distância aqui ===== */
const Pos = {
  get() { try { return JSON.parse(sessionStorage.getItem("mobite_pos")) } catch { return null } },
  set(p) { try { sessionStorage.setItem("mobite_pos", JSON.stringify(p)) } catch { } }
};
function distKm(lat, lng) {
  const p = Pos.get(); if (!p || lat == null) return null;
  const r = Math.PI / 180, a = Math.sin((lat - p.lat) * r / 2) ** 2 + Math.cos(p.lat * r) * Math.cos(lat * r) * Math.sin((lng - p.lng) * r / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(a));
}
const fmtKm = d => d == null ? "distância indisponível" : d < 1 ? `${Math.round(d * 1000 / 10) * 10} m` : `${d.toFixed(1).replace(".", ",")} km`;

function localizar(depois) {
  if (!navigator.geolocation) return toast("Seu navegador não compartilha a localização. Use o CEP.");
  navigator.geolocation.getCurrentPosition(p => {
    Pos.set({ lat: p.coords.latitude, lng: p.coords.longitude, origem: "gps" });
    toast("Localização ativada.");
    document.dispatchEvent(new CustomEvent("posicao-mudou"));
    depois?.();
  }, () => toast("Sem acesso à localização. Use o CEP."), { enableHighAccuracy: false, timeout: 15000 });
}
document.addEventListener("click", e => { if (e.target.closest("[data-localizar]")) localizar() });

/* CEP → endereço (ViaCEP) → coordenadas (Nominatim/OpenStreetMap). Feito pelo navegador. */
async function buscarCep(cep) {
  const n = cep.replace(/\D/g, "");
  if (n.length != 8) throw new Error("CEP deve ter 8 números.");
  const end = await fetch(`https://viacep.com.br/ws/${n}/json/`).then(r => r.json());
  if (end.erro) throw new Error("Não encontramos esse CEP.");
  const tentativas = [
    { street: end.logradouro, city: end.localidade, state: end.uf, country: "Brasil" },
    { postalcode: `${n.slice(0, 5)}-${n.slice(5)}`, country: "Brasil" },
    { city: end.localidade, state: end.uf, country: "Brasil" }
  ];
  for (const t of tentativas) {
    const q = new URLSearchParams({ ...Object.fromEntries(Object.entries(t).filter(([, v]) => v)), format: "json", limit: 1 });
    const r = await fetch(`https://nominatim.openstreetmap.org/search?${q}`, { headers: { "Accept-Language": "pt-BR" } }).then(r => r.json());
    if (r.length) { Pos.set({ lat: +r[0].lat, lng: +r[0].lon, origem: "cep", rotulo: `${end.logradouro || end.bairro}, ${end.localidade}` }); return Pos.get() }
  }
  throw new Error("Achamos o CEP, mas não a posição no mapa.");
}

/* ===== 5. Avisos (toast) ===== */
function toast(msg, acao, tipo = "ok") {
  const t = $("#toast");
  t.className = "toast-" + tipo;
  t.innerHTML = `${icone(tipo == "erro" ? "triangle-alert" : "circle-check")}<span class="toast-msg">${esc(msg)}</span>`;
  if (acao) { const b = document.createElement("button"); b.className = "btn sec mini"; b.textContent = acao.rotulo; b.onclick = () => { acao.fazer(); t.hidden = true }; $(".toast-msg", t).append(" ", b) }
  const x = document.createElement("button"); x.className = "toast-fechar"; x.setAttribute("aria-label", "Fechar aviso"); x.innerHTML = icone("x");
  x.onclick = () => t.hidden = true; t.append(x);
  t.hidden = false;
  const agendar = () => { clearTimeout(toast.t); toast.t = setTimeout(() => t.hidden = true, 6000) };
  t.onmouseenter = () => clearTimeout(toast.t); t.onmouseleave = agendar; // não some enquanto o mouse estiver em cima
  agendar();
}

/* Avisos do servidor: sucesso e informação viram o aviso flutuante (some em 6 s);
   erros e alertas ficam na página até a pessoa sair dela. */
(() => {
  const leves = $$(".avisos .aviso-success, .avisos .aviso-info");
  if (!leves.length) return;
  toast(leves.map(a => a.textContent.trim()).join(" "));
  leves.forEach(a => a.remove());
  if (!$(".avisos .aviso")) $(".avisos")?.remove();
})();

/* Ao voltar com o botão "Voltar", o navegador mostra a página guardada (com favoritos antigos): recarrega. */
addEventListener("pageshow", e => { if (e.persisted) location.reload() });

/* ===== 6. Menu hambúrguer (da Giovanna) ===== */
const fecharMenu = () => { $("#menu").classList.remove("aberto"); $("#burger").setAttribute("aria-expanded", false) };
$("#burger").onclick = () => $("#burger").setAttribute("aria-expanded", $("#menu").classList.toggle("aberto"));
document.addEventListener("keydown", e => e.key == "Escape" && fecharMenu());
document.addEventListener("click", e => { if ($("#menu").classList.contains("aberto") && !e.target.closest("#menu, #burger")) fecharMenu() });

/* ===== 7. Favoritar e esconder (exige conta) ===== */
async function preferencia(id, tipo) {
  if (!LOGADO) {
    if (abrirEntrar("Para favoritar ou esconder um lugar, entre na sua conta.")) return undefined;
    window.Carregando?.mostrar();
    location.href = `${document.body.dataset.login}?next=${encodeURIComponent(location.pathname)}`;
    return undefined;
  }
  const corpo = new URLSearchParams({ tipo, csrfmiddlewaretoken: csrf() });
  const r = await fetch(`/restaurantes/${id}/preferencia/`, { method: "POST", body: corpo, headers: { Accept: "application/json" } });
  if (!r.ok) { toast("Não deu certo agora. Tente de novo."); return undefined }
  const { estado } = await r.json();
  PREFS.favoritos = PREFS.favoritos.filter(x => x != id); PREFS.escondidos = PREFS.escondidos.filter(x => x != id);
  if (estado == "FAVORITO") PREFS.favoritos.push(id);
  if (estado == "ESCONDIDO") PREFS.escondidos.push(id);
  return estado;
}

/* ===== 8. Anúncios: escolhidos AQUI pelo perfil local (RN01.3), sempre com "Publicidade" ===== */
function mostrarAnuncios() {
  const p = Perfil.get();
  $$(".faixa-anuncio, .bloco-anuncio").forEach(caixa => {
    const todos = $$(".anuncio", caixa);
    todos.forEach(a => a.hidden = true); caixa.hidden = true;
    const doPerfil = p ? todos.filter(a => a.dataset.perfis.split(",").includes(p)) : [];
    const gerais = todos.filter(a => !a.dataset.perfis);
    const opcoes = doPerfil.length ? doPerfil : gerais;
    if (!opcoes.length) return;
    opcoes[Math.floor(Math.random() * opcoes.length)].hidden = false;
    caixa.hidden = false;
  });
  if ($(".faixa-anuncio:not([hidden])")) document.body.classList.add("com-anuncio");
  else document.body.classList.remove("com-anuncio");
}
mostrarAnuncios();

document.addEventListener("perfil-mudou", mostrarAnuncios);

/* ===== 9. Olhinho para mostrar a senha digitada ===== */
$$('input[type="password"]').forEach(campo => {
  const caixa = document.createElement("span"); caixa.className = "campo-senha";
  campo.replaceWith(caixa); caixa.append(campo);
  const b = document.createElement("button");
  b.type = "button"; b.className = "olho"; b.setAttribute("aria-pressed", "false");
  b.setAttribute("aria-label", "Mostrar senha"); b.innerHTML = icone("eye");
  b.onclick = () => {
    const mostrar = campo.type == "password";
    campo.type = mostrar ? "text" : "password";
    b.setAttribute("aria-pressed", mostrar); b.setAttribute("aria-label", mostrar ? "Esconder senha" : "Mostrar senha");
    b.innerHTML = icone(mostrar ? "eye-off" : "eye"); campo.focus();
  };
  caixa.append(b);
});
// Antes de enviar, volta a ser campo de senha (o navegador não guarda o texto aberto no histórico).
document.addEventListener("submit", e => $$(".campo-senha input", e.target).forEach(c => c.type = "password"), true);

/* ===== 10. App instalável (PWA) ===== */
if ("serviceWorker" in navigator && location.protocol != "file:") {
  if (document.body.dataset.dev == "1") { // no PC de desenvolvimento, nada de cópia guardada: sempre a versão nova
    navigator.serviceWorker.getRegistrations().then(rs => rs.forEach(r => r.unregister())).catch(() => { });
    if (window.caches) caches.keys().then(ks => ks.forEach(k => caches.delete(k))).catch(() => { });
  } else navigator.serviceWorker.register("/sw.js").catch(() => { });
}

/* ===== 11. Entrar sem sair da página =====
   A janela (templates/_entrar.html) manda o login para o django-allauth por fetch e, se der certo,
   recarrega a mesma página já conectada. Criar conta e "Esqueci a senha" abrem as páginas completas. */
const dlgEntrar = $("#dlg-entrar");
function abrirEntrar(motivo = "") {
  if (!dlgEntrar || LOGADO) return false;
  const aqui = location.pathname + location.search;
  $$("a[data-com-next]", dlgEntrar).forEach(a => a.search = "?next=" + encodeURIComponent(aqui));
  const m = $("#entrar-motivo"); m.textContent = motivo; m.hidden = !motivo;
  $("#entrar-erro").textContent = "";
  fecharMenu();
  dlgEntrar.showModal();
  $("#entrar-email").focus();
  return true;
}
// Links para a página de login (topo, menu, perfil) abrem a janela, menos nas próprias páginas de conta
document.addEventListener("click", e => {
  const a = e.target.closest(`a[href^="${document.body.dataset.login}"]`);
  if (!a || a.closest("#dlg-entrar") || location.pathname.startsWith("/contas/")) return;
  if (e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
  if (abrirEntrar(a.dataset.motivo)) e.preventDefault();
});
document.addEventListener("click", e => { if (e.target.closest("[data-fechar-entrar]")) dlgEntrar?.close() });
$("#form-entrar")?.addEventListener("submit", async e => {
  e.preventDefault();
  const f = e.target, erro = $("#entrar-erro"), botao = $("button[type=submit]", f), dados = new FormData(f);
  dados.set("next", f.dataset.depois);   // resposta leve; quem mostra a página conectada é o recarregar abaixo
  botao.disabled = true; erro.textContent = "";
  try {
    const r = await fetch(f.action, { method: "POST", body: dados, credentials: "same-origin" });
    const destino = new URL(r.url).pathname;
    if (r.ok && destino == f.dataset.depois) { window.Carregando?.mostrar(0); location.reload(); return }
    if (destino.includes("confirm-email")) {
      erro.textContent = "Falta confirmar o seu e-mail. Mandamos o link de novo para a sua caixa de entrada.";
      return;
    }
    if (r.status == 429) { erro.textContent = "Muitas tentativas. Espere alguns minutos e tente de novo."; return }
    const pagina = new DOMParser().parseFromString(await r.text(), "text/html");
    const aviso = ($(".errorlist", pagina) || $("form .aviso", pagina))?.textContent.trim();
    erro.textContent = aviso || "E-mail ou senha incorretos.";
  } catch {
    erro.textContent = "Não deu para entrar agora. Confira a conexão e tente de novo.";
  } finally { botao.disabled = false }
});
