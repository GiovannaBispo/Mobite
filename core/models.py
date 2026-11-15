"""Modelos do MoBite, seguindo o diagrama de classes final (Figura 2 do trabalho escrito).

O que não está no diagrama vem marcado com "[fora da UML]".
"""
import math
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

CFG = settings.MOBITE


# ---------------------------------------------------------------- enums
class Papel(models.TextChoices):
    MEMBRO = "MEMBRO", "Membro"
    EQUIPE_MOBITE = "EQUIPE_MOBITE", "Equipe MoBite"


class StatusConta(models.TextChoices):
    ATIVA = "ATIVA", "Ativa"
    BLOQUEADA = "BLOQUEADA", "Bloqueada"


class Zona(models.TextChoices):
    CHEGADA = "CHEGADA", "Chegada"
    ENTRADA = "ENTRADA", "Entrada"
    INTERIOR = "INTERIOR", "Interior"
    BANHEIRO = "BANHEIRO", "Banheiro"


class Peso(models.TextChoices):
    BLOQUEIA = "BLOQUEIA", "Bloqueia"
    IMPORTA = "IMPORTA", "Importa"


class Resposta(models.TextChoices):
    SIM = "SIM", "Sim"
    NAO = "NAO", "Não"
    NAO_SEI = "NAO_SEI", "Não sei"


class Classificacao(models.TextChoices):
    FUNCIONA = "FUNCIONA", "Funciona"
    FUNCIONA_COM_RESSALVA = "FUNCIONA_COM_RESSALVA", "Funciona com ressalva"
    TEM_BARREIRA = "TEM_BARREIRA", "Tem barreira"
    FALTA_INFORMACAO = "FALTA_INFORMACAO", "Falta informação"


class Selo(models.TextChoices):
    INICIANTE = "INICIANTE", "Iniciante"
    COLABORADOR = "COLABORADOR", "Colaborador"
    REFERENCIA = "REFERENCIA", "Referência"


class TipoPreferencia(models.TextChoices):
    FAVORITO = "FAVORITO", "Favorito"
    ESCONDIDO = "ESCONDIDO", "Escondido"


