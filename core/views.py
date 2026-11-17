"""Páginas e ações do MoBite.

O perfil de mobilidade e a localização de quem consulta NUNCA chegam aqui (RN01.2):
o servidor manda o resultado dos 5 perfis e o navegador mostra o do perfil guardado nele.
"""
import json
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import regras
from .forms import (AvaliacaoForm, ContaForm, DadosBasicosForm, DenunciaForm, ReivindicacaoForm,
                    RespostaEstabelecimentoForm)
from .templatetags.mobite import ha_dias
from .models import (Anuncio, AvaliacaoAcessibilidade, AvaliacaoAtendimento, Classificacao, ConsultaDiaria, Conta,
                     Denuncia, FotoEntrada, ItemChecklist, PreferenciaRestaurante,
                     Reivindicacao, Resposta, RespostaEstabelecimento, RespostaItem, Restaurante, SituacaoItem,
                     StatusAnalise, TipoPreferencia, Zona)

CFG = settings.MOBITE
CSS = {Classificacao.FUNCIONA: "ok", Classificacao.FUNCIONA_COM_RESSALVA: "warn",
       Classificacao.TEM_BARREIRA: "bar", Classificacao.FALTA_INFORMACAO: "nd"}
PALETAS = [  # cores das fachadas r1 a r10 desenhadas pela Giovanna: (fundo, toldo)
    ("#f6e2c4", "#c8553d"), ("#dcecf3", "#2f6f8f"), ("#e2f0e3", "#3d7a5c"), ("#f1e4d3", "#7a5230"),
    ("#f8ecd0", "#b8872e"), ("#f6dcd6", "#a63d2f"), ("#e1e9f5", "#4a6fa5"), ("#f7e6d0", "#b5651d"),
    ("#eaf1de", "#6b8e4e"), ("#f4dfe3", "#8c3b4a"),
]


# ------------------------------------------------------------------ ajudantes
def conta_confirmada(view):
    """Exige conta com e-mail confirmado (RN03.1). Quem entrou com Google já vem confirmado.
    Com MOBITE_CONFIRMAR_EMAIL=0 no servidor, basta estar conectado."""
    @wraps(view)
    @login_required
    def _view(request, *args, **kwargs):
        if settings.MOBITE["CONFIRMAR_EMAIL"] and not (request.user.is_staff or request.user.email_confirmado):
            messages.warning(request, "Confirme seu e-mail para avaliar. Dá para reenviar o link aqui.")
            return redirect("account_email")
        return view(request, *args, **kwargs)
    return _view


def dias_atras(data):
    return None if data is None else (timezone.now() - data).days


def nomes_itens(codigos, itens, limite=3):
    nomes = [itens[c].nome.lower() for c in codigos if c in itens]
    if len(nomes) > limite:
        resto = len(nomes) - limite
        return ", ".join(nomes[:limite]) + f" e mais {resto} ite{'m' if resto == 1 else 'ns'}"
    return ", ".join(nomes)


def prefs_da_conta(user):
    if not user.is_authenticated:
        return {}
    return dict(PreferenciaRestaurante.objects.filter(conta=user).values_list("restaurante_id", "tipo"))


