/* dados.js – dados FICTÍCIOS e constantes. Em produção, viriam de uma API/banco de dados.
   Para adicionar um restaurante, inclua um objeto em RESTAURANTES (e uma imagem em assets/images/restaurantes). */

// Checklist: 10 itens da ABNT NBR 9050 conferíveis a olho (q = pergunta do formulário de avaliação)
const CRIT = [
  { k: "vaga", nome: "Vaga reservada", q: "Existe vaga reservada?" },
  { k: "degrau", nome: "Entrada sem degrau", q: "A entrada é sem degrau?" },
  { k: "porta", nome: "Porta larga", q: "A porta de entrada é larga?" },
  { k: "corrimao", nome: "Corrimão", q: "A entrada possui corrimão?" },
  { k: "circulacao", nome: "Circulação entre mesas", q: "Há espaço para circular entre as mesas?" },
  { k: "mesa", nome: "Mesa que encaixa", q: "Há mesa em que a cadeira de rodas encaixa?" },
  { k: "terreo", nome: "Tudo no térreo", q: "Tudo fica no térreo, sem escada?" },
  { k: "cadeira", nome: "Cadeira sem braço", q: "Existe cadeira sem braço ou de assento largo?" },
  { k: "banheiro", nome: "Banheiro acessível", q: "O banheiro é acessível?" },
  { k: "banheiroesc", nome: "Banheiro sem escada", q: "O banheiro é sem escada?" }
];
const NOME = Object.fromEntries(CRIT.map(c => [c.k, c.nome]));
const OPC = [["sim", "Sim"], ["parcial", "Parcialmente"], ["nao", "Não"], ["na", "Não se aplica"], ["nv", "Não consegui verificar"]];

// Cada perfil de mobilidade → itens do checklist que importam para ele (o resultado muda conforme o perfil)
const NEC = {
  idoso: { nome: "Idosos", crit: ["degrau", "corrimao", "terreo", "banheiroesc", "cadeira"] },
  muleta: { nome: "Pessoas que utilizam muletas", crit: ["degrau", "corrimao", "terreo", "circulacao"] },
  bengala: { nome: "Pessoas que utilizam bengalas", crit: ["corrimao", "circulacao", "terreo"] },
  andador: { nome: "Pessoas que utilizam andadores", crit: ["degrau", "porta", "circulacao", "banheiro", "terreo"] },
  cadeirante: { nome: "Cadeirantes", crit: ["vaga", "degrau", "porta", "circulacao", "mesa", "terreo", "banheiro"] },
  mae: { nome: "Mães com bebês de colo", crit: ["degrau", "porta", "circulacao", "terreo", "banheiro"] },
  obesidade: { nome: "Obesidade / espaços ampliados", crit: ["porta", "circulacao", "mesa", "cadeira"] },
  outra: { nome: "Outras necessidades de mobilidade", crit: ["degrau", "circulacao", "terreo"] }
};
const CATS = ["Restaurantes", "Cafeterias", "Lanchonetes", "Padarias"];

/* s = resposta de cada item na ordem de CRIT (0 = sem informação; 1–2 barreira; 3 ressalva; 4–5 funciona)
   v = visitas registradas · d = data da última verificação · nota = estrelas de ATENDIMENTO (não entra na acessibilidade)
   Esta lista é a RESERVA: se o Supabase falhar, o site usa estes dados. Normalmente ela é substituída
   pelos dados do banco, por carregarRestaurantes() (no final deste arquivo). */
