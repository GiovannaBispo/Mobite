"""Regras de negócio do resultado de acessibilidade (RN02) e das pendências (RN07.2).

Como a situação de cada item é montada (regra "mais recente, com proteção"):
- Entram, em ordem de data, as respostas visíveis das avaliações, as auditorias da equipe e os toques
  em "Continua igual". "Não sei" não muda nada.
- Vale a resposta mais recente, com uma proteção: se uma resposta sozinha contradiz um item que 2 ou mais
  pessoas confirmaram, o item fica "em dúvida" (e conta como "falta informação" no resultado).
- A dúvida termina quando outra pessoa responde: se concordar com a resposta nova, o item muda;
  se concordar com o que estava, ou tocar em "Continua igual", o item continua como estava.
  Uma resposta isolada não derruba o que várias pessoas confirmaram, mas também não é ignorada.

Como sai o resultado de um perfil (a matriz BLOQUEIA/IMPORTA está em PesoItemPerfil):
1. Algum item que BLOQUEIA está "não"            -> Tem barreira
2. Algum item que BLOQUEIA está sem resposta (ou em dúvida),
   ou 3+ itens relevantes estão sem resposta       -> Falta informação
3. Algum item que só IMPORTA está "não"          -> Funciona com ressalva
4. Senão                                         -> Funciona
O servidor calcula os 5 perfis; o navegador mostra só o do perfil guardado nele.
"""
from dataclasses import dataclass, field
from datetime import datetime

from django.conf import settings
from django.db import transaction

from .models import (Classificacao, Confirmacao, ItemChecklist, Peso, PerfilMobilidade, PesoItemPerfil, Resposta,
                     RespostaAuditoria, RespostaItem, ResultadoPerfil, SituacaoItem)

MIN_SEM_RESPOSTA = settings.MOBITE["MIN_SEM_RESPOSTA_FALTA_INFO"]
APOIO_PARA_PROTEGER = 2  # pessoas que precisam ter confirmado para uma resposta isolada virar "dúvida"


def classificar(pesos, respostas):
    """pesos: {codigo: Peso}; respostas: {codigo: Resposta normalizada}. Devolve (Classificacao, [codigos])."""
    bloqueiam = [c for c, p in pesos.items() if p == Peso.BLOQUEIA]
    importam = [c for c, p in pesos.items() if p == Peso.IMPORTA]
    sem = [c for c in pesos if respostas.get(c) not in (Resposta.SIM, Resposta.NAO)]

    barreiras = [c for c in bloqueiam if respostas.get(c) == Resposta.NAO]
    if barreiras:
        return Classificacao.TEM_BARREIRA, barreiras
    if any(c in sem for c in bloqueiam) or len(sem) >= MIN_SEM_RESPOSTA:
        return Classificacao.FALTA_INFORMACAO, sem
    ressalvas = [c for c in importam if respostas.get(c) == Resposta.NAO]
    if ressalvas:
        return Classificacao.FUNCIONA_COM_RESSALVA, ressalvas
    return Classificacao.FUNCIONA, []


def matriz_pesos():
    """{codigo_perfil: {codigo_item: peso}} para todos os perfis."""
    m = {p.codigo: {} for p in PerfilMobilidade.objects.all()}
    for peso in PesoItemPerfil.objects.select_related("perfil", "item"):
        m[peso.perfil.codigo][peso.item.codigo] = peso.peso
    return m


# ------------------------------------------------------------------ histórico de cada item
@dataclass
class Evento:
    data: datetime
    tipo: str              # "resposta" ou "confirmacao"
    pessoa: str            # quem (anônimos contam cada um como uma pessoa diferente)
    atende: str = ""       # Resposta normalizada (SIM = atende); vazio na confirmação
    origem: str = ""       # "avaliacao" ou "auditoria"
    com_foto: bool = False
    avaliacao_id: int | None = None