def montar_cards(restaurantes, user):
    """Dados de cada card. Os resultados vão todos; o navegador escolhe o do perfil."""
    restaurantes = list(restaurantes.annotate(
        media=Avg("atendimentos__estrelas", filter=Q(atendimentos__visivel=True)),
        n_atend=Count("atendimentos", filter=Q(atendimentos__visivel=True), distinct=True),
    ).prefetch_related("situacoes__item"))
    ids = [r.pk for r in restaurantes]
    n_fotos = dict(fotos_visiveis().filter(avaliacao__restaurante_id__in=ids).values("avaliacao__restaurante")
                   .annotate(n=Count("id")).values_list("avaliacao__restaurante", "n"))
    prefs = prefs_da_conta(user)
    itens = {i.codigo: i for i in ItemChecklist.objects.all()}
    matriz = regras.matriz_pesos()
    cards = []
    for r in restaurantes:
        situacoes = list(r.situacoes.all())
        ultima = max((s.data_ultima_verificacao for s in situacoes if s.data_ultima_verificacao), default=None)
        resultados, motivos = {}, {}
        for perfil, (classe, cods) in regras.resultados_com_motivo(situacoes, matriz).items():
            resultados[perfil] = CSS[classe]
            motivos[perfil] = nomes_itens(cods, itens)
        cards.append({
            "r": r,
            "n_fotos": n_fotos.get(r.pk, 0),  # a capa é sempre a ilustração; as fotos ficam na página do lugar
            "resultados": json.dumps(resultados),
            "motivos": json.dumps(motivos, ensure_ascii=False),
            "itens_ok": ",".join(s.item.codigo for s in situacoes if s.resposta == Resposta.SIM and not s.em_duvida),
            "media": r.media, "n_atend": r.n_atend,
            "dias": dias_atras(ultima),
            "fav": prefs.get(r.pk) == TipoPreferencia.FAVORITO,
            "escondido": prefs.get(r.pk) == TipoPreferencia.ESCONDIDO,
        })
    return cards


def fotos_visiveis():
    """Fotos aceitas (a até 150 m), de avaliação visível e não ocultadas pela moderação."""
    return FotoEntrada.objects.filter(avaliacao__visivel=True, visivel=True, proximidade_confirmada=True)


def visiveis():
    return Restaurante.publicos()


# ------------------------------------------------------------------ páginas de consulta (sem conta, RI01)
def inicio(request):
    """A lista é a tela inicial: topo, filtros, lista e mapa na mesma página.
    Quem administra restaurante vê primeiro o painel do próprio lugar."""
    cards = montar_cards(visiveis(), request.user)
    return render(request, "core/inicio.html", {
        "cards": [c for c in cards if not c["escondido"]],
        "ocultos": [c for c in cards if c["escondido"]],
        "q": request.GET.get("q", "")[:80],
        "paineis": paineis_do_dono(request.user),
    })


def restaurantes_do_dono(user):
    if not user.is_authenticated:
        return Restaurante.objects.none()
    return Restaurante.objects.filter(reivindicacoes__conta=user, reivindicacoes__status=StatusAnalise.APROVADA).distinct()


def paineis_do_dono(user):
    """Painel do lugar: só números somados, sem dizer quem consultou ou avaliou."""
    desde = timezone.now() - timedelta(days=30)
    paineis = []
    for r in restaurantes_do_dono(user):
        abertas, _ = regras.pendencias(r)
        assinatura = r.assinaturas.filter(status="ATIVA").order_by("-data_fim").first()
        paineis.append({
            "r": r,
            "resultados": [(res.perfil.nome, CSS[res.classificacao])
                           for res in r.resultados.select_related("perfil").order_by("perfil__ordem")],
            "abertas": abertas,
            "consultas": (ConsultaDiaria.objects.filter(restaurante=r, data__gte=timezone.localdate(desde))
                          .aggregate(t=Sum("total"))["t"] or 0),
            "avaliacoes": r.avaliacoes.filter(visivel=True, data__gte=desde).count(),
            "assinatura": r.assinatura_ativa(),
            "assinatura_fim": assinatura.data_fim if assinatura else None,
        })
    return paineis


def restaurantes(request):
    """Endereço antigo de "Encontrar restaurantes", que virou o Início."""
    destino = reverse("inicio")
    return redirect(destino + ("?" + request.GET.urlencode() if request.GET else ""))


def mapa(request):
    """O mapa agora é uma aba ao lado da lista; o endereço antigo leva para lá."""
    return redirect(reverse("inicio") + "?vista=mapa")


