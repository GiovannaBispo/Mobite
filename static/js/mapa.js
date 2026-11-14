/* mapa.js – Leaflet + OpenStreetMap. Zoom por botões + / − (sem depender de gesto de pinça) e marcador
   com a forma do resultado além da cor. (Giovanna)
   - mapaEm(): mini mapa da página do restaurante;
   - aba "Mapa" ao lado da lista: mostra os mesmos cards que a lista está mostrando (mesmos filtros). */
const mapas = {};
function quitarMapa(id) { mapas[id]?.remove(); delete mapas[id] }
const cssDo = r => { const p = Perfil.get(), v = r.res?.[p]; return p ? (typeof v == "object" ? v?.css : v) || "nd" : "sem" };
function iconeDe(css) {
  return L.divIcon({ className: `pin pin-${css}`, html: `<span>${css == "sem" ? "" : forma(css)}</span>`,
    iconSize: [28, 28], iconAnchor: [14, 28], popupAnchor: [0, -26] });
}
function novoMapa(id) {
  const m = L.map(id, { zoomControl: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, referrerPolicy: "strict-origin-when-cross-origin", // exigido pela política de uso do OSM
    attribution: '© <a href="https://www.openstreetmap.org/copyright">colaboradores do OpenStreetMap</a>'
  }).addTo(m);
  m.marcadores = L.layerGroup().addTo(m);
  return mapas[id] = m;
}
function marcar(m, rs) {
  m.marcadores.clearLayers();
  rs.forEach(r => {
    const css = cssDo(r), mk = L.marker([r.lat, r.lng], { icon: iconeDe(css), title: r.nome, alt: r.nome });
    if (!r.semPopup) mk.bindPopup(`<b>${esc(r.nome)}</b>${r.end ? "<br>" + esc(r.end) : ""}<br>${css != "sem" ? ind(css) + "<br>" : ""}<a class="btn" href="${r.url}">Ver detalhes</a>`);
    m.marcadores.addLayer(mk);
  });
  const pos = Pos.get();
  if (pos) m.marcadores.addLayer(L.circleMarker([pos.lat, pos.lng], { radius: 8 }).bindPopup("Você está aqui"));
}
function mapaEm(id, rs, foco) {
  quitarMapa(id);
  const el = document.getElementById(id); if (!el) return;
  if (!window.L) return el.textContent = "Mapa indisponível: verifique a conexão com a internet.";
  const m = novoMapa(id); marcar(m, rs); m.setView(foco, 16);
  return m;
}

/* ===== Aba "Mapa" da lista ===== */
const cardParaPonto = c => ({ id: +c.dataset.id, nome: c.dataset.nome, end: c.dataset.end, url: c.dataset.url,
  lat: +c.dataset.lat, lng: +c.dataset.lng, res: JSON.parse(c.dataset.res || "{}") });
function mapaVisivel() { const p = $("#painel-mapa"); return p && p.offsetParent !== null }
function desenharMapaLista(reenquadrar = true) {
  const el = $("#mapa-lista"); if (!el || !mapaVisivel()) return;
  if (!window.L) { el.textContent = "Mapa indisponível: verifique a conexão com a internet."; return }
  const m = mapas["mapa-lista"] || novoMapa("mapa-lista");
  m.invalidateSize();
  const pontos = $$('.card[data-combina="1"]').map(cardParaPonto);
  marcar(m, pontos);
  if (!reenquadrar && m.jaEnquadrado) return;
  const pos = Pos.get();
  if (pos) m.setView([pos.lat, pos.lng], 15);
  else if (pontos.length) m.fitBounds(pontos.map(p => [p.lat, p.lng]), { padding: [30, 30], maxZoom: 16 });
  else m.setView([-23.5614, -46.6559], 13); // referência: centro de São Paulo
  m.jaEnquadrado = true;
}
window.atualizarMapas = () => desenharMapaLista(false);
document.addEventListener("click", e => {
  const z = e.target.closest("[data-zoom]"); if (!z) return;
  const id = $(".leaflet-container", z.closest(".mapa-caixa"))?.id;
  mapas[id]?.[z.dataset.zoom == "in" ? "zoomIn" : "zoomOut"]();
});
document.addEventListener("posicao-mudou", () => desenharMapaLista(true));
window.desenharMapaLista = desenharMapaLista;
