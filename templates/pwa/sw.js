{% load static %}/* Service worker do MoBite (RNF01: instalar no celular como web app).
   Arquivos do app: guardados no aparelho. Páginas: busca na internet e, sem conexão,
   mostra a última versão vista ou a página "sem conexão". Nada de perfil ou localização passa por aqui. */
{% if MODO_DEV %}// Modo de desenvolvimento: apaga as cópias guardadas e se desinstala.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.map(k => caches.delete(k))))
  .then(() => self.registration.unregister())));
{% else %}const VERSAO = "mobite-{{ CFG.VERSAO }}";
const ARQUIVOS = [
  "{% url 'offline' %}",
  "{% static 'css/style.css' %}?v={{ CFG.VERSAO }}", "{% static 'css/paginas.css' %}?v={{ CFG.VERSAO }}", "{% static 'css/temas.css' %}?v={{ CFG.VERSAO }}",
  "{% static 'css/funcional.css' %}?v={{ CFG.VERSAO }}", "{% static 'js/comum.js' %}?v={{ CFG.VERSAO }}", "{% static 'js/tema.js' %}?v={{ CFG.VERSAO }}",
  "{% static 'js/lista.js' %}?v={{ CFG.VERSAO }}", "{% static 'js/detalhes.js' %}?v={{ CFG.VERSAO }}", "{% static 'js/mapa.js' %}?v={{ CFG.VERSAO }}", "{% static 'js/perfil.js' %}?v={{ CFG.VERSAO }}",
  "{% static 'vendor/leaflet/leaflet.js' %}", "{% static 'vendor/leaflet/leaflet.css' %}",
  "{% static 'img/logo-mobite.png' %}", "{% static 'img/logo-mobite-escuro.png' %}", "{% static 'img/icone-192.png' %}",
  "{% static 'css/carregando.css' %}?v={{ CFG.VERSAO }}", "{% static 'js/carregando.js' %}?v={{ CFG.VERSAO }}"
];

// cache "reload": busca no servidor, não numa cópia antiga guardada pelo navegador
self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSAO).then(c => c.addAll(ARQUIVOS.map(u => new Request(u, {cache: "reload"})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSAO).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/equipe/") || url.pathname.startsWith("/contas/")) return;
  if (url.pathname.startsWith("{% get_static_prefix %}")) {
    e.respondWith(caches.match(req).then(r => r || fetch(req)));
    return;
  }
  if (req.mode === "navigate") {
    // Só guarda páginas públicas de consulta; nada de conta, avaliações ou favoritos.
    const publica = /^\/($|restaurantes\/(\d+\/)?$|sobre\/$|perguntas-frequentes\/$|configuracoes\/$)/.test(url.pathname);
    e.respondWith(fetch(req).then(resp => {
      const copia = resp.clone();
      if (resp.ok && publica) caches.open(VERSAO).then(c => c.put(req, copia));
      return resp;
    }).catch(() => caches.match(req).then(r => r || caches.match("{% url 'offline' %}"))));
  }
});
{% endif %}
