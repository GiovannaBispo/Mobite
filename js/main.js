/* main.js – inicialização: preenche listas dinâmicas, aplica as configurações salvas e abre a página da URL. */
const HOME = [["todos", "Todos"], ...CATS.map(c => [c, c]), ["top", "Mais bem avaliados"], ["perto", "Mais próximos"]];
$("#chips-h").innerHTML = HOME.map(([v, t]) => `<button class="chip" data-h="${v}" aria-pressed="false">${t}</button>`).join("");
$("#filtros").cat.innerHTML = '<option value="">Todas</option>' + CATS.map(c => `<option>${c}</option>`).join("");
$("#filtros").acess.innerHTML = '<option value="">Qualquer</option>' + CRIT.map(c => `<option value="${c.k}">${c.nome}</option>`).join("");
$("#needs").innerHTML = Object.entries(NEC).map(([k, n]) => `<label class="check"><input type="checkbox" name="need" value="${k}">${n.nome}</label>`).join("");
$("#lista-faq").innerHTML = FAQ.map(([q, a]) => `<details><summary>${q}</summary><p>${a}</p></details>`).join("");
if (innerWidth < 800) $("#caixa-filtros").open = false;
aplicarCfg(); syncCfg(); rota();
