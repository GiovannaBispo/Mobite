"""Testes das regras de negócio do MoBite. Rodar com: python manage.py test"""
import io
import shutil
import tempfile
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from . import regras
from .forms import cnpj_valido
from .models import (LINK_EXEMPLO, Anuncio, Assinatura, AvaliacaoAcessibilidade, Classificacao, ConfiguracaoSite,
                     Conta, FotoEntrada, ItemChecklist, Papel, Peso, PerfilMobilidade, Reivindicacao, Resposta, RespostaEstabelecimento,
                     RespostaItem, Restaurante, ResultadoPerfil, SituacaoItem, StatusAnalise)

MIDIA = tempfile.mkdtemp()
B, I, S, N = Peso.BLOQUEIA, Peso.IMPORTA, Resposta.SIM, Resposta.NAO


def conta(email="pessoa@teste.com", **extra):
    c = Conta.objects.create_user(email=email, password="senha-forte-123", **extra)
    EmailAddress.objects.create(user=c, email=email, verified=True, primary=True)
    return c


def foto_com_exif(tamanho=(3000, 2000)):
    img = Image.new("RGB", tamanho, (200, 100, 50))
    exif = Image.Exif()
    exif[0x010F] = "Fabricante do celular"   # Make
    exif[0x0110] = "Modelo secreto"          # Model
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    buf.seek(0)
    buf.name = "entrada.jpg"
    return buf


class ClassificarTest(TestCase):
    """RN02: barreira > falta informação > ressalva > funciona."""
    pesos = {"E1": B, "E2": B, "I3": B, "I1": I, "I2": I}

    def test_barreira_quando_item_que_bloqueia_esta_nao(self):
        c, itens = regras.classificar(self.pesos, {"E1": N, "E2": S, "I3": S, "I1": S, "I2": S})
        self.assertEqual((c, itens), (Classificacao.TEM_BARREIRA, ["E1"]))

    def test_falta_informacao_quando_item_que_bloqueia_sem_resposta(self):
        c, _ = regras.classificar(self.pesos, {"E1": S, "I3": S, "I1": S, "I2": S})
        self.assertEqual(c, Classificacao.FALTA_INFORMACAO)

    def test_falta_informacao_com_tres_relevantes_sem_resposta(self):
        pesos = {"E1": B, "I1": I, "I2": I, "B1": I}
        c, itens = regras.classificar(pesos, {"E1": S})
        self.assertEqual(c, Classificacao.FALTA_INFORMACAO)
        self.assertEqual(len(itens), 3)

    def test_nao_sei_conta_como_sem_resposta(self):
        c, _ = regras.classificar(self.pesos, {"E1": Resposta.NAO_SEI, "E2": S, "I3": S, "I1": S, "I2": S})
        self.assertEqual(c, Classificacao.FALTA_INFORMACAO)

    def test_ressalva_quando_so_item_que_importa_esta_nao(self):
        c, itens = regras.classificar(self.pesos, {"E1": S, "E2": S, "I3": S, "I1": N, "I2": S})
        self.assertEqual((c, itens), (Classificacao.FUNCIONA_COM_RESSALVA, ["I1"]))

    def test_funciona(self):
        c, _ = regras.classificar(self.pesos, {k: S for k in self.pesos})
        self.assertEqual(c, Classificacao.FUNCIONA)


class DadosFixosTest(TestCase):
    def test_migracao_cria_checklist_perfis_e_matriz(self):
        self.assertEqual(ItemChecklist.objects.count(), 10)
        self.assertEqual(PerfilMobilidade.objects.count(), 5)
        e1 = ItemChecklist.objects.get(codigo="E1")
        self.assertFalse(e1.invertida)  # "Dá para entrar sem subir degrau?": Sim é o que atende
        self.assertEqual(e1.pergunta, "Dá para entrar sem subir degrau ou escada?")
        cadeira = PerfilMobilidade.objects.get(codigo="cadeira")
        self.assertEqual(cadeira.pesos.get(item__codigo="E1").peso, B)

    def test_vaga_conta_so_para_quem_tem_direito(self):
        # LBI, art. 47: a vaga com espaço ao lado é de pessoa com deficiência com comprometimento de mobilidade
        com_vaga = set(PerfilMobilidade.objects.filter(pesos__item__codigo="C3").values_list("codigo", flat=True))
        self.assertEqual(com_vaga, {"cadeira", "muleta"})

    def test_textos_cobrem_os_casos_da_rua(self):
        itens = {i.codigo: i for i in ItemChecklist.objects.all()}
        self.assertIn("não tem degrau nem rampa, responda Sim", itens["E3"].ajuda)    # entrada plana
        for codigo in ("B1", "B2"):                                                     # sem banheiro
            self.assertIn("Se não tem banheiro para clientes, responda Não", itens[codigo].ajuda)
        self.assertIn("só uma abre", itens["E2"].ajuda)                                # porta de duas folhas
        for i in itens.values():                                                        # cabe no campo
            self.assertLessEqual(len(i.ajuda), 160, i.codigo)
            self.assertLessEqual(len(i.pergunta), 160, i.codigo)

    def test_restaurante_nasce_com_10_situacoes_e_5_resultados(self):
        r = Restaurante.objects.create(nome="Teste", latitude=-23.56, longitude=-46.65)
        self.assertEqual(r.situacoes.count(), 10)
        self.assertEqual(r.resultados.filter(classificacao=Classificacao.FALTA_INFORMACAO).count(), 5)


