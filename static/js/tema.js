/* tema.js – aparência e preferências: tema claro/escuro, tamanho da fonte, alto contraste, animações e
   preferências da lista. Tudo é salvo no localStorage (chave mobite_cfg) e aplicado em <html>. (Giovanna) */
function aplicarCfg() {
  const c = S.cfg, h = document.documentElement;
  h.dataset.tema = c.tema; h.dataset.contraste = c.contraste; h.dataset.anim = c.anim;
  h.style.fontSize = c.fonte + "%"; // todo o CSS usa rem, então a fonte muda em toda a interface
}
function syncCfg() { // atualiza os controles da página Configurações (o ícone do tema troca pelo CSS)
  $$("[data-pref]").forEach(i => i.checked = S.cfg[i.dataset.pref]);
  if ($("#fonte-val")) $("#fonte-val").textContent = S.cfg.fonte + "%";
  if ($("#tema-val")) $("#tema-val").textContent = S.cfg.tema == "escuro" ? "Modo escuro" : "Modo claro";
  $("#btn-tema").setAttribute("aria-pressed", S.cfg.tema == "escuro");
}
function salvarCfg() { persist(); aplicarCfg(); syncCfg(); window.atualizarListas?.(); window.atualizarMapas?.() }
document.addEventListener("click", e => {
  const b = e.target.closest("[data-cfg]"); if (!b) return; const c = S.cfg, v = b.dataset.cfg;
  if (v == "tema") c.tema = c.tema == "claro" ? "escuro" : "claro";
  if (v == "mais") c.fonte = Math.min(140, c.fonte + 10);   // limites de legibilidade: 80% a 140%
  if (v == "menos") c.fonte = Math.max(80, c.fonte - 10);
  if (v == "padrao") c.fonte = 100;
  salvarCfg();
});
document.addEventListener("change", e => { const i = e.target.closest("[data-pref]"); if (i) { S.cfg[i.dataset.pref] = i.checked; salvarCfg() } });
aplicarCfg(); syncCfg();