class StatusAnalise(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    APROVADA = "APROVADA", "Aprovada"
    REJEITADA = "REJEITADA", "Rejeitada"


class StatusAssinatura(models.TextChoices):
    ATIVA = "ATIVA", "Ativa"
    EXPIRADA = "EXPIRADA", "Expirada"
    CANCELADA = "CANCELADA", "Cancelada"


class MotivoDenuncia(models.TextChoices):
    INFORMACAO_FALSA = "INFORMACAO_FALSA", "Informação falsa"
    FOTO_INADEQUADA = "FOTO_INADEQUADA", "Foto inadequada ou de outro lugar"
    OFENSA = "OFENSA", "Ofensa"
    OUTRO = "OUTRO", "Outro motivo"


class TipoAcaoModeracao(models.TextChoices):
    OCULTAR = "OCULTAR", "Ocultar"
    REEXIBIR = "REEXIBIR", "Reexibir"
    REMOVER = "REMOVER", "Remover"
    BLOQUEAR_CONTA = "BLOQUEAR_CONTA", "Bloquear conta"
    DESBLOQUEAR_CONTA = "DESBLOQUEAR_CONTA", "Desbloquear conta"
    EXCLUIR_CONTA = "EXCLUIR_CONTA", "Excluir conta"


class TipoAlvo(models.TextChoices):
    CONTA = "CONTA", "Conta"
    RESTAURANTE = "RESTAURANTE", "Restaurante"
    AVALIACAO_ACESSIBILIDADE = "AVALIACAO_ACESSIBILIDADE", "Avaliação de acessibilidade"
    FOTO = "FOTO", "Foto"
    RESPOSTA_ESTABELECIMENTO = "RESPOSTA_ESTABELECIMENTO", "Resposta do estabelecimento"
    AVALIACAO_ATENDIMENTO = "AVALIACAO_ATENDIMENTO", "Avaliação de atendimento"


# ---------------------------------------------------------------- Conta
class ContaManager(BaseUserManager):
    use_in_migrations = True

    def _criar(self, email, password, **extra):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        conta = self.model(email=self.normalize_email(email), **extra)
        conta.set_password(password)  # RNF07: só o hash é guardado
        conta.save(using=self._db)
        return conta

    def create_user(self, email, password=None, **extra):
        return self._criar(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(papel=Papel.EQUIPE_MOBITE, is_superuser=True)
        return self._criar(email, password, **extra)


class Conta(AbstractUser):
    """Conta de quem avalia, do responsável por restaurante e da equipe.

    senhaHash = password (vazio/inutilizável para quem entra só com Google);
    emailConfirmado vem do allauth; dataCriacao = date_joined.
    Não há ligação com PerfilMobilidade: o perfil fica só no aparelho (LGPD).
    """
    username = None
    first_name = None
    last_name = None
    email = models.EmailField("e-mail", unique=True)
    apelido = models.CharField(max_length=40, blank=True)
    aparecer_publicamente = models.BooleanField(
        "aparecer com apelido e selo", default=False,
        help_text="RN05.2: só aparece em público se a pessoa ativar.")
    papel = models.CharField(max_length=20, choices=Papel.choices, default=Papel.MEMBRO)
    status = models.CharField(max_length=10, choices=StatusConta.choices, default=StatusConta.ATIVA)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = ContaManager()

    class Meta:
        verbose_name = "conta"

    def __str__(self):
        return self.apelido or self.email

    def save(self, *args, **kwargs):
        # papel e status mandam nas permissões do Django
        self.is_staff = self.papel == Papel.EQUIPE_MOBITE
        self.is_active = self.status == StatusConta.ATIVA
        super().save(*args, **kwargs)

    # RN07.3: o papel "Equipe MoBite" dá acesso ao painel (moderação, auditoria, assinaturas e anúncios).
    APPS_DA_EQUIPE = ("core", "account", "socialaccount")

    def _e_equipe(self):
        return self.is_active and self.papel == Papel.EQUIPE_MOBITE

    def has_perm(self, perm, obj=None):
        if self._e_equipe() and perm.split(".")[0] in self.APPS_DA_EQUIPE:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self._e_equipe() and app_label in self.APPS_DA_EQUIPE:
            return True
        return super().has_module_perms(app_label)

    @property
    def email_confirmado(self):
        if self.socialaccount_set.exists():
            return True
        return self.emailaddress_set.filter(email__iexact=self.email, verified=True).exists()

    def total_avaliacoes(self):
        return self.avaliacoes.filter(visivel=True).count()

    def obter_selo(self):
        n = self.total_avaliacoes()
        if n >= 20:
            return Selo.REFERENCIA
        if n >= 5:
            return Selo.COLABORADOR
        return Selo.INICIANTE

    def contar_pessoas_ajudadas(self):
        """RF19: consultas aos lugares que a pessoa avaliou, contadas a partir da 1ª avaliação dela em cada um."""
        total = 0
        primeiras = (self.avaliacoes.filter(visivel=True).values("restaurante")
                     .annotate(primeira=models.Min("data")))
        for p in primeiras:
            total += (ConsultaDiaria.objects.filter(restaurante_id=p["restaurante"],
                                                    data__gte=timezone.localdate(p["primeira"]))
                      .aggregate(t=models.Sum("total"))["t"] or 0)
        return total

    def bloquear(self, motivo, por=None):
        self.status = StatusConta.BLOQUEADA
        self.save()
        AcaoModeracao.registrar(por, TipoAcaoModeracao.BLOQUEAR_CONTA, TipoAlvo.CONTA, self.pk, motivo)

    def desbloquear(self, por=None):
        self.status = StatusConta.ATIVA
        self.save()
        AcaoModeracao.registrar(por, TipoAcaoModeracao.DESBLOQUEAR_CONTA, TipoAlvo.CONTA, self.pk, "")

    def excluir_conta(self, por=None):
        """LGPD, art. 18, VI: dados pessoais eliminados; as avaliações ficam anônimas (on_delete=SET_NULL)."""
        AcaoModeracao.registrar(por, TipoAcaoModeracao.EXCLUIR_CONTA, TipoAlvo.CONTA, self.pk,
                                "Pedido da própria pessoa" if por is None else "")
        self.delete()


# ---------------------------------------------------------------- checklist e perfis
class ItemChecklist(models.Model):
    codigo = models.CharField("código", max_length=4, unique=True)
    nome = models.CharField("nome curto", max_length=40)  # [fora da UML] rótulo da lista
    pergunta = models.CharField(max_length=160)
    ajuda = models.CharField(max_length=160, blank=True)  # [fora da UML] dica de como conferir
    zona = models.CharField(max_length=10, choices=Zona.choices)
    invertida = models.BooleanField(default=False, help_text='Pergunta feita ao contrário ("tem degrau?").')
    ordem = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["ordem"]
        verbose_name = "item do checklist"
        verbose_name_plural = "itens do checklist"

    def __str__(self):
        return f"{self.codigo} {self.nome}"

    def normalizar(self, resposta):
        """Converte a resposta da pergunta para 'o item atende?' (SIM = atende)."""
        if self.invertida and resposta in (Resposta.SIM, Resposta.NAO):
            return Resposta.NAO if resposta == Resposta.SIM else Resposta.SIM
        return resposta


class PerfilMobilidade(models.Model):
    """Os 5 perfis são fixos. O perfil escolhido fica só no aparelho."""
    codigo = models.SlugField("código", max_length=20, unique=True)  # [fora da UML] chave usada no navegador
    nome = models.CharField(max_length=60)
    descricao = models.CharField("descrição", max_length=120)
    ordem = models.PositiveSmallIntegerField(default=0)
    itens = models.ManyToManyField(ItemChecklist, through="PesoItemPerfil", related_name="perfis")

    class Meta:
        ordering = ["ordem"]
        verbose_name = "perfil de mobilidade"
        verbose_name_plural = "perfis de mobilidade"

    def __str__(self):
        return self.nome


class PesoItemPerfil(models.Model):
    """Diz se o item BLOQUEIA ou só IMPORTA para aquele perfil. Usado em calcular_resultados()."""
    perfil = models.ForeignKey(PerfilMobilidade, on_delete=models.CASCADE, related_name="pesos")
    item = models.ForeignKey(ItemChecklist, on_delete=models.CASCADE, related_name="pesos")
    peso = models.CharField(max_length=10, choices=Peso.choices)

    class Meta:
        unique_together = [("perfil", "item")]
        verbose_name = "peso do item no perfil"
        verbose_name_plural = "pesos dos itens nos perfis"


# ---------------------------------------------------------------- Restaurante
class Restaurante(models.Model):
    osm_tipo = models.CharField("tipo no OSM", max_length=1, blank=True, help_text="n, w ou r")  # [fora da UML] node/way/relation
    osm_id = models.BigIntegerField("id no OSM", null=True, blank=True)
    nome = models.CharField(max_length=120)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    telefone = models.CharField(max_length=40, blank=True)
    horario = models.CharField("horário", max_length=200, blank=True)
    data_importacao = models.DateTimeField("importado em", null=True, blank=True)
    visivel = models.BooleanField("visível", default=True)
    demonstracao = models.BooleanField("demonstração", 
        default=False, help_text="Restaurante fictício, criado só para demonstração.")  # [fora da UML]

    class Meta:
        ordering = ["nome"]
        constraints = [models.UniqueConstraint(fields=["osm_tipo", "osm_id"], condition=models.Q(osm_id__isnull=False),
                                               name="restaurante_osm_unico")]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        novo = self.pk is None
        super().save(*args, **kwargs)
        if novo:  # todo restaurante nasce com 10 situações e 5 resultados ("falta informação")
            for item in ItemChecklist.objects.all():
                SituacaoItem.objects.get_or_create(restaurante=self, item=item)
            from .regras import calcular_resultados
            calcular_resultados(self)

    def calcular_resultados(self):
        from .regras import calcular_resultados
        calcular_resultados(self)

    @classmethod
    def publicos(cls):
        """O que o público vê: visível e, com a demonstração desligada no painel, sem os fictícios."""
        qs = cls.objects.filter(visivel=True)
        return qs if ConfiguracaoSite.demonstracao_visivel() else qs.filter(demonstracao=False)

    def publico(self):
        return self.visivel and (not self.demonstracao or ConfiguracaoSite.demonstracao_visivel())

    def editar_dados_basicos(self, telefone, horario):
        self.telefone, self.horario = telefone, horario
        self.save(update_fields=["telefone", "horario"])

    def media_atendimento(self):
        r = self.atendimentos.filter(visivel=True).aggregate(m=models.Avg("estrelas"), n=models.Count("id"))
        return r["m"], r["n"]

    def ocultar(self, motivo, por=None):
        self.visivel = False
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.OCULTAR, TipoAlvo.RESTAURANTE, self.pk, motivo)

    def reexibir(self, por=None):
        self.visivel = True
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.REEXIBIR, TipoAlvo.RESTAURANTE, self.pk, "")

    def assinatura_ativa(self):
        hoje = timezone.localdate()
        return self.assinaturas.filter(status=StatusAssinatura.ATIVA, data_inicio__lte=hoje).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje)).exists()

    def responsaveis(self):
        return Conta.objects.filter(reivindicacoes__restaurante=self, reivindicacoes__status=StatusAnalise.APROVADA)

    def distancia_metros(self, lat, lon):
        return distancia_metros(self.latitude, self.longitude, lat, lon)