class SituacaoEPendenciaTest(TestCase):
    def setUp(self):
        self.r = Restaurante.objects.create(nome="Cantina", latitude=-23.56, longitude=-46.65)
        self.itens = {i.codigo: i for i in ItemChecklist.objects.all()}
        self.ana = conta("ana@teste.com")

    def avaliar(self, respostas, dias_atras=0, autor=None):
        av = AvaliacaoAcessibilidade.objects.create(autor=autor or self.ana, restaurante=self.r,
                                                    data=timezone.now() - timedelta(days=dias_atras))
        for cod, resp in respostas.items():
            RespostaItem.objects.create(avaliacao=av, item=self.itens[cod], resposta=resp)
        regras.recalcular(self.r)
        return av

    def situacao(self, cod):
        return SituacaoItem.objects.get(restaurante=self.r, item=self.itens[cod])

    def test_pergunta_invertida(self):
        # Nenhum item é invertido hoje, mas a regra continua: com "invertida", Sim quer dizer que não atende
        ItemChecklist.objects.filter(codigo="E3").update(invertida=True)
        self.avaliar({"E3": S})
        self.assertEqual(self.situacao("E3").resposta, N)

    def test_entrada_sem_degrau_sim_atende(self):
        self.avaliar({"E1": S})  # "Dá para entrar sem subir degrau ou escada?" Sim (pode ser pela rampa)
        self.assertEqual(self.situacao("E1").resposta, S)

    def test_vale_a_resposta_mais_recente_e_vira_pendencia_resolvida(self):
        self.avaliar({"B1": N}, dias_atras=30)
        self.avaliar({"B1": S}, dias_atras=2)
        self.assertEqual(self.situacao("B1").resposta, S)
        abertas, resolvidas = regras.pendencias(self.r)
        self.assertEqual(abertas, [])
        self.assertEqual(resolvidas[0]["item"].codigo, "B1")

    def test_confirmacao_conta_e_atualiza_data(self):
        self.avaliar({"B2": S}, dias_atras=10)
        regras.registrar_confirmacao(self.situacao("B2"), conta("bia@teste.com"))
        s = self.situacao("B2")
        self.assertEqual(s.confirmacoes, 1)
        self.assertEqual(s.dias_desde_verificacao(), 0)

    def test_ocultar_avaliacao_recalcula(self):
        av = self.avaliar({"E2": N})
        cadeira = PerfilMobilidade.objects.get(codigo="cadeira")
        self.assertEqual(ResultadoPerfil.objects.get(restaurante=self.r, perfil=cadeira).classificacao,
                         Classificacao.TEM_BARREIRA)
        av.ocultar("teste")
        self.assertEqual(self.situacao("E2").resposta, Resposta.NAO_SEI)
        self.assertNotEqual(ResultadoPerfil.objects.get(restaurante=self.r, perfil=cadeira).classificacao,
                            Classificacao.TEM_BARREIRA)

    def test_excluir_conta_deixa_avaliacao_anonima(self):
        av = self.avaliar({"C3": S})
        self.ana.excluir_conta()
        av.refresh_from_db()
        self.assertIsNone(av.autor)
        self.assertEqual(self.situacao("C3").resposta, S)