def historico_por_item(restaurante):
    """{codigo_item: [Evento...]} em ordem de data, só com o que está visível."""
    hist = {i.codigo: [] for i in ItemChecklist.objects.all()}
    respostas = (RespostaItem.objects
                 .filter(avaliacao__restaurante=restaurante, avaliacao__visivel=True)
                 .select_related("item", "avaliacao", "avaliacao__foto"))
    for r in respostas:
        foto = getattr(r.avaliacao, "foto", None)
        pessoa = f"conta-{r.avaliacao.autor_id}" if r.avaliacao.autor_id else f"anonimo-a{r.avaliacao_id}"
        hist[r.item.codigo].append(Evento(
            r.avaliacao.data, "resposta", pessoa, r.atende, "avaliacao",
            com_foto=bool(foto and foto.visivel and foto.proximidade_confirmada), avaliacao_id=r.avaliacao_id))
    for r in RespostaAuditoria.objects.filter(auditoria__restaurante=restaurante).select_related("item", "auditoria"):
        pessoa = f"conta-{r.auditoria.autor_id}" if r.auditoria.autor_id else f"auditoria-{r.auditoria_id}"
        hist[r.item.codigo].append(Evento(r.auditoria.data, "resposta", pessoa, r.atende, "auditoria"))
    for c in Confirmacao.objects.filter(situacao__restaurante=restaurante).select_related("situacao__item"):
        pessoa = f"conta-{c.autor_id}" if c.autor_id else f"anonimo-c{c.pk}"
        hist[c.situacao.item.codigo].append(Evento(c.data, "confirmacao", pessoa))
    for eventos in hist.values():
        eventos.sort(key=lambda e: e.data)
    return hist


@dataclass
class Estado:
    """Como um item ficou depois de percorrer o histórico."""
    resposta: str = Resposta.NAO_SEI          # SIM ou NAO estabelecido (NAO_SEI = sem resposta)
    apoio: set = field(default_factory=set)   # pessoas que sustentam a resposta atual
    duvida: dict | None = None                # {"valor", "pessoa", "data", "avaliacao_id", "apoio"}
    mudancas: list = field(default_factory=list)  # [(data, de, para, Evento)]
    ultima: datetime | None = None            # última verificação (resposta ou confirmação)
    evento_atual: Evento | None = None        # última resposta que sustenta o estado (alvo de denúncia)


def percorrer(eventos):
    """Aplica a regra "mais recente, com proteção" ao histórico de um item."""
    e = Estado()
    for ev in eventos:
        if ev.tipo == "confirmacao":
            if e.resposta == Resposta.NAO_SEI or (e.duvida and ev.pessoa == e.duvida["pessoa"]):
                continue
            e.apoio.add(ev.pessoa)
            e.duvida = None                      # "Continua igual" mantém o que estava
            e.ultima = ev.data
            continue
        if ev.atende not in (Resposta.SIM, Resposta.NAO):
            continue                             # "não sei" não muda nada
        e.ultima = ev.data
        if e.resposta == Resposta.NAO_SEI:       # primeira resposta
            e.mudancas.append((ev.data, None, ev.atende, ev))
            e.resposta, e.apoio, e.evento_atual = ev.atende, {ev.pessoa}, ev
            continue
        if e.duvida:
            if ev.pessoa == e.duvida["pessoa"]:  # a mesma pessoa não desempata
                if ev.atende == e.resposta:      # ...a não ser que volte atrás
                    e.duvida = None
                    e.apoio.add(ev.pessoa)
                continue
            if ev.atende == e.duvida["valor"]:   # outra pessoa confirma a mudança: o item muda
                e.mudancas.append((ev.data, e.resposta, ev.atende, ev))
                e.resposta, e.apoio, e.evento_atual = ev.atende, {e.duvida["pessoa"], ev.pessoa}, ev
            else:                                # outra pessoa confirma o que estava
                e.apoio.add(ev.pessoa)
                e.evento_atual = ev
            e.duvida = None
            continue
        if ev.atende == e.resposta:              # concorda
            e.apoio.add(ev.pessoa)
            e.evento_atual = ev
            continue
        e.apoio.discard(ev.pessoa)               # discorda (quem mudou de ideia deixa de apoiar o antigo)
        if len(e.apoio) >= APOIO_PARA_PROTEGER:
            e.duvida = {"valor": ev.atende, "pessoa": ev.pessoa, "data": ev.data,
                        "avaliacao_id": ev.avaliacao_id, "apoio": len(e.apoio)}
        else:
            e.mudancas.append((ev.data, e.resposta, ev.atende, ev))
            e.resposta, e.apoio, e.evento_atual = ev.atende, {ev.pessoa}, ev
    return e