let RESTAURANTES = [
  { id: 1, nome: "Sabor & Cia", tipo: "Restaurantes", s: "5555545555", v: 48, d: "21/10/2026", nota: 4.8, lat: -23.5614, lng: -46.6559, end: "Rua Exemplo, 100", hor: "11h–23h" },
  { id: 2, nome: "Sabores do Mundo", tipo: "Restaurantes", s: "4435432335", v: 31, d: "12/10/2026", nota: 4.6, lat: -23.5575, lng: -46.6620, end: "Av. Modelo, 250", hor: "12h–22h" },
  { id: 3, nome: "Bistrô da Praça", tipo: "Restaurantes", s: "0415320254", v: 22, d: "03/09/2026", nota: 4.5, lat: -23.5650, lng: -46.6500, end: "Praça Fictícia, 12", hor: "10h–21h" },
  { id: 4, nome: "Café Brisa", tipo: "Cafeterias", s: "0551500500", v: 14, d: "28/09/2026", nota: 4.3, lat: -23.5590, lng: -46.6700, end: "Rua das Ideias, 45", hor: "8h–19h" },
  { id: 5, nome: "Grão & Prosa", tipo: "Cafeterias", s: "4544455450", v: 17, d: "30/10/2026", nota: 4.7, lat: -23.5530, lng: -46.6490, end: "Rua do Teste, 77", hor: "7h–20h" },
  { id: 6, nome: "Lanche Express", tipo: "Lanchonetes", s: "1215120100", v: 9, d: "15/08/2026", nota: 4.0, lat: -23.5700, lng: -46.6450, end: "Rua Protótipo, 78", hor: "9h–22h" },
  { id: 7, nome: "Burger Largo", tipo: "Lanchonetes", s: "5435335455", v: 19, d: "05/10/2026", nota: 4.4, lat: -23.5480, lng: -46.6600, end: "Av. Demonstração, 300", hor: "11h–23h" },
  { id: 8, nome: "Padaria Pão Nosso", tipo: "Padarias", s: "3255453554", v: 26, d: "18/10/2026", nota: 4.4, lat: -23.5540, lng: -46.6580, end: "Rua Teste, 9", hor: "6h–20h" },
  { id: 9, nome: "Forno da Vila", tipo: "Padarias", s: "0000000000", v: 0, d: "", nota: 0, lat: -23.5660, lng: -46.6650, end: "Rua da Vila, 21", hor: "6h–19h" },
  { id: 10, nome: "Cantina Nonna Rosa", tipo: "Restaurantes", s: "5525555255", v: 35, d: "25/10/2026", nota: 4.9, lat: -23.5600, lng: -46.6420, end: "Rua Imaginária, 5", hor: "12h–23h" }
].map(r => ({ ...r, img: `assets/images/restaurantes/r${r.id}.svg` }));

// Busca os restaurantes no Supabase e substitui a lista de reserva. Se der erro, mantém os dados locais.
async function carregarRestaurantes() {
  try {
    const { data, error } = await supabaseClient.from("restaurantes").select("*").order("id");
    if (error || !data?.length) {
      console.warn("Supabase indisponível, usando dados locais.", error);
      return;
    }
    RESTAURANTES = data.map(r => ({
      id: r.id, nome: r.nome, tipo: r.tipo, s: r.s,
      v: r.visitas, nota: Number(r.nota),
      d: r.verificado_em ? new Date(r.verificado_em + "T00:00:00").toLocaleDateString("pt-BR") : "",
      lat: r.lat, lng: r.lng, end: r.endereco, hor: r.horario,
      img: `assets/images/restaurantes/r${r.id}.svg`
    }));
  } catch (e) {
    console.warn("Falha ao carregar do Supabase, usando dados locais.", e);
  }
}

const FAQ = [
  ["Preciso criar conta?", "Não para consultar: a lista, o mapa e o checklist ficam abertos. Conta só para avaliar, favoritar e esconder lugares."],
  ["É pago?", "Não. Para quem usa é grátis e vai continuar. A ideia de receita é um plano para o restaurante, e só depois de o app estar de pé."],
  ["Quem pode avaliar?", "Qualquer pessoa com conta, respondendo o que viu no lugar. Não existe nota geral chutada: são itens de sim ou não, com data."],
  ["As estrelas contam na acessibilidade?", "Não. Estrela é só atendimento. Acessibilidade é item conferido, e a resposta ainda muda conforme o perfil."],
  ["E se o restaurante discordar?", "Ele tem direito de resposta, que aparece junto do item (funcionalidade planejada: exige backend). Se o lugar corrigiu a barreira, uma nova visita atualiza o item."],
  ["Vocês avaliam a calçada?", "Não nesta etapa. A calçada não é do restaurante e muda de quadra em quadra. A gente começa na vaga e na porta, e vai até a mesa e o banheiro."],
  ["Este protótipo guarda o que eu marco?", "Sim, se você estiver com a conta: favoritos, lugares ocultados e avaliações ficam salvos nela. O perfil de mobilidade fica só no seu aparelho."],
  ["De onde vem o checklist?", "Da ABNT NBR 9050, a norma de acessibilidade em edificações. A gente usou os pontos que uma pessoa comum consegue verificar sem equipamento."]
];