@override_settings(MEDIA_ROOT=MIDIA)
class AvaliarViewTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MIDIA, ignore_errors=True)

    def setUp(self):
        self.r = Restaurante.objects.create(nome="Bistrô", latitude=-23.5600, longitude=-46.6500)
        self.url = reverse("avaliar", args=[self.r.pk])
        self.ana = conta("ana@teste.com")

    def test_consultar_nao_exige_conta(self):
        for nome, args in [("inicio", []), ("detalhes", [self.r.pk])]:
            self.assertEqual(self.client.get(reverse(nome, args=args)).status_code, 200)

    def test_avaliar_exige_conta(self):
        resp = self.client.post(self.url, {"r_E2": "SIM"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("account_login"), resp["Location"])
        self.assertFalse(AvaliacaoAcessibilidade.objects.exists())

    def test_no_maximo_5_perguntas(self):
        self.client.force_login(self.ana)
        dados = {f"r_{c}": "SIM" for c in ["C3", "E1", "E2", "E3", "I1", "I2"]}
        resp = self.client.post(self.url, dados)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AvaliacaoAcessibilidade.objects.exists())

    def test_avaliacao_e_estrelas_ficam_separadas(self):
        self.client.force_login(self.ana)
        resp = self.client.post(self.url, {"r_E2": "SIM", "r_I1": "NAO", "estrelas": "4"})
        self.assertRedirects(resp, reverse("obrigado", args=[self.r.pk]))
        self.assertEqual(RespostaItem.objects.count(), 2)
        self.assertEqual(self.r.atendimentos.get().estrelas, 4)

    def test_foto_perto_e_aceita_sem_exif_e_reduzida(self):
        self.client.force_login(self.ana)
        resp = self.client.post(self.url, {"r_E2": "SIM", "foto": foto_com_exif(), "lat": "-23.5601", "lon": "-46.6501"})
        self.assertEqual(resp.status_code, 302)
        foto = FotoEntrada.objects.get()
        self.assertTrue(foto.proximidade_confirmada)
        with Image.open(foto.arquivo.path) as img:
            self.assertLessEqual(max(img.size), 1280)
            self.assertEqual(len(img.getexif()), 0)

    def test_duas_fotos_ficam_na_galeria_e_nenhuma_vira_capa(self):
        for email in ("ana@teste.com", "bia@teste.com"):
            self.client.force_login(conta(email) if email != "ana@teste.com" else self.ana)
            self.client.post(self.url, {"r_E2": "SIM", "foto": foto_com_exif((800, 600)), "lat": "-23.5601",
                                        "lon": "-46.6501"})
        pagina = self.client.get(reverse("detalhes", args=[self.r.pk])).content.decode()
        self.assertEqual(FotoEntrada.objects.count(), 2)
        self.assertIn("Fotos da entrada (2)", pagina)
        self.assertIn(f'src="{reverse("fachada", args=[self.r.pk])}"', pagina)  # capa continua a ilustração

    def test_foto_longe_e_recusada(self):
        self.client.force_login(self.ana)
        resp = self.client.post(self.url, {"r_E2": "SIM", "foto": foto_com_exif((800, 600)),
                                           "lat": "-23.5700", "lon": "-46.6500"})  # ~1,1 km
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "150 m")
        self.assertFalse(FotoEntrada.objects.exists())
        self.assertFalse(AvaliacaoAcessibilidade.objects.exists())

    def test_coordenadas_nao_sao_guardadas(self):
        self.client.force_login(self.ana)
        self.client.post(self.url, {"r_E2": "SIM", "foto": foto_com_exif((800, 600)), "lat": "-23.5601",
                                    "lon": "-46.6501"})
        campos = [f.name for m in (AvaliacaoAcessibilidade, FotoEntrada, RespostaItem) for f in m._meta.fields]
        self.assertFalse(any(n in campos for n in ("lat", "lon", "latitude", "longitude")))


class RestauranteClienteTest(TestCase):
    def setUp(self):
        self.r = Restaurante.objects.create(nome="Sabores", latitude=-23.56, longitude=-46.65)
        self.dono = conta("dono@teste.com")
        Reivindicacao.objects.create(conta=self.dono, restaurante=self.r, cnpj="11.222.333/0001-81",
                                     status=StatusAnalise.APROVADA)
        self.url = reverse("responder", args=[self.r.pk, "I3"])

    def test_sem_assinatura_nao_responde(self):
        self.client.force_login(self.dono)
        self.client.post(self.url, {"texto": "Estamos fazendo a rampa."})
        self.assertFalse(RespostaEstabelecimento.objects.exists())

    def test_com_assinatura_responde_e_resultado_nao_muda(self):
        antes = list(self.r.resultados.values_list("classificacao", flat=True))
        Assinatura.objects.create(restaurante=self.r, data_fim=timezone.localdate() + timedelta(days=30))
        self.client.force_login(self.dono)
        self.client.post(self.url, {"texto": "Estamos fazendo a rampa."})
        self.assertEqual(RespostaEstabelecimento.objects.count(), 1)
        self.assertEqual(antes, list(self.r.resultados.values_list("classificacao", flat=True)))

    def test_quem_nao_e_responsavel_nao_responde(self):
        Assinatura.objects.create(restaurante=self.r)
        self.client.force_login(conta("outra@teste.com"))
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_cnpj(self):
        self.assertTrue(cnpj_valido("11.222.333/0001-81"))
        self.assertFalse(cnpj_valido("11.222.333/0001-82"))