def distancia_metros(lat1, lon1, lat2, lon2):
    """Distância em metros pela fórmula de haversine."""
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class SituacaoItem(models.Model):
    """Estado atual de um item num restaurante (10 por restaurante). SIM = o item atende."""
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="situacoes")
    item = models.ForeignKey(ItemChecklist, on_delete=models.CASCADE)
    resposta = models.CharField(max_length=8, choices=Resposta.choices, default=Resposta.NAO_SEI)
    data_ultima_verificacao = models.DateTimeField("última verificação", null=True, blank=True)
    confirmacoes = models.PositiveIntegerField("confirmações", default=0)
    em_duvida = models.BooleanField("em dúvida", default=False,
                                    help_text="Uma resposta isolada contradiz o que 2 ou mais pessoas confirmaram.")

    class Meta:
        unique_together = [("restaurante", "item")]
        ordering = ["item__ordem"]
        verbose_name = "situação do item"
        verbose_name_plural = "situações dos itens"

    def __str__(self):
        return f"{self.restaurante} – {self.item.nome}: {self.get_resposta_display()}"

    def dias_desde_verificacao(self):
        if not self.data_ultima_verificacao:
            return None
        return (timezone.now() - self.data_ultima_verificacao).days

    def esta_verificado(self):
        d = self.dias_desde_verificacao()
        return d is not None and d <= CFG["DIAS_ITEM_DESATUALIZADO"]

    @property
    def tem_informacao(self):
        return self.resposta in (Resposta.SIM, Resposta.NAO)


