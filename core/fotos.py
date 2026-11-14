"""Tratamento da foto da entrada (RN03.5 / RNF05).

A foto é girada para a posição certa, reduzida e salva de novo em JPEG sem nenhum
metadado (EXIF): some a data, o modelo do celular e a localização embutida no arquivo.
"""
import io
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

LADO = settings.MOBITE["FOTO_LADO_MAXIMO"]
MAX_MB = settings.MOBITE["FOTO_TAMANHO_MAXIMO_MB"]


def tratar_foto(arquivo):
    """Recebe o arquivo enviado e devolve um ContentFile JPEG limpo, pronto para salvar."""
    if arquivo.size > MAX_MB * 1024 * 1024:
        raise ValidationError(f"A foto passa de {MAX_MB} MB. Tente uma foto menor.")
    try:
        img = Image.open(arquivo)
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Não conseguimos abrir esse arquivo como foto. Envie JPG, PNG ou HEIC convertido.")
    img = ImageOps.exif_transpose(img)  # usa a orientação do EXIF antes de apagá-lo
    img = img.convert("RGB")
    img.thumbnail((LADO, LADO), Image.LANCZOS)
    limpa = Image.new("RGB", img.size)  # imagem nova: nenhum metadado é copiado
    limpa.paste(img)
    saida = io.BytesIO()
    limpa.save(saida, "JPEG", quality=82, optimize=True, progressive=True)
    return ContentFile(saida.getvalue(), name=f"{uuid.uuid4().hex}.jpg")