class AnuncioTest(TestCase):
    def setUp(self):
        Anuncio.objects.create(titulo="Anúncio de teste", link="https://example.com/")

    def test_faixa_so_para_quem_nao_esta_logado(self):
        self.assertContains(self.client.get(reverse("inicio")), "Anúncio de teste")
        self.client.force_login(conta())
        self.assertNotContains(self.client.get(reverse("inicio")), "Anúncio de teste")

    def test_rotulo_publicidade(self):
        self.assertContains(self.client.get(reverse("inicio")), "Publicidade")

    def test_clique_conta_sem_ligar_a_conta(self):
        a = Anuncio.objects.get()
        self.client.get(reverse("anuncio", args=[a.pk]))
        a.refresh_from_db()
        self.assertEqual(a.cliques, 1)


class PessoasAjudadasTest(TestCase):
    """RF19: consultas ao lugar depois da avaliação, sem saber quem consultou."""

    def setUp(self):
        self.r = Restaurante.objects.create(nome="Bistrô", latitude=-23.56, longitude=-46.65)
        self.autor = conta("autor@teste.com")
        av = AvaliacaoAcessibilidade.objects.create(autor=self.autor, restaurante=self.r,
                                                    data=timezone.now() - timedelta(days=1))
        RespostaItem.objects.create(avaliacao=av, item=ItemChecklist.objects.get(codigo="E2"), resposta=Resposta.SIM)

    def test_consulta_de_outra_pessoa_conta_e_a_do_autor_nao(self):
        url = reverse("detalhes", args=[self.r.pk])
        self.client.get(url)                      # visitante sem conta: conta
        self.client.force_login(self.autor)
        self.client.get(url)                      # o próprio autor: não conta
        self.assertEqual(self.autor.contar_pessoas_ajudadas(), 1)
        self.assertContains(self.client.get(reverse("avaliacoes")), "ajudaram 1 pessoa")

    def test_consulta_do_mesmo_dia_da_avaliacao_nao_conta(self):
        outra = conta("outra@teste.com")
        self.client.force_login(outra)
        self.client.get(reverse("detalhes", args=[self.r.pk]))      # abriu antes de avaliar, no mesmo dia
        self.client.post(reverse("avaliar", args=[self.r.pk]), {"r_E2": "SIM"})
        self.assertEqual(outra.contar_pessoas_ajudadas(), 0)          # não ajudou a si mesma
        self.assertEqual(self.autor.contar_pessoas_ajudadas(), 1)     # quem avaliou ontem foi útil para ela

    def test_consulta_do_mesmo_dia_depois_da_avaliacao_conta(self):
        avaliou = conta("avaliou@teste.com")
        self.client.force_login(avaliou)
        self.client.get(reverse("detalhes", args=[self.r.pk]))      # abriu e avaliou hoje
        self.client.post(reverse("avaliar", args=[self.r.pk]), {"r_E2": "SIM"})
        self.client.get(reverse("detalhes", args=[self.r.pk]))      # voltar à página não conta
        self.assertEqual(avaliou.contar_pessoas_ajudadas(), 0)
        self.client.force_login(conta("viu-depois@teste.com"))
        self.client.get(reverse("detalhes", args=[self.r.pk]))      # outra pessoa, no mesmo dia, depois
        self.assertEqual(avaliou.contar_pessoas_ajudadas(), 1)
        self.client.force_login(avaliou)
        self.assertContains(self.client.get(reverse("avaliacoes")), "1 pessoa viu este lugar depois da sua avaliação")


