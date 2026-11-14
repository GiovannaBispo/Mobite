import re

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .fotos import tratar_foto
from .models import (Conta, FotoEntrada, ItemChecklist, MotivoDenuncia, Reivindicacao, Resposta,
                     RespostaEstabelecimento, Restaurante)

CFG = settings.MOBITE


class AvaliacaoForm(forms.Form):
    """Até 5 perguntas (sim, não ou não sei), foto opcional e estrelas de atendimento opcionais.

    A latitude e a longitude chegam só para conferir os 150 m da foto e não são guardadas (RN03.4).
    """
    foto = forms.FileField(required=False, label="Foto da entrada (opcional)")
    lat = forms.FloatField(required=False, min_value=-90, max_value=90, widget=forms.HiddenInput)
    lon = forms.FloatField(required=False, min_value=-180, max_value=180, widget=forms.HiddenInput)
    estrelas = forms.TypedChoiceField(required=False, coerce=int, empty_value=0,
                                      choices=[(n, n) for n in range(0, 6)])

    def __init__(self, *args, restaurante, **kwargs):
        super().__init__(*args, **kwargs)
        self.restaurante = restaurante
        self.itens = list(ItemChecklist.objects.all())
        for item in self.itens:
            self.fields[f"r_{item.codigo}"] = forms.ChoiceField(
                required=False, choices=[("", "Pular")] + list(Resposta.choices), label=item.pergunta)
        self.foto_tratada = None
        self.distancia = None

    def respostas(self):
        return {i: self.cleaned_data[f"r_{i.codigo}"] for i in self.itens if self.cleaned_data.get(f"r_{i.codigo}")}

    def clean(self):
        dados = super().clean()
        respostas = self.respostas()
        if len(respostas) > CFG["MAX_PERGUNTAS"]:
            raise ValidationError(f"Responda no máximo {CFG['MAX_PERGUNTAS']} perguntas por avaliação.")
        foto = dados.get("foto")
        if not respostas and not foto and not dados.get("estrelas"):
            raise ValidationError("Responda pelo menos uma pergunta ou avalie o atendimento.")
        if foto:
            if not respostas:
                self.add_error("foto", "Responda pelo menos uma pergunta para mandar a foto.")
            elif dados.get("lat") is None or dados.get("lon") is None:
                self.add_error("foto", "Permita a localização para mandar a foto.")
            else:
                self.distancia = self.restaurante.distancia_metros(dados["lat"], dados["lon"])
                if not FotoEntrada.validar_proximidade(self.restaurante, dados["lat"], dados["lon"]):
                    longe = (f"{self.distancia / 1000:.1f} km".replace(".", ",") if self.distancia >= 1000
                             else f"{self.distancia:.0f} m")
                    self.add_error("foto", f"Você está a {longe} do restaurante. A foto só vale tirada lá "
                                           f"(até {CFG['RAIO_FOTO_METROS']} m). Dá para enviar a avaliação sem ela.")
                else:
                    try:
                        self.foto_tratada = tratar_foto(foto)
                    except ValidationError as e:
                        self.add_error("foto", e)
        # As coordenadas não seguem adiante: a view só recebe se a proximidade foi confirmada.
        dados.pop("lat", None)
        dados.pop("lon", None)
        return dados


class ContaForm(forms.ModelForm):
    class Meta:
        model = Conta
        fields = ["apelido", "aparecer_publicamente"]
        labels = {"apelido": "Apelido (opcional)",
                  "aparecer_publicamente": "Mostrar meu apelido nas avaliações"}
        help_texts = {"apelido": "Se não marcar a opção abaixo, você aparece como anônimo."}

    def clean(self):
        dados = super().clean()
        if dados.get("aparecer_publicamente") and not dados.get("apelido", "").strip():
            self.add_error("apelido", "Escolha um apelido primeiro.")
        return dados


def cnpj_valido(cnpj):
    n = re.sub(r"\D", "", cnpj)
    if len(n) != 14 or n == n[0] * 14:
        return False
    for tam in (12, 13):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if tam == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(d) * p for d, p in zip(n[:tam], pesos))
        dig = 11 - soma % 11
        if (0 if dig >= 10 else dig) != int(n[tam]):
            return False
    return True


class ReivindicacaoForm(forms.ModelForm):
    class Meta:
        model = Reivindicacao
        fields = ["cnpj"]
        widgets = {"cnpj": forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "00.000.000/0000-00",
                                                  "autocomplete": "off"})}

    def clean_cnpj(self):
        cnpj = self.cleaned_data["cnpj"]
        if not cnpj_valido(cnpj):
            raise ValidationError("Esse CNPJ não é válido. Confira os números.")
        n = re.sub(r"\D", "", cnpj)
        return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


class RespostaEstabelecimentoForm(forms.ModelForm):
    class Meta:
        model = RespostaEstabelecimento
        fields = ["texto"]
        labels = {"texto": "Resposta do restaurante"}
        widgets = {"texto": forms.Textarea(attrs={"rows": 4, "maxlength": 500})}


class DadosBasicosForm(forms.ModelForm):
    class Meta:
        model = Restaurante
        fields = ["telefone", "horario"]
        labels = {"telefone": "Telefone", "horario": "Horário de funcionamento"}


class DenunciaForm(forms.Form):
    motivo = forms.ChoiceField(choices=MotivoDenuncia.choices, widget=forms.RadioSelect, label="O que há de errado?")
    descricao = forms.CharField(required=False, max_length=500, label="Conte mais (opcional)",
                                widget=forms.Textarea(attrs={"rows": 3, "maxlength": 500}))