def contar_consulta(request, restaurante):
    """Conta a consulta sem saber quem consultou. Quem tem sessão conta 1 vez por dia.
    Não contam a equipe nem quem já avaliou o lugar (a pessoa não "ajuda" a si mesma)."""
    if request.user.is_staff:
        return
    if request.user.is_authenticated and restaurante.avaliacoes.filter(autor=request.user).exists():
        return
    chave = f"c{restaurante.pk}-{timezone.localdate():%Y%m%d}"
    if request.session.session_key:
        vistos = request.session.get("consultas", [])
        if chave in vistos:
            return
        request.session["consultas"] = (vistos + [chave])[-200:]
    ConsultaDiaria.objects.get_or_create(restaurante=restaurante, data=timezone.localdate())
    ConsultaDiaria.objects.filter(restaurante=restaurante, data=timezone.localdate()).update(total=F("total") + 1)


def descrever_foto(foto, itens):
    """Texto alternativo da foto, gerado a partir das respostas da mesma avaliação (para leitor de tela)."""
    partes = []
    for resp in foto.avaliacao.respostas.select_related("item"):
        atende = resp.atende
        if atende == Resposta.SIM:
            partes.append(resp.item.nome.lower())
        elif atende == Resposta.NAO:
            partes.append(f"sem {resp.item.nome.lower()}" if not resp.item.nome.lower().startswith("entrada sem")
                          else "entrada com degrau")
    dias = dias_atras(foto.data_envio)
    quando = "hoje" if dias == 0 else f"há {dias} dias"
    base = f"Foto da entrada enviada {quando}"
    return base + (". Segundo quem enviou: " + ", ".join(partes) + "." if partes else ".")