class ResultadoPerfil(models.Model):
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="resultados")
    perfil = models.ForeignKey(PerfilMobilidade, on_delete=models.CASCADE)
    classificacao = models.CharField("classificação", max_length=24, choices=Classificacao.choices,
                                     default=Classificacao.FALTA_INFORMACAO)
    data_calculo = models.DateTimeField("calculado em", auto_now=True)

    class Meta:
        unique_together = [("restaurante", "perfil")]
        verbose_name = "resultado por perfil"
        verbose_name_plural = "resultados por perfil"


# ---------------------------------------------------------------- contribuições
class AvaliacaoAcessibilidade(models.Model):
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="avaliacoes")
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="avaliacoes")
    data = models.DateTimeField(default=timezone.now)
    visivel = models.BooleanField("visível", default=True)

    class Meta:
        ordering = ["-data"]
        verbose_name = "avaliação de acessibilidade"
        verbose_name_plural = "avaliações de acessibilidade"

    def __str__(self):
        return f"Avaliação de {self.restaurante} ({self.data:%d/%m/%Y})"

    def ocultar(self, motivo="", por=None):
        """Ao ocultar, SituacaoItem e ResultadoPerfil do restaurante são recalculados."""
        self.visivel = False
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.OCULTAR, TipoAlvo.AVALIACAO_ACESSIBILIDADE, self.pk, motivo)
        from .regras import recalcular
        recalcular(self.restaurante)

    def reexibir(self, por=None):
        self.visivel = True
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.REEXIBIR, TipoAlvo.AVALIACAO_ACESSIBILIDADE, self.pk, "")
        from .regras import recalcular
        recalcular(self.restaurante)


