/* carregando.js – mostra a animação da logo quando a troca de página demora (link, formulário ou recarregar).
   - Só aparece se a página não trocar em 250 ms, para não piscar nas trocas rápidas.
   - A página seguinte continua a animação de onde parou (o trecho no <head>, em _carregando_head.html)
     e some assim que ela fica pronta.
   - Na primeira página da visita, aparece como abertura por pelo menos 0,8 s.
   Outros scripts podem chamar Carregando.mostrar() antes de form.submit() ou location.reload(). */
(() => {
  const h = document.documentElement, CHAVE = "mobite_carregando", ATRASO = 250, LIMITE = 30000;
  let espera = 0, seguranca = 0;

  const guardar = v => { try { v ? sessionStorage.setItem(CHAVE, v) : sessionStorage.removeItem(CHAVE) } catch (e) { } };
  const texto = t => { const el = document.querySelector("#carregando .cg-texto"); if (el) el.textContent = t };

  function ativar() {
    // Janela aberta (<dialog>) fica numa camada acima de tudo e esconderia a animação. Como a página vai
    // trocar, ela fecha (o que já foi enviado não se perde).
    document.querySelectorAll("dialog[open]").forEach(d => d.close());
    h.style.setProperty("--cg-atraso", "0ms");        // começa do início do ciclo
    h.classList.remove("carregando-splash");
    h.classList.add("carregando-ativo");
    texto("Carregando…");
    guardar(String(Date.now()));                     // a próxima página continua daqui
    clearTimeout(seguranca);
    seguranca = setTimeout(esconder, LIMITE);        // se a troca não acontecer (ex.: download), some sozinha
  }

  function mostrar(atraso = ATRASO, ainda = () => true) {
    clearTimeout(espera);
    espera = setTimeout(() => { if (ainda()) ativar() }, atraso);
  }

  function esconder() {
    clearTimeout(espera); clearTimeout(seguranca);
    guardar(null);
    h.classList.remove("carregando-ativo");
    texto("");
    setTimeout(() => h.classList.remove("carregando-splash"), 300);
  }

  // Links para outra página do próprio site, abertos na mesma aba
  document.addEventListener("click", e => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    if ((a.target && a.target !== "_self") || a.hasAttribute("download")) return;
    const u = new URL(a.href, location.href);
    if (u.origin !== location.origin) return;                                   // outro site, e-mail, telefone
    if (u.pathname === location.pathname && u.search === location.search && u.hash) return;  // só muda a âncora
    mostrar(ATRASO, () => !e.defaultPrevented);                                 // o JS da página não tratou o clique
  });

  // Formulários enviados de verdade (não os tratados por JS nem os de fechar diálogo)
  document.addEventListener("submit", e => {
    const f = e.target, quem = e.submitter;
    const metodo = ((quem && quem.getAttribute("formmethod")) || f.getAttribute("method") || "get").toLowerCase();
    const alvo = (quem && quem.getAttribute("formtarget")) || f.getAttribute("target");
    if (metodo === "dialog" || (alvo && alvo !== "_self")) return;
    mostrar(ATRASO, () => !e.defaultPrevented);
  });

  // Voltar para uma página guardada pelo navegador: tira a animação que ficou congelada nela
  addEventListener("pageshow", e => { if (e.persisted) esconder() });

  // Esta página ficou pronta: some (na abertura, depois de pelo menos 0,8 s)
  function pronta() {
    if (!h.classList.contains("carregando-ativo")) return;
    const reduzido = matchMedia("(prefers-reduced-motion: reduce)").matches || h.dataset.anim === "true";
    const minimo = h.classList.contains("carregando-splash") ? (reduzido ? 300 : 800) : 0;
    setTimeout(esconder, Math.max(0, minimo - (performance.now() - (window.cgDesde || 0))));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", pronta); else pronta();

  window.Carregando = { mostrar, esconder };
})();
