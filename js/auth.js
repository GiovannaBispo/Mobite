/* auth.js – login (Supabase Auth) e gravação de favoritos, lugares ocultados e avaliações na conta do usuário.
   Depende de supabase-config.js (supabaseClient) e de app.js ($, S, toast, rota).
   O perfil de mobilidade NÃO vai para o banco: fica só no aparelho (localStorage). */

let modoCadastro = false;

const viraAval = x => ({ id: x.id, rid: x.restaurante_id, data: new Date(x.criado_em).toLocaleDateString("pt-BR"), resp: x.resp, atend: x.atend });

function traduzirErro(err) {
  const m = (err.message || "").toLowerCase();
  if (m.includes("not confirmed")) return "Confirme o seu e-mail antes de entrar.";
  if (m.includes("invalid login")) return "E-mail ou senha incorretos.";
  if (m.includes("already registered")) return 'Esse e-mail já tem conta. Use "Já tenho conta".';
  if (m.includes("password")) return "A senha precisa ter pelo menos 6 caracteres.";
  if (m.includes("rate limit")) return "Muitas tentativas. Espere um pouco e tente de novo.";
  if (m.includes("email")) return "Confira o e-mail digitado.";
  return "Não foi possível entrar agora. Tente de novo.";
}

function atualizarBotaoConta() {
  const b = $("#btn-conta");
  b.textContent = S.user ? "Sair" : "Entrar";
  b.setAttribute("aria-label", S.user ? `Sair da conta ${S.user.email}` : "Entrar ou criar conta");
}

function ajustarModo() {
  $("#auth-titulo").textContent = modoCadastro ? "Criar conta" : "Entrar";
  $("#auth-ok").textContent = modoCadastro ? "Criar conta" : "Entrar";
  $("#auth-troca").textContent = modoCadastro ? "Já tenho conta" : "Criar conta";
  $("#form-auth").senha.autocomplete = modoCadastro ? "new-password" : "current-password";
  $("#auth-erro").hidden = true;
}

function abrirLogin(msg = "") {
  modoCadastro = false; ajustarModo();
  $("#auth-msg").textContent = msg;
  if (!$("#dlg-auth").open) $("#dlg-auth").showModal();
}

// Barra ações que exigem conta: abre a janela de login e devolve false
function exigirLogin(acao) {
  if (S.user) return true;
  abrirLogin(`Para ${acao}, entre na sua conta ou crie uma.`);
  return false;
}

async function carregarDadosUsuario() {
  const [f, o, a] = await Promise.all([
    supabaseClient.from("favoritos").select("restaurante_id"),
    supabaseClient.from("ocultos").select("restaurante_id"),
    supabaseClient.from("avaliacoes").select("*").order("criado_em")
  ]);
  if (f.error || o.error || a.error) { console.warn("Erro ao carregar dados da conta.", f.error, o.error, a.error); toast("Não foi possível carregar os dados da sua conta.") }
  S.favs = (f.data || []).map(x => x.restaurante_id);
  S.ocultos = (o.data || []).map(x => x.restaurante_id);
  S.avals = (a.data || []).map(viraAval);
}

// Chamada uma vez na abertura do site: se já havia sessão salva, restaura a conta
async function iniciarAuth() {
  try {
    const { data } = await supabaseClient.auth.getSession();
    if (data.session) { S.user = data.session.user; await carregarDadosUsuario() }
  } catch (e) { console.warn("Login indisponível.", e) }
  atualizarBotaoConta();
}

async function sair() {
  try { await supabaseClient.auth.signOut() } catch (e) { console.warn(e) }
  S.user = null; S.favs = []; S.ocultos = []; S.avals = [];
  atualizarBotaoConta(); toast("Você saiu da conta."); rota(true);
}

// Favoritar / ocultar: adiciona (on = true) ou remove (on = false) a linha do usuário
async function dbMarcar(tabela, rid, on) {
  const { error } = on
    ? await supabaseClient.from(tabela).insert({ restaurante_id: rid })
    : await supabaseClient.from(tabela).delete().eq("restaurante_id", rid);
  if (error && error.code != "23505") { console.warn(error); toast("Não foi possível salvar. Tente de novo."); return false }
  return true;
}

// Cria (id = null) ou atualiza uma avaliação. Devolve a avaliação no formato do site, ou null se falhar
async function dbSalvarAval(id, rid, resp, atend) {
  const q = id
    ? supabaseClient.from("avaliacoes").update({ resp, atend, criado_em: new Date().toISOString() }).eq("id", id)
    : supabaseClient.from("avaliacoes").insert({ restaurante_id: rid, resp, atend });
  const { data, error } = await q.select().single();
  if (error) { console.warn(error); toast("Não foi possível salvar a avaliação. Tente de novo."); return null }
  return viraAval(data);
}

/* ===== Eventos da janela de login ===== */
$("#btn-conta").onclick = () => S.user ? sair() : abrirLogin();
$("#auth-troca").onclick = () => { modoCadastro = !modoCadastro; ajustarModo() };
$("#auth-fechar").onclick = () => $("#dlg-auth").close();

$("#form-auth").onsubmit = async e => {
  e.preventDefault();
  const f = e.target, email = f.email.value.trim(), password = f.senha.value, erro = $("#auth-erro"), ok = $("#auth-ok");
  ok.disabled = true; erro.hidden = true;
  try {
    const { data, error } = modoCadastro
      ? await supabaseClient.auth.signUp({ email, password })
      : await supabaseClient.auth.signInWithPassword({ email, password });
    if (error) throw error;
    if (!data.session) { erro.textContent = "Conta criada. Confirme o e-mail para entrar."; erro.hidden = false; return }
    S.user = data.user;
    await carregarDadosUsuario();
    atualizarBotaoConta(); f.reset(); $("#dlg-auth").close();
    toast("Você entrou na conta."); rota(true);
  } catch (err) {
    erro.textContent = traduzirErro(err); erro.hidden = false;
  } finally { ok.disabled = false }
};