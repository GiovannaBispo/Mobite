"""Importa nome e localização dos restaurantes de um bairro a partir do OpenStreetMap (RF01).

A consulta roda no PC (o PythonAnywhere gratuito só acessa sites liberados) e fica guardada num arquivo,
que vai junto no zip. No servidor, o script de publicação importa o arquivo.

    # no PC: consulta o mapa (a até 500 m do campus Taguá da FMU), guarda o arquivo e importa
    python manage.py importar_osm --perto=-23.5612,-46.6366,500 --salvar dados/osm-liberdade.json
    # ou por retângulo (sul,oeste,norte,leste)
    python manage.py importar_osm --bbox=-23.5645,-46.6400,-23.5515,-46.6315
    # no servidor (o deploy/pythonanywhere.sh já faz): importa do arquivo, sem consultar o mapa
    python manage.py importar_osm --arquivo dados/osm-liberdade.json --so-novos
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Restaurante

# O servidor principal do Overpass às vezes fica lotado; os outros dois são espelhos públicos.
SERVIDORES = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
              "https://overpass.private.coffee/api/interpreter"]


class Command(BaseCommand):
    help = ("Importa os restaurantes de uma área do OpenStreetMap (Overpass API). Lanchonetes e redes de fast food "
            "(Habib's, Burger King...) também contam; cafés, padarias e bares ficam de fora.")

    def add_arguments(self, parser):
        parser.add_argument("--bbox", help="sul,oeste,norte,leste em graus decimais")
        parser.add_argument("--perto", help="latitude,longitude,metros: só o que fica a até essa distância do ponto")
        parser.add_argument("--arquivo", help="Importa de um arquivo guardado com --salvar, sem consultar o mapa")
        parser.add_argument("--salvar", help="Guarda o que veio do mapa neste arquivo (para importar no servidor)")
        parser.add_argument("--endpoint", help="Servidor Overpass (o padrão tenta três)")
        parser.add_argument("--so-novos", action="store_true",
                            help="Só cria os que faltam; não mexe nos que já existem (usado na publicação)")
        parser.add_argument("--simular", action="store_true", help="Só mostra o que seria importado")

    @staticmethod
    def area(bbox, perto):
        if perto:
            try:
                lat, lon, metros = (float(x) for x in perto.split(","))
            except ValueError:
                raise CommandError("Use --perto=latitude,longitude,metros (ex.: -23.5612,-46.6366,500).")
            return f"(around:{metros:.0f},{lat},{lon})"
        try:
            s, w, n, e = (float(x) for x in bbox.split(","))
        except ValueError:
            raise CommandError("Use --bbox=sul,oeste,norte,leste (ex.: -23.5645,-46.64,-23.5515,-46.6315).")
        if not (s < n and w < e):
            raise CommandError("O retângulo está invertido: sul < norte e oeste < leste.")
        return f"({s},{w},{n},{e})"

    def consultar(self, area, endpoint):
        consulta = f"""[out:json][timeout:90];
nwr["amenity"~"^(restaurant|fast_food)$"]["name"]{area};
out center tags;"""
        corpo = urllib.parse.urlencode({"data": consulta}).encode()
        erros = []
        for url in [endpoint] if endpoint else SERVIDORES:
            self.stdout.write(f"Consultando o OpenStreetMap ({urllib.parse.urlparse(url).netloc})...")
            pedido = urllib.request.Request(url, data=corpo, headers={"User-Agent": "importar-osm/1.0"})
            try:
                with urllib.request.urlopen(pedido, timeout=150) as resp:
                    return json.load(resp)["elements"]
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as erro:
                erros.append(f"{url}: {erro}")
                self.stdout.write(self.style.WARNING(f"  não respondeu ({erro}), tentando o próximo"))
        raise CommandError("Nenhum servidor do OpenStreetMap respondeu. Tente de novo mais tarde.\n" + "\n".join(erros))

    def handle(self, *args, bbox, perto, arquivo, salvar, endpoint, so_novos, simular, **kwargs):
        if arquivo:
            try:
                guardado = json.loads(Path(arquivo).read_text(encoding="utf-8"))
            except (OSError, ValueError) as erro:
                raise CommandError(f"Não consegui ler {arquivo}: {erro}")
            elementos = guardado["elementos"]
            self.stdout.write(f"Lendo {arquivo} (consulta de {guardado.get('consultado_em', '?')}).")
        elif bbox or perto:
            elementos = self.consultar(self.area(bbox, perto), endpoint)
            if salvar:
                # "retirados": lugares que a equipe tirou do arquivo à mão (ex.: refeitório de empresa).
                # Continuam de fora quando o mapa é consultado de novo.
                try:
                    retirados = json.loads(Path(salvar).read_text(encoding="utf-8")).get("retirados", [])
                except (OSError, ValueError):
                    retirados = []
                fora = {(r["type"], r["id"]) for r in retirados}
                elementos = [el for el in elementos if (el["type"], el["id"]) not in fora]
                Path(salvar).parent.mkdir(parents=True, exist_ok=True)
                Path(salvar).write_text(json.dumps({
                    "fonte": "© colaboradores do OpenStreetMap (ODbL), https://www.openstreetmap.org/copyright",
                    "area": f"perto={perto}" if perto else f"bbox={bbox}",
                    "consultado_em": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
                    "elementos": elementos, "retirados": retirados}, ensure_ascii=False, indent=1), encoding="utf-8")
                self.stdout.write(f"Guardado em {salvar}.")
        else:
            raise CommandError("Informe --perto ou --bbox (consulta o mapa) ou --arquivo (importa um arquivo guardado).")

        novos = atualizados = mantidos = 0
        agora = timezone.now()
        for el in elementos:
            tags = el.get("tags", {})
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat is None or lon is None or not tags.get("name"):
                continue
            rua = tags.get("addr:street", "")
            endereco = f"{rua}, {tags['addr:housenumber']}" if rua and tags.get("addr:housenumber") else rua
            dados = {
                "nome": tags["name"][:120],
                "endereco": endereco[:200], "latitude": lat, "longitude": lon,
                "telefone": (tags.get("phone") or tags.get("contact:phone") or "")[:40],
                "horario": tags.get("opening_hours", "")[:200], "data_importacao": agora,
            }
            if simular:
                self.stdout.write(f"  {dados['nome']} – {endereco or 'sem endereço no mapa'}")
                continue
            r = Restaurante.objects.filter(osm_tipo=el["type"][0], osm_id=el["id"]).first()
            if r and so_novos:
                mantidos += 1
            elif r:
                for campo in ("nome", "latitude", "longitude", "data_importacao"):
                    setattr(r, campo, dados[campo])
                # endereço, telefone e horário podem ter sido preenchidos pela equipe ou pelo restaurante:
                # o mapa só preenche o que estiver vazio
                r.endereco = r.endereco or dados["endereco"]
                r.telefone = r.telefone or dados["telefone"]
                r.horario = r.horario or dados["horario"]
                r.save()
                atualizados += 1
            else:
                Restaurante.objects.create(osm_tipo=el["type"][0], osm_id=el["id"], **dados)
                novos += 1
        if simular:
            self.stdout.write(self.style.SUCCESS(f"{len(elementos)} restaurantes encontrados (simulação, nada foi salvo)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{len(elementos)} restaurantes no mapa: {novos} novos, "
                                                 f"{atualizados} atualizados, {mantidos} já existiam."))
        self.stdout.write("Dados © colaboradores do OpenStreetMap (ODbL): a atribuição já aparece no rodapé e nos mapas.")
