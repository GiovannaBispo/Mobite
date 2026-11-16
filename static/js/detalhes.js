/* detalhes.js – página do restaurante e formulário de avaliação.
   - mostra o resultado do perfil local e marca os itens que importam para ele;
   - escolhe até 5 perguntas começando pelo que falta saber para o perfil (o perfil não é enviado);
   - pede a localização só quando há foto, para o servidor conferir os 150 m e descartar. */

const det = $("#det");

/* ===== 1. Resultado para o perfil ===== */
function pintarDetalhes() {
  const box = $("#res-det"); if (!box) return;
  const perfil = Perfil.dados(), todos = JSON.parse($("#resultados-det").textContent);
  $$(".crit").forEach(li => { li.classList.remove("destaque"); const t = $(".tag-perfil", li); t.hidden = true });
  if (!perfil) {
    box.innerHTML = 'Escolha seu perfil em <a href="/perfil/">Meu perfil</a> para ver a resposta personalizada.';
    $("#motivo-det").hidden = true;
  } else {
    const r = todos[perfil.codigo] || { css: "nd", motivo: "" };
    box.innerHTML = `Para o seu perfil (${esc(perfil.nome.toLowerCase())}): ${ind(r.css)}`;
    const pre = { bar: "Barreira em: ", warn: "Ressalva em: ", nd: "Ainda falta saber: " }[r.css];
    $("#motivo-det").textContent = pre && r.motivo ? pre + r.motivo + "." : "";
    $("#motivo-det").hidden = !(pre && r.motivo);
    $$(".crit").forEach(li => {
      const peso = perfil.pesos[li.dataset.codigo]; if (!peso) return;
      li.classList.add("destaque");
      const t = $(".tag-perfil", li); t.hidden = false;
      t.textContent = peso == "BLOQUEIA" ? "(essencial para você)" : "(importa para você)";
    });
  }
  if (det?.dataset.lat) $$(".dist", det).forEach(x => x.textContent = fmtKm(distKm(+det.dataset.lat, +det.dataset.lng)));
}

/* ===== 2. Fila de até 5 perguntas ===== */
function montarFila() {
  const form = $("#form-av"); if (!form) return;
  const max = 5, perfil = Perfil.dados(), pesos = perfil?.pesos || {};
  const perguntas = $$(".pergunta", form);
  const respondidas = perguntas.filter(f => $("input:checked", f)?.value);
  const peso = f => ({ BLOQUEIA: 0, IMPORTA: 1 }[pesos[f.dataset.codigo]] ?? 2);
  const falta = f => ({ sem: 0, antigo: 1 }[f.dataset.estado] ?? 2);
  // Primeiro o que ainda falta saber (sem resposta, em dúvida ou desatualizado), começando pelo que importa
  // para o perfil e, nele, pelo que bloqueia. O que já tem resposta só entra se sobrar lugar.
  const chave = f => [falta(f) == 2, peso(f) == 2, falta(f), peso(f)].map(Number);
  const comparar = (a, b) => { const x = chave(a), y = chave(b); return x.reduce((d, v, i) => d || v - y[i], 0) };
  const fila = respondidas.length ? respondidas : [...perguntas].sort(comparar).slice(0, max);
  perguntas.forEach(f => { const v = fila.includes(f); f.hidden = !v; f.disabled = !v });
  fila.forEach(f => form.insertBefore(f, $(".foto-campo", form))); // na ordem da fila: as que bloqueiam primeiro
}

/* ===== 3. Janela de avaliação (dialog da Giovanna) ===== */
const dlg = $("#dlg");
$("#abrir-aval")?.addEventListener("click", e => {
  if (!dlg) { if (abrirEntrar("Para avaliar, entre na sua conta.")) e.preventDefault(); return } // sem conta
  e.preventDefault(); montarFila(); dlg.showModal();
});
document.addEventListener("click", e => { if (e.target.closest("[data-fechar]")) dlg?.close() });