def detalhes(request, pk):
    r = get_object_or_404(Restaurante, pk=pk)
    if not r.publico() and not request.user.is_staff:
        raise Http404
    contar_consulta(request, r)
    estados = regras.estados_por_item(r)
    itens = {i.codigo: i for i in ItemChecklist.objects.all()}
    situacoes = list(r.situacoes.select_related("item").prefetch_related(
        "respostas_estabelecimento", "confirmacoes_feitas"))
    respostas_rest = {s.pk: next((x for x in s.respostas_estabelecimento.all() if x.visivel), None) for s in situacoes}
    hoje = timezone.now()
    eu = request.user if request.user.is_authenticated else None
    confirmei = set()
    if eu:
        confirmei = set(r.situacoes.filter(confirmacoes_feitas__autor=eu,
                                           confirmacoes_feitas__data__gte=hoje - timedelta(days=1))
                        .values_list("pk", flat=True))
    zonas = []
    for zona_valor, zona_nome in Zona.choices:
        linhas = []
        for s in [s for s in situacoes if s.item.zona == zona_valor]:
            dias = s.dias_desde_verificacao()
            duvida = estados[s.item.codigo].duvida if s.em_duvida else None
            linhas.append({
                "s": s, "item": s.item,
                "estado": ("nd" if duvida else "ok" if s.resposta == Resposta.SIM
                           else "bar" if s.resposta == Resposta.NAO else "nd"),
                "rotulo": "Em dúvida" if duvida else None,
                "duvida": duvida and {"antes": Resposta(s.resposta).label, "apoio": duvida["apoio"],
                                      "novo": Resposta(duvida["valor"]).label, "dias": dias_atras(duvida["data"])},
                "dias": dias, "desatualizado": dias is not None and dias > CFG["DIAS_ITEM_DESATUALIZADO"],
                "resposta_rest": respostas_rest.get(s.pk),
                "avaliacao_origem": regras.avaliacao_que_definiu(r, s.item, estados),
                "confirmei": s.pk in confirmei,
            })
        zonas.append({"nome": zona_nome, "linhas": linhas})
    abertas, resolvidas = regras.pendencias(r, estados)
    for p in abertas + resolvidas:
        p["dias_desde"] = dias_atras(p["desde"])
        if "quando" in p:
            p["dias_quando"] = dias_atras(p["quando"])
        sit = next(s for s in situacoes if s.item_id == p["item"].pk)
        p["resposta_rest"] = respostas_rest.get(sit.pk)
    resultados = {perfil: {"css": CSS[classe], "motivo": nomes_itens(cods, itens)}
                  for perfil, (classe, cods) in regras.resultados_com_motivo(situacoes, regras.matriz_pesos()).items()}
    media, n_atend = r.media_atendimento()
    # Todas as fotos aceitas, da mais nova para a mais antiga. Nenhuma vira capa: a foto ilustra, o resultado vem dos itens.
    fotos = list(fotos_visiveis().filter(avaliacao__restaurante=r).select_related("avaliacao")
                 .order_by("-data_envio")[:12])
    galeria = [{"f": f, "alt": descrever_foto(f, itens)} for f in fotos]
    total_fotos = fotos_visiveis().filter(avaliacao__restaurante=r).count()
    # "Quem já foi": quantas contas diferentes contribuíram (avaliação ou confirmação), sem dizer quem.
    autores = set(AvaliacaoAcessibilidade.objects.filter(restaurante=r, visivel=True).values_list("autor_id", flat=True))
    autores |= set(SituacaoItem.objects.filter(restaurante=r).values_list("confirmacoes_feitas__autor_id", flat=True))
    anonimos = (AvaliacaoAcessibilidade.objects.filter(restaurante=r, visivel=True, autor__isnull=True).count())
    contribuintes = len([a for a in autores if a]) + anonimos
    publicos = [(c.apelido, c.obter_selo().label) for c in
                Conta.objects.filter(avaliacoes__restaurante=r, avaliacoes__visivel=True,
                                     aparecer_publicamente=True).exclude(apelido="").distinct()]
    responsavel = bool(eu) and r.responsaveis().filter(pk=eu.pk).exists()
    assinatura = r.assinatura_ativa()
    # Ordem sugerida das perguntas sem perfil (o navegador reordena pelo perfil): sem resposta, desatualizadas, resto.
    fila = sorted(situacoes, key=lambda s: (0 if not s.tem_informacao or s.em_duvida else 1 if not s.esta_verificado() else 2,
                                            s.item.ordem))
    padrao = {s.item.codigo for s in fila[:CFG["MAX_PERGUNTAS"]]}
    estado_item = {s.item.codigo: ("sem" if not s.tem_informacao or s.em_duvida else "antigo" if not s.esta_verificado() else "ok")
                   for s in situacoes}
    form = AvaliacaoForm(restaurante=r)
    return render(request, "core/detalhes.html", {
        "r": r, "zonas": zonas, "abertas": abertas, "resolvidas": resolvidas,
        "resultados_json": resultados, "media": media, "n_atend": n_atend,
        "galeria": galeria, "total_fotos": total_fotos,
        "contribuintes": contribuintes, "publicos": publicos,
        "responsavel": responsavel, "assinatura": assinatura,
        "reivindicacao": (Reivindicacao.objects.filter(conta=eu, restaurante=r).order_by("-data_solicitacao").first()
                          if eu else None),
        "pref": prefs_da_conta(request.user).get(r.pk),
        "form": form, "perguntas": perguntas_do_form(form, padrao, estado_item),
    })


def perguntas_do_form(form, padrao, estado_item):
    return [{"campo": form[f"r_{i.codigo}"], "item": i, "visivel": i.codigo in padrao,
             "estado": estado_item.get(i.codigo, "sem")} for i in form.itens]


def fachada(request, pk):
    """Ilustração da fachada no estilo das imagens da Giovanna, para quem ainda não tem foto."""
    r = get_object_or_404(Restaurante, pk=pk)
    fundo, toldo = PALETAS[(r.pk - 1) % len(PALETAS)]
    svg = render_to_string("core/fachada.svg", {"fundo": fundo, "toldo": toldo, "listras": range(40, 360, 40)})
    resp = HttpResponse(svg, content_type="image/svg+xml")
    resp["Cache-Control"] = "public, max-age=86400"
    return resp