class RespostaItem(models.Model):
    """Resposta como a pessoa marcou (para item invertido, SIM = "tem degrau")."""
    avaliacao = models.ForeignKey(AvaliacaoAcessibilidade, verbose_name="avaliação", on_delete=models.CASCADE, related_name="respostas")
    item = models.ForeignKey(ItemChecklist, on_delete=models.CASCADE)
    resposta = models.CharField(max_length=8, choices=Resposta.choices)

    class Meta:
        unique_together = [("avaliacao", "item")]
        ordering = ["item__ordem"]
        verbose_name = "resposta de item"
        verbose_name_plural = "respostas de item"

    @property
    def atende(self):
        return self.item.normalizar(self.resposta)


class FotoEntrada(models.Model):
    """latAtual/lonAtual só são usados na validação e descartados. A localização nunca é salva (LGPD)."""
    avaliacao = models.OneToOneField(AvaliacaoAcessibilidade, verbose_name="avaliação", on_delete=models.CASCADE, related_name="foto")
    arquivo = models.ImageField(upload_to="fotos/%Y/%m/")
    data_envio = models.DateTimeField("enviada em", default=timezone.now)
    proximidade_confirmada = models.BooleanField("tirada no local (até 150 m)", default=False)
    visivel = models.BooleanField("visível", default=True)

    class Meta:
        verbose_name = "foto da entrada"
        verbose_name_plural = "fotos da entrada"

    @staticmethod
    def validar_proximidade(restaurante, lat_atual, lon_atual):
        return restaurante.distancia_metros(lat_atual, lon_atual) <= CFG["RAIO_FOTO_METROS"]

    def ocultar(self, motivo="", por=None):
        self.visivel = False
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.OCULTAR, TipoAlvo.FOTO, self.pk, motivo)

    def reexibir(self, por=None):
        self.visivel = True
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.REEXIBIR, TipoAlvo.FOTO, self.pk, "")


class AvaliacaoAtendimento(models.Model):
    """Estrelas: só atendimento. Bloco e tabela separados da acessibilidade (RN04)."""
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="atendimentos")
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="atendimentos")
    estrelas = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    data = models.DateTimeField(default=timezone.now)
    visivel = models.BooleanField("visível", default=True)

    class Meta:
        verbose_name = "avaliação de atendimento"
        verbose_name_plural = "avaliações de atendimento"

    def remover(self, motivo="", por=None):
        self.visivel = False
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.OCULTAR, TipoAlvo.AVALIACAO_ATENDIMENTO, self.pk, motivo)


class Confirmacao(models.Model):
    """Confirmação com um toque de que o item continua igual (RN03.6)."""
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="confirmacoes")
    situacao = models.ForeignKey(SituacaoItem, verbose_name="situação", on_delete=models.CASCADE, related_name="confirmacoes_feitas")
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "confirmação"
        verbose_name_plural = "confirmações"


class RespostaEstabelecimento(models.Model):
    """Direito de resposta do restaurante com assinatura ativa (RN06.1). Não apaga nem edita a avaliação."""
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="respostas_estabelecimento")
    situacao = models.ForeignKey(SituacaoItem, verbose_name="situação", on_delete=models.CASCADE, related_name="respostas_estabelecimento")
    texto = models.TextField(max_length=500)
    data = models.DateTimeField(default=timezone.now)
    data_edicao = models.DateTimeField("editada em", null=True, blank=True)
    visivel = models.BooleanField("visível", default=True)

    class Meta:
        ordering = ["-data"]
        verbose_name = "resposta do estabelecimento"
        verbose_name_plural = "respostas do estabelecimento"

    def editar(self, novo_texto):
        self.texto, self.data_edicao = novo_texto, timezone.now()
        self.save(update_fields=["texto", "data_edicao"])

    def ocultar(self, motivo="", por=None):
        self.visivel = False
        self.save(update_fields=["visivel"])
        AcaoModeracao.registrar(por, TipoAcaoModeracao.OCULTAR, TipoAlvo.RESPOSTA_ESTABELECIMENTO, self.pk, motivo)

    def remover(self, motivo="", por=None):
        AcaoModeracao.registrar(por, TipoAcaoModeracao.REMOVER, TipoAlvo.RESPOSTA_ESTABELECIMENTO, self.pk, motivo)
        self.delete()