class MoverDemoTest(TestCase):
    """Ferramenta da equipe: só restaurante de demonstração, só equipe."""

    def setUp(self):
        self.demo = Restaurante.objects.create(nome="Demo", latitude=-23.5, longitude=-46.6, demonstracao=True)
        self.real = Restaurante.objects.create(nome="Real", latitude=-23.5, longitude=-46.6)
        self.dados = {"lat": "-23.55", "lon": "-46.38"}

    def test_equipe_move_demonstracao(self):
        self.client.force_login(conta("equipe@teste.com", papel="EQUIPE_MOBITE"))
        self.client.post(reverse("mover_demo", args=[self.demo.pk]), self.dados)
        self.demo.refresh_from_db()
        self.assertAlmostEqual(self.demo.longitude, -46.38)
        self.assertLess(self.demo.distancia_metros(-23.55, -46.38), 150)

    def test_restaurante_real_e_membro_nao_movem(self):
        self.client.force_login(conta("equipe@teste.com", papel="EQUIPE_MOBITE"))
        self.assertEqual(self.client.post(reverse("mover_demo", args=[self.real.pk]), self.dados).status_code, 404)
        self.client.force_login(conta("membro@teste.com"))
        self.assertEqual(self.client.post(reverse("mover_demo", args=[self.demo.pk]), self.dados).status_code, 404)


class PainelDonoTest(TestCase):
    def test_dono_ve_o_proprio_restaurante_no_inicio(self):
        r = Restaurante.objects.create(nome="Cantina do Dono", latitude=-23.56, longitude=-46.65)
        dono = conta("dono@teste.com")
        Reivindicacao.objects.create(conta=dono, restaurante=r, cnpj="11.222.333/0001-81", status=StatusAnalise.APROVADA)
        self.client.force_login(dono)
        self.assertContains(self.client.get(reverse("inicio")), "Seu restaurante")
        self.client.force_login(conta("outra@teste.com"))
        self.assertNotContains(self.client.get(reverse("inicio")), "Seu restaurante")


class DuvidaTest(TestCase):
    """Regra "mais recente, com proteção"."""

    def setUp(self):
        self.r = Restaurante.objects.create(nome="Teste", latitude=-23.56, longitude=-46.65)
        self.e2 = ItemChecklist.objects.get(codigo="E2")  # porta larga: BLOQUEIA para cadeira de rodas
        self.cadeira = PerfilMobilidade.objects.get(codigo="cadeira")

    def responder(self, email, resposta, dias_atras):
        autor = Conta.objects.filter(email=email).first() or conta(email)
        av = AvaliacaoAcessibilidade.objects.create(autor=autor, restaurante=self.r,
                                                    data=timezone.now() - timedelta(days=dias_atras))
        RespostaItem.objects.create(avaliacao=av, item=self.e2, resposta=resposta)
        regras.recalcular(self.r)
        return SituacaoItem.objects.get(restaurante=self.r, item=self.e2)

    def resultado_cadeira(self):
        return ResultadoPerfil.objects.get(restaurante=self.r, perfil=self.cadeira).classificacao

    def test_resposta_isolada_contra_duas_pessoas_vira_duvida(self):
        self.responder("a@t.com", S, 10)
        self.responder("b@t.com", S, 8)
        s = self.responder("c@t.com", N, 1)
        self.assertTrue(s.em_duvida)
        self.assertEqual(s.resposta, S)  # não derrubou
        self.assertEqual(self.resultado_cadeira(), Classificacao.FALTA_INFORMACAO)

    def test_segunda_pessoa_confirma_a_mudanca(self):
        self.responder("a@t.com", S, 10)
        self.responder("b@t.com", S, 8)
        self.responder("c@t.com", N, 2)
        s = self.responder("d@t.com", N, 1)
        self.assertFalse(s.em_duvida)
        self.assertEqual(s.resposta, N)
        self.assertEqual(self.resultado_cadeira(), Classificacao.TEM_BARREIRA)
        abertas, _ = regras.pendencias(self.r)
        self.assertEqual([p["item"].codigo for p in abertas], ["E2"])

    def test_continua_igual_tira_da_duvida(self):
        self.responder("a@t.com", S, 10)
        self.responder("b@t.com", S, 8)
        s = self.responder("c@t.com", N, 2)
        regras.registrar_confirmacao(s, conta("d@t.com"))
        s.refresh_from_db()
        self.assertFalse(s.em_duvida)
        self.assertEqual(s.resposta, S)

    def test_a_mesma_pessoa_nao_desempata(self):
        self.responder("a@t.com", S, 10)
        self.responder("b@t.com", S, 8)
        self.responder("c@t.com", N, 2)
        s = self.responder("c@t.com", N, 1)
        self.assertTrue(s.em_duvida)

    def test_com_uma_pessoa_so_vale_a_mais_recente(self):
        self.responder("a@t.com", S, 10)
        s = self.responder("b@t.com", N, 1)
        self.assertFalse(s.em_duvida)
        self.assertEqual(s.resposta, N)