# ------------------------------------------------------------------ avaliar (RN03)
@conta_confirmada
def avaliar(request, pk):
    r = get_object_or_404(visiveis(), pk=pk)
    if request.method == "POST":
        form = AvaliacaoForm(request.POST, request.FILES, restaurante=r)
        if form.is_valid():
            agora = timezone.now()
            with transaction.atomic():
                respostas = form.respostas()
                if respostas:
                    no_dia = (ConsultaDiaria.objects.filter(restaurante=r, data=timezone.localdate(agora))
                              .values_list("total", flat=True).first() or 0)
                    av = AvaliacaoAcessibilidade.objects.create(autor=request.user, restaurante=r, data=agora,
                                                                consultas_no_dia=no_dia)
                    RespostaItem.objects.bulk_create(
                        [RespostaItem(avaliacao=av, item=i, resposta=v) for i, v in respostas.items()])
                    if form.foto_tratada:
                        FotoEntrada.objects.create(avaliacao=av, arquivo=form.foto_tratada, data_envio=agora,
                                                   proximidade_confirmada=True)
                    regras.recalcular(r)
                if form.cleaned_data.get("estrelas"):
                    AvaliacaoAtendimento.objects.create(autor=request.user, restaurante=r,
                                                        estrelas=form.cleaned_data["estrelas"], data=agora)
            request.session["obrigado"] = {"r": r.pk, "n": len(respostas), "foto": bool(form.foto_tratada),
                                           "estrelas": form.cleaned_data.get("estrelas") or 0}
            return redirect("obrigado", pk=r.pk)
    else:
        form = AvaliacaoForm(restaurante=r)
    estado = {s.item.codigo: ("sem" if not s.tem_informacao or s.em_duvida else "antigo" if not s.esta_verificado() else "ok")
              for s in r.situacoes.select_related("item")}
    marcados = {i.codigo for i in form.itens if form.data.get(f"r_{i.codigo}")} if form.is_bound else set()
    fila = sorted(form.itens, key=lambda i: ({"sem": 0, "antigo": 1}.get(estado.get(i.codigo), 2), i.ordem))
    padrao = marcados or {i.codigo for i in fila[:CFG["MAX_PERGUNTAS"]]}
    return render(request, "core/avaliar.html", {"r": r, "form": form,
                                                 "perguntas": perguntas_do_form(form, padrao, estado)})


@login_required
def obrigado(request, pk):
    r = get_object_or_404(Restaurante, pk=pk)
    info = request.session.pop("obrigado", None)
    if not info or info.get("r") != r.pk:
        return redirect("detalhes", pk=r.pk)
    total = request.user.total_avaliacoes()
    # Bloco de anúncio "de vez em quando": 1 a cada N avaliações (RN06.3).
    mostrar_anuncio = info["n"] > 0 and total % CFG["ANUNCIO_A_CADA_AVALIACOES"] == 1
    # Resultado novo dos 5 perfis: o navegador mostra só o do perfil guardado nele
    resultado = {res.perfil.codigo: CSS[res.classificacao] for res in r.resultados.select_related("perfil")}
    return render(request, "core/obrigado.html", {"r": r, "info": info, "total": total, "resultado": resultado,
                                                  "mostrar_anuncio": mostrar_anuncio,
                                                  "anuncios_obrigado": list(Anuncio.ativos()) if mostrar_anuncio else []})


