/* mapa.js – Leaflet + OpenStreetMap: mini mapa dos detalhes e página "Mapa" com todos os restaurantes.
   Zoom por botões + / − (sem depender de gesto de pinça). Depende de app.js. */
const mapas = {};
const CENTRO = [-23.5614, -46.6559]; // centro de São Paulo: apenas referência, NÃO é a localização do usuário
function quitarMapa(id) { mapas[id]?.remove(); delete mapas[id] }
function mapaEm(id, rs, foco) {
  quitarMapa(id);
  if (!window.L) return $("#" + id).textContent = "Mapa indisponível: o Leaflet precisa de conexão com a internet.";
  const m = L.map(id, { zoomControl: false }).setView(foco || CENTRO, foco ? 16 : 13);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(m);
  const icone = L.divIcon({ className: "pin", html: "<span></span>", iconSize: [28, 28], iconAnchor: [14, 28], popupAnchor: [0, -26] });
  rs.forEach(r => { const res = resultado(r);
    L.marker([r.lat, r.lng], { icon: icone, title: r.nome }).addTo(m).bindPopup(`<b>${r.nome}</b><br>${r.tipo} · ${r.end}<br>${res ? ind(res) : ""}<br>
      <button class="btn" data-a="ver" data-id="${r.id}">Ver detalhes</button>`) });
  if (S.pos) L.circleMarker([S.pos.lat, S.pos.lng], { radius: 8 }).addTo(m).bindPopup("Você está aqui");
  return mapas[id] = m;
}
PAGES.mapa = () => {
  const visiveis = RESTAURANTES.filter(r => !S.ocultos.includes(r.id));
  mapaEm("mapa-grande", visiveis, S.pos && [S.pos.lat, S.pos.lng]);
  $("#aviso-mapa").hidden = !!S.pos;
};
document.addEventListener("click", e => { const z = e.target.closest("[data-zoom]"); if (z) mapas["mapa-grande"]?.[z.dataset.zoom == "in" ? "zoomIn" : "zoomOut"]() });