class PreferenciaRestaurante(models.Model):
    """Favoritar ou esconder da própria lista (ideia da Giovanna). Exige conta."""
    conta = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferencias")
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="preferencias")
    tipo = models.CharField(max_length=10, choices=TipoPreferencia.choices)
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("conta", "restaurante")]
        verbose_name = "preferência de restaurante"
        verbose_name_plural = "preferências de restaurante"


# ---------------------------------------------------------------- restaurante como cliente
class Reivindicacao(models.Model):
    conta = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reivindicacoes")
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="reivindicacoes")
    cnpj = models.CharField("CNPJ", max_length=18)
    data_solicitacao = models.DateTimeField("pedido em", default=timezone.now)
    status = models.CharField(max_length=10, choices=StatusAnalise.choices, default=StatusAnalise.PENDENTE)
    verificada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name="reivindicacoes_verificadas")

    class Meta:
        verbose_name = "reivindicação"
        verbose_name_plural = "reivindicações"

    def aprovar(self, por=None):
        self.status, self.verificada_por = StatusAnalise.APROVADA, por
        self.save(update_fields=["status", "verificada_por"])

    def rejeitar(self, por=None):
        self.status, self.verificada_por = StatusAnalise.REJEITADA, por
        self.save(update_fields=["status", "verificada_por"])


class Assinatura(models.Model):
    """Mensalidade que libera a resposta aos itens. No MVP, a equipe ativa manualmente no painel."""
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="assinaturas")
    plano = models.CharField(max_length=40, default="Mensal")
    data_inicio = models.DateField("início", default=timezone.localdate)
    data_fim = models.DateField("fim", null=True, blank=True)
    status = models.CharField(max_length=10, choices=StatusAssinatura.choices, default=StatusAssinatura.ATIVA)
    ativada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="assinaturas_ativadas")

    def ativar(self, por=None, meses=1):
        self.status, self.ativada_por = StatusAssinatura.ATIVA, por
        self.data_inicio = timezone.localdate()
        self.data_fim = self.data_inicio + timedelta(days=30 * meses)
        self.save()

    def cancelar(self):
        self.status = StatusAssinatura.CANCELADA
        self.save(update_fields=["status"])


LINK_EXEMPLO = "https://example.com/"  # link dos anúncios de exemplo criados pelo dados_demo


class Anuncio(models.Model):
    """Anúncio por perfil, escolhido no navegador (RN01.3). Sempre com o rótulo "Publicidade"."""
    titulo = models.CharField("título", max_length=80)
    imagem = models.ImageField(upload_to="anuncios/", blank=True)  # imagemUrl
    link = models.URLField()
    data_inicio = models.DateField("início", default=timezone.localdate)
    data_fim = models.DateField("fim", null=True, blank=True)
    cadastrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name="anuncios")
    restaurante = models.ForeignKey(Restaurante, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="anuncios", help_text="Opcional: restaurante divulgado.")
    perfis = models.ManyToManyField(PerfilMobilidade, blank=True, related_name="anuncios",
                                    help_text="Vazio = aparece para qualquer perfil.")
    cliques = models.PositiveIntegerField(default=0, editable=False)  # [fora da UML] sem ligar à conta (RI08)

    class Meta:
        verbose_name = "anúncio"

    def __str__(self):
        return self.titulo

    @classmethod
    def ativos(cls):
        hoje = timezone.localdate()
        return cls.objects.filter(data_inicio__lte=hoje).filter(
            models.Q(data_fim__isnull=True) | models.Q(data_fim__gte=hoje)).prefetch_related("perfis")


# ---------------------------------------------------------------- equipe
class Auditoria(models.Model):
    """Visita da equipe (MVP Concierge). As respostas atualizam a situação dos itens."""
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="auditorias")
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="auditorias")
    data = models.DateTimeField(default=timezone.now)
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        verbose_name = "auditoria (Concierge)"
        verbose_name_plural = "auditorias (Concierge)"

    def __str__(self):
        return f"Auditoria de {self.restaurante} ({self.data:%d/%m/%Y})"