@conta_confirmada
def confirmar(request, pk, codigo):
    """RN03.6: confirmar com um toque que o item continua igual.

    Quem não estava logado passa pelo login e volta aqui por GET: nada é gravado sem o toque,
    então a pessoa volta ao item e confirma de novo."""
    r = get_object_or_404(visiveis(), pk=pk)
    s = get_object_or_404(SituacaoItem, restaurante=r, item__codigo=codigo)
    if request.method != "POST":
        messages.info(request, "Agora é só tocar de novo em “Continua igual”.")
        return redirect(reverse("detalhes", args=[pk]) + f"#item-{codigo}")
    estava_em_duvida = s.em_duvida
    if not s.tem_informacao:
        mensagem = "Esse item ainda não tem resposta. Avalie o lugar para responder."
    elif s.confirmacoes_feitas.filter(autor=request.user, data__gte=timezone.now() - timedelta(days=1)).exists():
        mensagem = "Você já confirmou esse item hoje."
    else:
        regras.registrar_confirmacao(s, request.user)
        s.refresh_from_db()
        mensagem = f"Obrigado! “{s.item.nome}” confirmado."
    if "application/json" in request.headers.get("Accept", ""):  # o botão confirma sem recarregar a página
        return JsonResponse({"mensagem": mensagem, "verificacao": texto_verificacao(s),
                             "recarregar": estava_em_duvida != s.em_duvida})
    messages.success(request, mensagem)
    return redirect(reverse("detalhes", args=[pk]) + f"#item-{codigo}")


def texto_verificacao(s):
    """O mesmo texto da linha do item: "Verificado há N dias · N confirmações"."""
    dias = s.dias_desde_verificacao()
    if dias is None:
        return "Sem respostas"
    if s.em_duvida:
        return "Em dúvida"
    texto = f"Verificado {ha_dias(dias)}"
    if s.confirmacoes:
        texto += f" · {s.confirmacoes} confirmaç{'ão' if s.confirmacoes == 1 else 'ões'}"
    if dias > CFG["DIAS_ITEM_DESATUALIZADO"]:
        texto += " · desatualizado"
    return texto


@require_POST
def preferencia(request, pk):
    """Favoritar ou esconder da própria lista (exige conta). Responde JSON para o botão sem recarregar."""
    quer_json = "application/json" in request.headers.get("Accept", "")
    if not request.user.is_authenticated:
        login = f"{reverse('account_login')}?next={request.POST.get('next') or reverse('detalhes', args=[pk])}"
        return JsonResponse({"login": login}, status=401) if quer_json else redirect(login)
    r = get_object_or_404(Restaurante, pk=pk)
    tipo = request.POST.get("tipo")
    if tipo not in TipoPreferencia.values:
        return JsonResponse({"erro": "tipo"}, status=400)
    atual = PreferenciaRestaurante.objects.filter(conta=request.user, restaurante=r).first()
    if atual and atual.tipo == tipo:
        atual.delete()
        estado = None
    else:
        PreferenciaRestaurante.objects.update_or_create(conta=request.user, restaurante=r,
                                                        defaults={"tipo": tipo, "data": timezone.now()})
        estado = tipo
    if quer_json:
        return JsonResponse({"estado": estado})
    return redirect(request.POST.get("next") or reverse("detalhes", args=[pk]))


# ------------------------------------------------------------------ páginas da conta
@login_required
def favoritos(request):
    ids = PreferenciaRestaurante.objects.filter(conta=request.user, tipo=TipoPreferencia.FAVORITO).values("restaurante")
    return render(request, "core/favoritos.html", {"cards": montar_cards(visiveis().filter(pk__in=ids), request.user)})


@login_required
def minhas_avaliacoes(request):
    avals = (AvaliacaoAcessibilidade.objects.filter(autor=request.user)
             .select_related("restaurante").prefetch_related("respostas__item"))
    atend = {(a.restaurante_id, a.data): a for a in AvaliacaoAtendimento.objects.filter(autor=request.user)}
    lista = [{"a": a, "atendimento": atend.pop((a.restaurante_id, a.data), None),
              "foto": getattr(a, "foto", None), "ajudou": a.consultas_depois()} for a in avals]
    soltas = sorted(atend.values(), key=lambda a: a.data, reverse=True)  # só estrelas, sem perguntas
    return render(request, "core/avaliacoes.html", {"lista": lista, "soltas": soltas,
                                                    "ajudadas": request.user.contar_pessoas_ajudadas()})


