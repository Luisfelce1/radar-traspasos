"""Normalización: precios, provincias, sectores y tipo de operación."""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- utilidades


def fold(s: str) -> str:
    """minúsculas, sin tildes, solo letras/números/espacios."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def slugify(s: str, max_len: int = 70) -> str:
    return fold(s).replace(" ", "-")[:max_len].strip("-")


# ---------------------------------------------------------------- precios

_NUM = r"\d{1,3}(?:[.\s]\d{3})+|\d+(?:,\d+)?"


def _to_number(tok: str, suffix: str = "") -> float | None:
    tok = tok.strip()
    if re.fullmatch(r"\d{1,3}(?:[.\s]\d{3})+", tok):
        val = float(re.sub(r"[.\s]", "", tok))
    else:
        try:
            val = float(tok.replace(",", "."))
        except ValueError:
            return None
    suffix = suffix.lower()
    if suffix in ("k", "mil"):
        val *= 1_000
    elif suffix in ("m", "mm", "millones", "millón", "millon"):
        val *= 1_000_000
    return val


def parse_money(text: str | None, minimum: float = 1_000) -> tuple[int | None, int | None]:
    """'€ 250.000 - € 500.000' -> (250000, 500000). 'Confidencial' -> (None, None).
    Valores por debajo de `minimum` se descartan (suelen ser errores o miles abreviados)."""
    if not text:
        return None, None
    t = text.lower()
    if any(w in t for w in ("confiden", "consultar", "a convenir", "negociable")) and not re.search(r"\d", t):
        return None, None
    vals = []
    for m in re.finditer(rf"({_NUM})\s*(k|mil|millones|millón|millon|mm|m)?\b", t):
        v = _to_number(m.group(1), m.group(2) or "")
        if v is not None and v >= minimum:
            vals.append(int(v))
    if not vals:
        return None, None
    return min(vals), max(vals)


# ---------------------------------------------------------------- provincias

# slug, nombre, comunidad, [variantes]
PROVINCIAS = [
    ("a-coruna", "A Coruña", "galicia", ["a coruna", "coruna", "coruna a", "la coruna"]),
    ("alava", "Álava", "pais-vasco", ["alava", "araba", "araba alava", "vitoria"]),
    ("albacete", "Albacete", "castilla-la-mancha", []),
    ("alicante", "Alicante", "comunidad-valenciana", ["alicante alacant", "alacant", "benidorm", "elche"]),
    ("almeria", "Almería", "andalucia", []),
    ("asturias", "Asturias", "asturias", ["oviedo", "gijon"]),
    ("avila", "Ávila", "castilla-y-leon", []),
    ("badajoz", "Badajoz", "extremadura", []),
    ("baleares", "Illes Balears", "baleares", ["illes balears", "balears illes", "baleares", "islas baleares",
                                              "mallorca", "palma de mallorca", "ibiza", "menorca"]),
    ("barcelona", "Barcelona", "cataluna", ["badalona", "hospitalet de llobregat", "sabadell", "terrassa"]),
    ("bizkaia", "Bizkaia", "pais-vasco", ["vizcaya", "bilbao"]),
    ("burgos", "Burgos", "castilla-y-leon", []),
    ("caceres", "Cáceres", "extremadura", []),
    ("cadiz", "Cádiz", "andalucia", ["jerez", "algeciras"]),
    ("cantabria", "Cantabria", "cantabria", ["santander"]),
    ("castellon", "Castellón", "comunidad-valenciana", ["castellon castello", "castello"]),
    ("ceuta", "Ceuta", "ceuta", []),
    ("ciudad-real", "Ciudad Real", "castilla-la-mancha", []),
    ("cordoba", "Córdoba", "andalucia", []),
    ("cuenca", "Cuenca", "castilla-la-mancha", []),
    ("gipuzkoa", "Gipuzkoa", "pais-vasco", ["guipuzcoa", "san sebastian", "donostia"]),
    ("girona", "Girona", "cataluna", ["gerona"]),
    ("granada", "Granada", "andalucia", []),
    ("guadalajara", "Guadalajara", "castilla-la-mancha", []),
    ("huelva", "Huelva", "andalucia", []),
    ("huesca", "Huesca", "aragon", []),
    ("jaen", "Jaén", "andalucia", []),
    ("la-rioja", "La Rioja", "la-rioja", ["rioja la", "rioja", "logrono"]),
    ("las-palmas", "Las Palmas", "canarias", ["palmas las", "gran canaria", "lanzarote", "fuerteventura",
                                             "las palmas de gran canaria"]),
    ("leon", "León", "castilla-y-leon", ["ponferrada"]),
    ("lleida", "Lleida", "cataluna", ["lerida"]),
    ("lugo", "Lugo", "galicia", []),
    ("madrid", "Madrid", "madrid", ["comunidad de madrid"]),
    ("malaga", "Málaga", "andalucia", ["marbella"]),
    ("melilla", "Melilla", "melilla", []),
    ("murcia", "Murcia", "murcia", ["region de murcia", "cartagena"]),
    ("navarra", "Navarra", "navarra", ["pamplona"]),
    ("ourense", "Ourense", "galicia", ["orense"]),
    ("palencia", "Palencia", "castilla-y-leon", []),
    ("pontevedra", "Pontevedra", "galicia", ["vigo"]),
    ("salamanca", "Salamanca", "castilla-y-leon", []),
    ("santa-cruz-de-tenerife", "Santa Cruz de Tenerife", "canarias", ["tenerife", "la palma", "la gomera"]),
    ("segovia", "Segovia", "castilla-y-leon", []),
    ("sevilla", "Sevilla", "andalucia", []),
    ("soria", "Soria", "castilla-y-leon", []),
    ("tarragona", "Tarragona", "cataluna", ["reus"]),
    ("teruel", "Teruel", "aragon", []),
    ("toledo", "Toledo", "castilla-la-mancha", []),
    ("valencia", "Valencia", "comunidad-valenciana", ["valencia valencia", "gandia"]),
    ("valladolid", "Valladolid", "castilla-y-leon", []),
    ("zamora", "Zamora", "castilla-y-leon", []),
    ("zaragoza", "Zaragoza", "aragon", []),
]

COMUNIDADES = {
    "andalucia": "Andalucía", "aragon": "Aragón", "asturias": "Asturias", "baleares": "Illes Balears",
    "canarias": "Canarias", "cantabria": "Cantabria", "castilla-la-mancha": "Castilla-La Mancha",
    "castilla-y-leon": "Castilla y León", "cataluna": "Cataluña", "ceuta": "Ceuta",
    "comunidad-valenciana": "Comunidad Valenciana", "extremadura": "Extremadura", "galicia": "Galicia",
    "la-rioja": "La Rioja", "madrid": "Madrid", "melilla": "Melilla", "murcia": "Murcia",
    "navarra": "Navarra", "pais-vasco": "País Vasco",
}
_COMUNIDAD_ALIASES = {fold(v): k for k, v in COMUNIDADES.items()} | {
    "comunidad de madrid": "madrid", "region de murcia": "murcia", "principado de asturias": "asturias",
    "comunidad foral de navarra": "navarra", "illes balears": "baleares", "islas baleares": "baleares",
    "comunitat valenciana": "comunidad-valenciana", "castilla y leon": "castilla-y-leon",
    "catalunya": "cataluna", "valencia comunidad": "comunidad-valenciana", "pais vasco euskadi": "pais-vasco",
    "euskadi": "pais-vasco", "castilla la mancha": "castilla-la-mancha", "comunitat valenciana": "comunidad-valenciana",
}

PROV_BY_SLUG = {p[0]: {"slug": p[0], "nombre": p[1], "comunidad": p[2]} for p in PROVINCIAS}
_PROV_ALIASES: dict[str, str] = {}
for slug, nombre, _, variantes in PROVINCIAS:
    for v in [nombre, slug.replace("-", " "), *variantes]:
        _PROV_ALIASES[fold(v)] = slug
        _PROV_ALIASES[fold(v).replace(" ", "")] = slug  # 'valenciavalencia', 'palmaslas'


def match_provincia(text: str | None) -> str | None:
    """Coincidencia exacta de un texto corto ('Madrid', 'valenciavalencia', 'Coruña, A')."""
    if not text:
        return None
    f = fold(text)
    return _PROV_ALIASES.get(f) or _PROV_ALIASES.get(f.replace(" ", ""))


def find_provincia_in(text: str | None) -> str | None:
    """Busca ' en <provincia>' dentro de un texto largo (título)."""
    if not text:
        return None
    f = f" {fold(text)} "
    best = None
    for alias, slug in _PROV_ALIASES.items():
        if " " not in alias and len(alias) < 4:
            continue
        pos = f.rfind(f" en {alias} ")
        if pos >= 0 and (best is None or pos > best[0] or (pos == best[0] and len(alias) > best[2])):
            best = (pos, slug, len(alias))
    return best[1] if best else None


def match_comunidad(text: str | None) -> str | None:
    return _COMUNIDAD_ALIASES.get(fold(text or "")) if text else None


FOREIGN_HINTS = {"belgica", "francia", "portugal", "alemania", "italia", "mexico", "argentina", "costa rica",
                 "republica dominicana", "paises bajos", "reino unido", "andorra", "panama", "estados unidos"}


def is_foreign(region: str | None) -> bool:
    return fold(region or "") in FOREIGN_HINTS


# ---------------------------------------------------------------- sectores

# Orden = prioridad. Primera coincidencia gana.
SECTORES = [
    ("online", "Negocio online", ["tienda online", "ecommerce", "e commerce", "negocio online", "amazon",
                                  "saas", "marketplace", "comercio electronico", "sitio web", "pagina web", "negocio digital", "app "]),
    ("hosteleria", "Hostelería", ["bar ", "bares", "restaurante", "cafeteria", "pizzeria", "hamburgueseria",
                                  "taperia", "cerveceria", "pub ", "discoteca", "catering", "heladeria", "churreria",
                                  "bocateria", "gastro", "vinoteca", "cocteleria", "kebab", "brunch", "asador",
                                  "hosteleria", "food truck", "marisqueria", "vermuteria"]),
    ("alojamiento", "Hoteles y alojamiento", ["hotel", "hostal", "albergue", "casa rural", "casas rurales",
                                              "apartamentos turisticos", "pension", "camping", "glamping",
                                              "apartahotel", "alquiler vacacional", "hostel", "posada"]),
    ("estetica", "Estética y peluquería", ["peluqueria", "estetica", "barberia", "manicura", "pedicura",
                                          "belleza", "spa ", "masaje", "depilacion", "bronceado"]),
    ("salud", "Salud y bienestar", ["clinica", "dental", "fisioterapia", "centro medico", "medico",
                                    "veterinari", "optica", "farmacia", "podolog", "psicolog", "residencia",
                                    "geriatric", "centro de dia", "audiolog", "policlinica", "parafarmacia"]),
    ("alimentacion", "Alimentación", ["carniceria", "panaderia", "pasteleria", "fruteria", "pescaderia",
                                      "supermercado", "alimentacion", "charcuteria", "obrador", "gourmet",
                                      "minimarket", "polleria", "herbolario", "dietetica", "reposteria"]),
    ("educacion", "Educación y formación", ["academia", "escuela", "guarderia", "formacion", "idiomas",
                                           "autoescuela", "centro educativo", "ludoteca", "escuela infantil"]),
    ("deporte-ocio", "Deporte y ocio", ["gimnasio", "pilates", "fitness", "yoga", "padel", "escape room",
                                        "ocio", "bolera", "karting", "crossfit", "deportiv", "recreativos",
                                        "parque infantil", "parque de aventura"]),
    ("comercio", "Comercio", ["tienda", "boutique", "ferreteria", "papeleria", "libreria", "joyeria", "moda",
                              "ropa", "zapateria", "calzado", "merceria", "floristeria", "jugueteria",
                              "perfumeria", "regalos", "estanco", "loterias", "kiosco", "quiosco", "bazar",
                              "colchoneria", "muebles", "decoracion", "telefonia", "comercio"]),
    ("transporte", "Transporte y logística", ["transporte", "logistica", "mensajeria", "paqueteria", "vtc",
                                              "taxi", "reparto", "mudanzas", "flota"]),
    ("servicios", "Servicios", ["asesoria", "gestoria", "agencia", "inmobiliaria", "limpieza", "lavanderia",
                                "tintoreria", "reformas", "taller", "seguros", "consultora", "imprenta",
                                "rotulacion", "copisteria", "cerrajeria", "funeraria", "eventos",
                                "administracion de fincas", "servicio tecnico", "vending"]),
    ("industria", "Industria y construcción", ["fabrica", "industria", "fabricacion", "produccion",
                                               "metalica", "carpinteria", "construccion", "mecanizado",
                                               "maquinaria", "bodega", "envasad", "constructora"]),
]
SECTOR_NAMES = {s[0]: s[1] for s in SECTORES} | {"otros": "Otros negocios"}


def detect_sector(*texts: str | None) -> str:
    """Busca en cada texto por orden (primero el sector del portal, luego el título)."""
    folded = [f" {fold(t or '')} " for t in texts if t and t.strip()]
    # 'online' manda sobre la categoría del portal ('Comercio' + 'tienda online' => online)
    if any(f" {kw}" in f for f in folded for kw in SECTORES[0][2]):
        return "online"
    for f in folded:
        for slug, _, kws in SECTORES[1:]:
            if any(f" {kw}" in f for kw in kws):
                return slug
    return "otros"


# ---------------------------------------------------------------- tipo de operación

_BUSQUEDA = ["busco", "buscamos", "compro ", "compramos", "socio", "inversor", "invertir", "inversion para",
             "financiacion", "prestamo", "se busca", "convocatoria"]
_INMUEBLE = ["suelo urbano", "solar ", "chalet", "edificio residencial", "terreno", "casa o chalet",
             "local en alquiler", "arrendamiento de local", "nave con terreno"]


def detect_tipo(title: str, url: str = "") -> str:
    t = f" {fold(title)} {fold(url.rsplit('/', 1)[-1])} "
    if any(f" {w}" in t for w in _BUSQUEDA):
        return "busqueda"
    if any(f" {w}" in t for w in _INMUEBLE):
        return "inmueble"
    if "traspas" in t or "trapaso" in t or "traspado" in t:
        return "traspaso"
    if "alquil" in t or "arrend" in t:
        return "alquiler"
    return "venta"


TIPO_NAMES = {"traspaso": "Traspaso", "venta": "Venta", "alquiler": "Alquiler"}