class RespostaAuditoria(models.Model):  # [fora da UML] guarda o que a equipe viu em cada item
    auditoria = models.ForeignKey(Auditoria, on_delete=models.CASCADE, related_name="respostas")
    item = models.ForeignKey(ItemChecklist, on_delete=models.CASCADE)
    resposta = models.CharField(max_length=8, choices=Resposta.choices)

    class Meta:
        unique_together = [("auditoria", "item")]

    @property
    def atende(self):
        return self.item.normalizar(self.resposta)


class Denuncia(models.Model):
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name="denuncias")
    motivo = models.CharField(max_length=20, choices=MotivoDenuncia.choices)
    descricao = models.TextField("descrição", max_length=500, blank=True)
    data = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=StatusAnalise.choices, default=StatusAnalise.PENDENTE)
    analisada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="denuncias_analisadas")
    avaliacao = models.ForeignKey(AvaliacaoAcessibilidade, verbose_name="avaliação", null=True, blank=True, on_delete=models.CASCADE,
                                  related_name="denuncias")
    foto = models.ForeignKey(FotoEntrada, null=True, blank=True, on_delete=models.CASCADE, related_name="denuncias")
    resposta_estabelecimento = models.ForeignKey(RespostaEstabelecimento, verbose_name="resposta do estabelecimento", null=True, blank=True,
                                                 on_delete=models.CASCADE, related_name="denuncias")

    class Meta:
        ordering = ["status", "-data"]
        verbose_name = "denúncia"

    @property
    def alvo(self):
        return self.avaliacao or self.foto or self.resposta_estabelecimento

    def resolver(self, decisao, por=None):
        """APROVADA oculta o conteúdo denunciado; REJEITADA mantém. As duas ficam no histórico."""
        self.status, self.analisada_por = decisao, por
        self.save(update_fields=["status", "analisada_por"])
        if decisao == StatusAnalise.APROVADA and self.alvo is not None:
            self.alvo.ocultar(f"Denúncia #{self.pk}: {self.get_motivo_display()}", por=por)
            AcaoModeracao.objects.filter(denuncia__isnull=True, executada_por=por).order_by("-pk")[:1].update(
                denuncia=self)


class AcaoModeracao(models.Model):
    """Histórico do que a Equipe MoBite fez e por quê. A equipe oculta ou remove, mas não reescreve textos."""
    executada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="acoes_moderacao")
    denuncia = models.ForeignKey(Denuncia, verbose_name="denúncia", null=True, blank=True, on_delete=models.SET_NULL, related_name="acoes")
    tipo = models.CharField(max_length=20, choices=TipoAcaoModeracao.choices)
    alvo = models.CharField(max_length=30, choices=TipoAlvo.choices)
    id_alvo = models.PositiveIntegerField("id do alvo", )
    motivo = models.CharField(max_length=200, blank=True)
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-data"]
        verbose_name = "ação de moderação"
        verbose_name_plural = "ações de moderação"

    @classmethod
    def registrar(cls, por, tipo, alvo, id_alvo, motivo):
        if por is not None and not getattr(por, "pk", None):
            por = None
        return cls.objects.create(executada_por=por, tipo=tipo, alvo=alvo, id_alvo=id_alvo or 0, motivo=motivo[:200])


class ConsultaDiaria(models.Model):  # [fora da UML] base do "pessoas ajudadas" (RF19), sem saber quem consultou
    restaurante = models.ForeignKey(Restaurante, on_delete=models.CASCADE, related_name="consultas")
    data = models.DateField(default=timezone.localdate)
    total = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("restaurante", "data")]


class ConfiguracaoSite(models.Model):  # [fora da UML] chaves que a equipe liga e desliga no painel (uma linha só)
    mostrar_demonstracao = models.BooleanField(
        "mostrar a demonstração", default=True,
        help_text="Desligado, os restaurantes fictícios somem do app para o público.")
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    alterado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "configuração do app"
        verbose_name_plural = "configuração do app"

    def __str__(self):
        return "Configuração do app"

    @classmethod
    def atual(cls):
        return cls.objects.get_or_create(pk=1)[0]

    @classmethod
    def demonstracao_visivel(cls):
        return not cls.objects.filter(pk=1, mostrar_demonstracao=False).exists()

    def alternar_demonstracao(self, por=None):
        self.mostrar_demonstracao = not self.mostrar_demonstracao
        self.alterado_por = por if getattr(por, "pk", None) else None
        self.alterado_em = timezone.now()
        self.save()