@require_POST
@login_required
def excluir_avaliacao(request, pk):
    a = get_object_or_404(AvaliacaoAcessibilidade, pk=pk, autor=request.user)
    r = a.restaurante
    with transaction.atomic():
        AvaliacaoAtendimento.objects.filter(autor=request.user, restaurante=r, data=a.data).delete()
        foto = getattr(a, "foto", None)
        if foto:
            foto.arquivo.delete(save=False)
        a.delete()
        regras.recalcular(r)
    messages.success(request, f"Avaliação de {r.nome} excluída.")
    return redirect("avaliacoes")


@require_POST
@login_required
def excluir_atendimento(request, pk):
    get_object_or_404(AvaliacaoAtendimento, pk=pk, autor=request.user).delete()
    messages.success(request, "Avaliação de atendimento excluída.")
    return redirect("avaliacoes")


def perfil(request):
    """O perfil de mobilidade é salvo pelo navegador (localStorage). Aqui só se mexe na conta."""
    form = None
    if request.user.is_authenticated:
        form = ContaForm(request.POST or None, instance=request.user)
        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(request, "Conta atualizada.")
            return redirect("perfil")
    ctx = {"form": form}
    if request.user.is_authenticated:
        u = request.user
        ctx.update(total=u.total_avaliacoes(), selo=u.obter_selo(), ajudadas=u.contar_pessoas_ajudadas(),
                   favs=Restaurante.objects.filter(preferencias__conta=u, preferencias__tipo=TipoPreferencia.FAVORITO),
                   meus_restaurantes=Restaurante.objects.filter(reivindicacoes__conta=u,
                                                                reivindicacoes__status=StatusAnalise.APROVADA))
    return render(request, "core/perfil.html", ctx)


@login_required
def excluir_conta(request):
    if request.method == "POST" and request.POST.get("confirmo") == "sim":
        conta = request.user
        logout(request)
        conta.excluir_conta()
        messages.success(request, "Sua conta foi excluída.")
        return redirect("inicio")
    return render(request, "core/excluir_conta.html")


# ------------------------------------------------------------------ restaurante como cliente (RN06)
@login_required
def reivindicar(request, pk):
    r = get_object_or_404(visiveis(), pk=pk)
    existente = Reivindicacao.objects.filter(conta=request.user, restaurante=r).exclude(
        status=StatusAnalise.REJEITADA).first()
    form = ReivindicacaoForm(request.POST or None)
    if request.method == "POST" and not existente and form.is_valid():
        Reivindicacao.objects.create(conta=request.user, restaurante=r, cnpj=form.cleaned_data["cnpj"])
        messages.success(request, "Pedido enviado. Avisamos por e-mail quando for aprovado.")
        return redirect("detalhes", pk=pk)
    return render(request, "core/reivindicar.html", {"r": r, "form": form, "existente": existente})


def exigir_responsavel(request, r):
    if not (request.user.is_authenticated and r.responsaveis().filter(pk=request.user.pk).exists()):
        raise Http404


@login_required
def responder(request, pk, codigo):
    """RN06.1: só responsável com assinatura ativa responde. A resposta fica junto do item."""
    r = get_object_or_404(Restaurante, pk=pk)
    exigir_responsavel(request, r)
    s = get_object_or_404(SituacaoItem, restaurante=r, item__codigo=codigo)
    if not r.assinatura_ativa():
        return render(request, "core/responder.html", {"r": r, "s": s, "sem_assinatura": True})
    atual = s.respostas_estabelecimento.filter(visivel=True).first()
    form = RespostaEstabelecimentoForm(request.POST or None, instance=atual)
    if request.method == "POST" and form.is_valid():
        if atual:
            atual.editar(form.cleaned_data["texto"])
        else:
            RespostaEstabelecimento.objects.create(situacao=s, autor=request.user, texto=form.cleaned_data["texto"])
        messages.success(request, "Resposta publicada junto do item.")
        return redirect(reverse("detalhes", args=[pk]) + f"#item-{codigo}")
    return render(request, "core/responder.html", {"r": r, "s": s, "form": form, "atual": atual})