/* ===== 4. Envio: com foto, confere a localização antes ===== */
$("#form-av")?.addEventListener("submit", e => {
  const form = e.target, foto = form.foto?.files?.[0], erro = $("#erro-foto"), botao = $("#enviar-av");
  if (!foto || form.dataset.conferido) return;
  e.preventDefault();
  if (!navigator.geolocation) { erro.textContent = "Este navegador não compartilha a localização. Envie a avaliação sem a foto."; return }
  botao.disabled = true; botao.textContent = "Enviando…"; erro.textContent = "";
  navigator.geolocation.getCurrentPosition(p => {
    form.lat.value = p.coords.latitude; form.lon.value = p.coords.longitude; // vão só neste envio e são descartadas
    form.dataset.conferido = "1"; window.Carregando?.mostrar(); form.submit();
  }, () => {
    botao.disabled = false; botao.textContent = "Enviar avaliação";
    erro.textContent = "Permita a localização para mandar a foto, ou envie a avaliação sem ela.";
  }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 });
});

/* ===== 5. "Continua igual" sem recarregar a página (a tela não pula) ===== */
document.addEventListener("submit", async e => {
  const f = e.target.closest("form.form-confirmar"); if (!f) return;
  if (!LOGADO) { if (abrirEntrar("Para confirmar um item, entre na sua conta.")) e.preventDefault(); return } // sem conta
  e.preventDefault();
  const b = $("button", f), li = f.closest("li"); b.disabled = true;
  try {
    const r = await fetch(f.action, { method: "POST", body: new FormData(f), headers: { Accept: "application/json" } });
    const d = await r.json();
    toast(d.mensagem);
    if (d.recarregar) { setTimeout(() => { window.Carregando?.mostrar(); location.reload() }, 900); return }
    $(".verificacao", li).textContent = d.verificacao;
    b.innerHTML = `${icone("check")} Você confirmou<span class="sr"> – ${esc($("span", li).firstChild.textContent.trim())}</span>`;
  } catch { window.Carregando?.mostrar(); f.submit() } // e-mail não confirmado ou sem conexão: faz do jeito normal
});

/* ===== 6. Equipe: trazer restaurante de demonstração para cá ===== */
$("#form-mover")?.addEventListener("submit", e => {
  const f = e.target; if (f.lat.value) return;
  e.preventDefault();
  if (!navigator.geolocation) return toast("Este navegador não informa a localização.");
  navigator.geolocation.getCurrentPosition(p => { f.lat.value = p.coords.latitude; f.lon.value = p.coords.longitude; window.Carregando?.mostrar(); f.submit() },
    () => toast("Permita a localização para trazer o restaurante para cá."), { enableHighAccuracy: true, timeout: 20000 });
});

/* ===== 7. Fotos da entrada: toque abre a foto grande ===== */
document.addEventListener("click", e => {
  const a = e.target.closest(".abre-foto"), d = $("#dlg-foto"); if (!a || !d) return;
  e.preventDefault();
  const img = $("img", a);
  $("img", d).src = a.href; $("img", d).alt = img.alt; $("p", d).textContent = `${a.dataset.legenda}. ${img.alt}`;
  d.showModal();
});
document.addEventListener("click", e => { if (e.target.closest("[data-fechar-foto]")) $("#dlg-foto")?.close() });

function miniMapa() {
  if (det?.dataset.lat && window.mapaEm && $("#mapa-mini")) mapaEm("mapa-mini", [{ id: +det.dataset.id, nome: det.dataset.nome, lat: +det.dataset.lat, lng: +det.dataset.lng, res: JSON.parse($("#resultados-det").textContent), semPopup: true }], [+det.dataset.lat, +det.dataset.lng]);
}
document.addEventListener("perfil-mudou", () => { pintarDetalhes(); montarFila(); miniMapa() });
pintarDetalhes(); montarFila(); miniMapa();