def estados_por_item(restaurante, hist=None):
    hist = hist or historico_por_item(restaurante)
    return {codigo: percorrer(eventos) for codigo, eventos in hist.items()}


def recalcular_situacoes(restaurante, estados=None):
    estados = estados or estados_por_item(restaurante)
    situacoes = {s.item.codigo: s for s in restaurante.situacoes.select_related("item")}
    for item in ItemChecklist.objects.all():
        s = situacoes.get(item.codigo) or SituacaoItem.objects.create(restaurante=restaurante, item=item)
        e = estados[item.codigo]
        s.resposta = e.resposta
        s.em_duvida = e.duvida is not None
        s.confirmacoes = max(len(e.apoio) - 1, 0)   # quem confirmou além da primeira pessoa
        s.data_ultima_verificacao = e.ultima
        s.save()


def respostas_efetivas(situacoes):
    """Item em dúvida conta como sem resposta no resultado."""
    return {s.item.codigo: (Resposta.NAO_SEI if s.em_duvida else s.resposta) for s in situacoes}


def calcular_resultados(restaurante):
    respostas = respostas_efetivas(restaurante.situacoes.select_related("item"))
    for perfil_codigo, pesos in matriz_pesos().items():
        classe, _ = classificar(pesos, respostas)
        ResultadoPerfil.objects.update_or_create(
            restaurante=restaurante, perfil=PerfilMobilidade.objects.get(codigo=perfil_codigo),
            defaults={"classificacao": classe})


def resultados_com_motivo(situacoes, matriz):
    """{perfil: (classificacao, [itens que explicam])}, calculado na hora a partir das situações já carregadas."""
    respostas = respostas_efetivas(situacoes)
    return {perfil: classificar(pesos, respostas) for perfil, pesos in matriz.items()}


@transaction.atomic
def recalcular(restaurante):
    """Chamado depois de avaliação, auditoria, confirmação ou moderação."""
    recalcular_situacoes(restaurante)
    calcular_resultados(restaurante)


def pendencias(restaurante, estados=None):
    """Item com "não" vira pendência; quando o item muda de "não" para "sim", a pendência está resolvida.

    Devolve (abertas, resolvidas): listas de dicts com item, desde/quando e como.
    """
    estados = estados or estados_por_item(restaurante)
    itens = {i.codigo: i for i in ItemChecklist.objects.all()}
    abertas, resolvidas = [], []
    for codigo, e in estados.items():
        aberta_desde = None
        for data, _de, para, ev in e.mudancas:
            if para == Resposta.NAO:
                aberta_desde = data
            elif para == Resposta.SIM and aberta_desde is not None:
                como = ("visita da equipe MoBite" if ev.origem == "auditoria"
                        else "nova avaliação com foto" if ev.com_foto else "nova avaliação")
                resolvidas.append({"item": itens[codigo], "desde": aberta_desde, "quando": data, "como": como})
                aberta_desde = None
        if e.resposta == Resposta.NAO and aberta_desde is not None:
            abertas.append({"item": itens[codigo], "desde": aberta_desde})
    abertas.sort(key=lambda p: p["item"].ordem)
    resolvidas.sort(key=lambda p: p["quando"], reverse=True)
    return abertas, resolvidas


def avaliacao_que_definiu(restaurante, item, estados=None):
    """Alvo da denúncia "informação errada": a resposta que contradisse (se o item está em dúvida)
    ou a avaliação mais recente que sustenta a resposta atual."""
    estados = estados or estados_por_item(restaurante)
    e = estados[item.codigo]
    if e.duvida and e.duvida["avaliacao_id"]:
        return e.duvida["avaliacao_id"]
    if e.evento_atual and e.evento_atual.origem == "avaliacao":
        return e.evento_atual.avaliacao_id
    return None


def registrar_confirmacao(situacao, autor):
    Confirmacao.objects.create(situacao=situacao, autor=autor)
    recalcular(situacao.restaurante)