class EntrarEConfirmacaoTest(TestCase):
    """Entrar por uma janela e cadastro sem confirmar o e-mail (opcional)."""

    def setUp(self):
        self.r = Restaurante.objects.create(nome="Teste", latitude=-23.56, longitude=-46.65)

    def test_janela_entrar_so_para_quem_nao_entrou(self):
        self.assertContains(self.client.get(reverse("inicio")), 'id="dlg-entrar"')
        self.client.force_login(conta())
        self.assertNotContains(self.client.get(reverse("inicio")), 'id="dlg-entrar"')

    def test_login_da_janela_volta_para_o_endereco_leve(self):
        conta("ana@teste.com")
        resp = self.client.post(reverse("account_login"),
                                {"login": "ana@teste.com", "password": "senha-forte-123", "next": reverse("manifest")})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("manifest"))

    def test_login_errado_fica_na_pagina_com_o_erro(self):
        conta("ana@teste.com")
        resp = self.client.post(reverse("account_login"),
                                {"login": "ana@teste.com", "password": "errada", "next": reverse("manifest")})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "errorlist")

    def test_confirmacao_de_email_ligada_e_desligada(self):
        sem_confirmar = Conta.objects.create_user(email="novo@teste.com", password="senha-forte-123")
        self.client.force_login(sem_confirmar)
        url = reverse("avaliar", args=[self.r.pk])
        self.assertRedirects(self.client.get(url), reverse("account_email"), fetch_redirect_response=False)
        from django.conf import settings
        with override_settings(MOBITE={**settings.MOBITE, "CONFIRMAR_EMAIL": False}):
            self.assertEqual(self.client.get(url).status_code, 200)


