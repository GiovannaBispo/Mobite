/* perfil.js – escolha do perfil de mobilidade. Salva só no localStorage deste aparelho (RN01.1):
   o formulário não tem action e nunca é enviado ao servidor. */
const formPerfil = $("#form-perfil");
const atual = Perfil.get();
$$("[name=perfil]", formPerfil).forEach(i => i.checked = i.value == atual);
formPerfil.addEventListener("submit", e => {
  e.preventDefault();
  const escolhido = $("[name=perfil]:checked", formPerfil)?.value || "";
  Perfil.set(escolhido);
  mostrarAnuncios();
  toast(escolhido ? "Perfil salvo! Os resultados agora seguem o seu perfil." : "Perfil removido.");
});