@require_POST
@login_required
def mover_demo(request, pk):
    """Ferramenta da equipe: traz um restaurante DE DEMONSTRAÇÃO para perto de onde a pessoa está,
    para testar ou apresentar a foto (aceita só a até 150 m). Restaurante real nunca é movido."""
    r = get_object_or_404(Restaurante, pk=pk, demonstracao=True)
    if not request.user.is_staff:
        raise Http404
    try:
        lat, lon = float(request.POST["lat"]), float(request.POST["lon"])
    except (KeyError, ValueError):
        messages.error(request, "Não recebemos a localização do aparelho. Permita a localização e tente de novo.")
        return redirect("detalhes", pk=pk)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise Http404
    r.latitude, r.longitude = lat + 20 / 111_320, lon  # uns 20 m ao norte de quem está com o celular
    r.save(update_fields=["latitude", "longitude"])
    messages.success(request, f"Pronto: {r.nome} agora fica a uns 20 m de você.")
    return redirect("detalhes", pk=pk)


@login_required
def editar_dados(request, pk):
    r = get_object_or_404(Restaurante, pk=pk)
    exigir_responsavel(request, r)
    form = DadosBasicosForm(request.POST or None, instance=r)
    if request.method == "POST" and form.is_valid():
        r.editar_dados_basicos(form.cleaned_data["telefone"], form.cleaned_data["horario"])
        messages.success(request, "Dados atualizados.")
        return redirect("detalhes", pk=pk)
    return render(request, "core/editar_dados.html", {"r": r, "form": form})


# ------------------------------------------------------------------ denúncia (RN07.1)
ALVOS = {"avaliacao": (AvaliacaoAcessibilidade, "avaliacao"), "foto": (FotoEntrada, "foto"),
         "resposta": (RespostaEstabelecimento, "resposta_estabelecimento")}


@login_required
def denunciar(request, tipo, pk):
    if tipo not in ALVOS:
        raise Http404
    modelo, campo = ALVOS[tipo]
    alvo = get_object_or_404(modelo, pk=pk)
    r = (alvo.restaurante if tipo == "avaliacao" else alvo.avaliacao.restaurante if tipo == "foto"
         else alvo.situacao.restaurante)
    form = DenunciaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ja = Denuncia.objects.filter(autor=request.user, status=StatusAnalise.PENDENTE, **{campo: alvo}).exists()
        if not ja:
            Denuncia.objects.create(autor=request.user, motivo=form.cleaned_data["motivo"],
                                    descricao=form.cleaned_data["descricao"], **{campo: alvo})
        messages.success(request, "Denúncia enviada. Obrigado por avisar.")
        return redirect("detalhes", pk=r.pk)
    return render(request, "core/denunciar.html", {"form": form, "r": r, "tipo": tipo})


# ------------------------------------------------------------------ anúncios, PWA e páginas fixas
def anuncio(request, pk):
    """Conta o clique sem ligar à conta de quem clicou (RI08) e leva ao anunciante."""
    a = get_object_or_404(Anuncio, pk=pk)
    Anuncio.objects.filter(pk=pk).update(cliques=F("cliques") + 1)
    return redirect(a.link)


def manifest(request):
    return render(request, "pwa/manifest.webmanifest", content_type="application/manifest+json")


def service_worker(request):
    resp = render(request, "pwa/sw.js", content_type="application/javascript")
    resp["Cache-Control"] = "no-cache"
    return resp


def pagina(template):
    def _view(request):
        return render(request, template)
    return _view