class ChaveDemonstracaoTest(TestCase):
    """Botão do painel que mostra ou esconde os restaurantes fictícios do público (os anúncios continuam)."""

    def setUp(self):
        self.demo = Restaurante.objects.create(nome="Fictício da Silva", latitude=-23.56, longitude=-46.63,
                                               demonstracao=True)
        self.real = Restaurante.objects.create(nome="Real de Verdade", latitude=-23.56, longitude=-46.63)
        Anuncio.objects.create(titulo="Anúncio de exemplo", link=LINK_EXEMPLO)
        self.equipe = conta("equipe@teste.com", papel=Papel.EQUIPE_MOBITE)
        self.url = reverse("admin:alternar_demonstracao")

    def test_ligada_por_padrao(self):
        resp = self.client.get(reverse("inicio"))
        self.assertContains(resp, "Fictício da Silva")
        self.assertContains(resp, "Anúncio de exemplo")

    def test_equipe_esconde_e_mostra_de_novo(self):
        self.client.force_login(self.equipe)
        self.assertContains(self.client.get(reverse("admin:index")), "Esconder do público")
        self.assertRedirects(self.client.post(self.url), reverse("admin:index"))
        config = ConfiguracaoSite.atual()
        self.assertFalse(config.mostrar_demonstracao)
        self.assertEqual(config.alterado_por, self.equipe)
        self.client.logout()

        resp = self.client.get(reverse("inicio"))
        self.assertContains(resp, "Real de Verdade")
        self.assertNotContains(resp, "Fictício da Silva")
        self.assertContains(resp, "Anúncio de exemplo")
        self.assertEqual(self.client.get(reverse("detalhes", args=[self.demo.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("detalhes", args=[self.real.pk])).status_code, 200)

        self.client.force_login(self.equipe)  # a equipe ainda abre o fictício
        self.assertEqual(self.client.get(reverse("detalhes", args=[self.demo.pk])).status_code, 200)
        self.client.post(self.url)
        self.assertTrue(ConfiguracaoSite.atual().mostrar_demonstracao)

    def test_so_equipe_e_so_por_post(self):
        self.client.force_login(self.equipe)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(conta())
        self.client.post(self.url)
        self.assertTrue(ConfiguracaoSite.atual().mostrar_demonstracao)


class ImportarOsmTest(TestCase):
    """Importação a partir do arquivo guardado (como roda no servidor)."""

    def setUp(self):
        import json
        self.pasta = tempfile.mkdtemp()
        self.arquivo = f"{self.pasta}/osm.json"
        with open(self.arquivo, "w", encoding="utf-8") as f:
            json.dump({"elementos": [
                {"type": "node", "id": 1, "lat": -23.561, "lon": -46.636,
                 "tags": {"name": "Lamen Real", "addr:street": "Rua Taguá", "addr:housenumber": "10"}},
                {"type": "way", "id": 2, "center": {"lat": -23.562, "lon": -46.637}, "tags": {"name": "Sem Endereço"}},
                {"type": "node", "id": 3, "lat": -23.563, "lon": -46.638, "tags": {}},  # sem nome: fica de fora
            ]}, f)

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def importar(self, *extra):
        from django.core.management import call_command
        call_command("importar_osm", "--arquivo", self.arquivo, *extra, stdout=io.StringIO())

    def test_cria_real_com_falta_de_informacao(self):
        self.importar()
        self.assertEqual(Restaurante.objects.count(), 2)
        r = Restaurante.objects.get(osm_tipo="n", osm_id=1)
        self.assertEqual(r.endereco, "Rua Taguá, 10")
        self.assertFalse(r.demonstracao)
        self.assertEqual(r.situacoes.count(), ItemChecklist.objects.count())
        self.assertFalse(r.situacoes.exclude(resposta=Resposta.NAO_SEI).exists())
        self.assertFalse(r.resultados.exclude(classificacao=Classificacao.FALTA_INFORMACAO).exists())

    def test_reimportar_nao_apaga_o_que_a_equipe_corrigiu(self):
        self.importar()
        Restaurante.objects.filter(osm_id=2).update(endereco="Rua corrigida pela equipe, 5", nome="Nome da equipe")
        self.importar("--so-novos")
        self.assertEqual(Restaurante.objects.get(osm_id=2).nome, "Nome da equipe")
        self.importar()
        r = Restaurante.objects.get(osm_id=2)
        self.assertEqual(r.endereco, "Rua corrigida pela equipe, 5")
        self.assertEqual(Restaurante.objects.count(), 2)


class SenhasTest(TestCase):
    """Contas de teste com a senha do .env e painel entrando pelo login que bloqueia tentativas."""

    def test_login_do_painel_vai_para_o_login_do_site(self):
        resp = self.client.get(reverse("admin:login") + "?next=/equipe/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith(reverse("account_login")))
        self.assertIn("next=%2Fequipe%2F", resp["Location"])
        self.client.force_login(conta())  # conta comum não fica presa num vaivém de páginas
        self.assertRedirects(self.client.get("/equipe/"), reverse("admin:login") + "?next=/equipe/",
                             target_status_code=302)
        self.assertRedirects(self.client.get(reverse("admin:login") + "?next=/equipe/"), reverse("inicio"))

    def test_trocar_senha_nao_mexe_na_equipe(self):
        from django.core.management import call_command
        equipe = conta("equipe@mobite.example", papel=Papel.EQUIPE_MOBITE)
        teste = conta("mobite@mobite.example")
        with self.settings(MOBITE_SENHA_DEMO="outra-senha-123"):
            call_command("dados_demo", "--trocar-senha", stdout=io.StringIO())
        equipe.refresh_from_db(); teste.refresh_from_db()
        self.assertTrue(teste.check_password("outra-senha-123"))
        self.assertTrue(equipe.check_password("senha-forte-123"))


class ExcluirNoPainelTest(TestCase):
    """Excluir avaliação ou auditoria pelo painel refaz o resultado do restaurante."""

    def setUp(self):
        self.r = Restaurante.objects.create(nome="Bistrô", latitude=-23.56, longitude=-46.65)
        self.client.force_login(conta("equipe@teste.com", papel=Papel.EQUIPE_MOBITE))

    def avaliar(self):
        av = AvaliacaoAcessibilidade.objects.create(autor=conta(f"p{Conta.objects.count()}@teste.com"), restaurante=self.r)
        RespostaItem.objects.create(avaliacao=av, item=ItemChecklist.objects.get(codigo="E2"), resposta=S)
        regras.recalcular(self.r)
        return av

    def tem_resposta(self):
        return SituacaoItem.objects.get(restaurante=self.r, item__codigo="E2").tem_informacao

    def test_excluir_uma_avaliacao(self):
        av = self.avaliar()
        self.assertTrue(self.tem_resposta())
        self.client.post(reverse("admin:core_avaliacaoacessibilidade_delete", args=[av.pk]), {"post": "yes"})
        self.assertFalse(AvaliacaoAcessibilidade.objects.exists())
        self.assertFalse(self.tem_resposta())

    def test_excluir_varias_pela_lista(self):
        ids = [self.avaliar().pk, self.avaliar().pk]
        self.client.post(reverse("admin:core_avaliacaoacessibilidade_changelist"),
                         {"action": "delete_selected", "_selected_action": ids, "post": "yes"})
        self.assertFalse(AvaliacaoAcessibilidade.objects.exists())
        self.assertFalse(self.tem_resposta())

    def test_excluir_auditoria(self):
        from .models import Auditoria, RespostaAuditoria
        aud = Auditoria.objects.create(restaurante=self.r, data=timezone.now())
        RespostaAuditoria.objects.create(auditoria=aud, item=ItemChecklist.objects.get(codigo="E2"), resposta=S)
        regras.recalcular(self.r)
        self.assertTrue(self.tem_resposta())
        self.client.post(reverse("admin:core_auditoria_delete", args=[aud.pk]), {"post": "yes"})
        self.assertFalse(self.tem_resposta())


class EmailsTest(TestCase):
    """E-mails da conta saem com versão em texto e versão com a logo e o botão."""

    def html(self, m):
        return dict((tipo, corpo) for corpo, tipo in m.alternatives)["text/html"]

    def test_confirmacao_e_nova_senha(self):
        from django.core import mail
        self.client.post(reverse("account_signup"), {"email": "nova@teste.com", "password1": "Senha-forte-123",
                                                     "password2": "Senha-forte-123"})
        self.client.logout()
        self.client.post(reverse("account_reset_password"), {"email": "nova@teste.com"})
        confirmar, senha = mail.outbox
        self.assertEqual(confirmar.subject, "[MoBite] Confirme seu e-mail")
        self.assertIn("/contas/confirm-email/", confirmar.body)
        self.assertIn("http://testserver/static/img/logo-mobite.png", self.html(confirmar))
        self.assertIn("Confirmar e-mail", self.html(confirmar))
        self.assertEqual(senha.subject, "[MoBite] Crie uma nova senha")
        self.assertIn("/contas/password/reset/key/", self.html(senha))


class InicioTest(TestCase):
    """Topo do início em dois passos e o que a pessoa escondeu guardado num bloco fechado."""

    def test_passos_e_escondidos(self):
        from .models import PreferenciaRestaurante, TipoPreferencia
        r = Restaurante.objects.create(nome="Bistrô Escondido", latitude=-23.56, longitude=-46.65)
        pessoa = conta()
        PreferenciaRestaurante.objects.create(conta=pessoa, restaurante=r, tipo=TipoPreferencia.ESCONDIDO)
        self.client.force_login(pessoa)
        html = self.client.get(reverse("inicio")).content.decode()
        self.assertIn("Do que você precisa?", html)
        self.assertIn("Onde você está?", html)
        self.assertIn('placeholder="Procurar pelo nome"', html)
        self.assertNotIn("distância indisponível", html)
        fechado = html[html.index('<details id="ocultos"'):]
        self.assertIn("Bistrô Escondido", fechado[:fechado.index("</details>")])


class TelasDeContaTest(TestCase):
    """Cadastro e login com os textos do MoBite, e o resultado novo na tela de agradecimento."""

    def test_cadastro_e_login(self):
        cadastro = self.client.get(reverse("account_signup")).content.decode()
        self.assertNotIn("sign in", cadastro)
        self.assertIn(">E-mail</label>", cadastro)
        self.assertNotIn("password2", cadastro)  # senha uma vez só
        login = self.client.get(reverse("account_login")).content.decode()
        self.assertIn("Esqueci a senha", login)
        self.assertNotIn("remember", login)
        self.client.post(reverse("account_signup"), {"email": "nova@teste.com", "password1": "Senha-forte-123"})
        self.assertTrue(Conta.objects.filter(email="nova@teste.com").exists())

    def test_obrigado_traz_o_resultado_dos_perfis(self):
        r = Restaurante.objects.create(nome="Bistrô", latitude=-23.56, longitude=-46.65)
        self.client.force_login(conta())
        resp = self.client.post(reverse("avaliar", args=[r.pk]), {"r_E2": "SIM"}, follow=True)
        self.assertContains(resp, 'id="resultado-obrigado"')
        self.assertContains(resp, '"cadeira": "nd"')
