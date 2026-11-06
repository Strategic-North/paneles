"""Genera los paneles de noticias por estado a partir de feeds RSS/Atom.

Uso: python generar.py [carpeta_config] [carpeta_salida]
Por omisión lee config/*.json y escribe en docs/ (lo que publica GitHub Pages).
Solo usa la biblioteca estándar de Python.
"""
import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

CDMX = timezone(timedelta(hours=-6))  # CDMX no tiene horario de verano desde 2022
HORA_CORTE = 20
DIAS_RECIENTES = 3  # cuántos días hacia atrás se aceptan notas nuevas
# Casi la mitad de los medios rechaza el User-Agent de Python: se usa uno de navegador.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
         "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12}
GNEWS = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=MX&ceid=MX:es-419"

RAIZ = Path(__file__).resolve().parent
CONFIG = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "config"
SALIDA = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "docs"


def sin_acentos(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def limpiar(texto):
    texto = re.sub(r"<[^>]+>", " ", html.unescape(texto or ""))
    return re.sub(r"\s+", " ", texto).strip()


def leer_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def fecha(texto):
    if not texto:
        return None
    texto = texto.strip()
    try:
        d = parsedate_to_datetime(texto)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            d = fecha_en_espanol(texto)
            if d is None:
                return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=CDMX)
    return d.astimezone(CDMX)


def fecha_en_espanol(texto):
    """Fechas como 'LUN, 02 NOV 2026 14:05:00 -0600' (El Porvenir)."""
    m = re.search(r"(\d{1,2})\s+([a-zA-Z]{3})[a-zA-Z]*\.?\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", texto)
    if not m or sin_acentos(m.group(2))[:3] not in MESES:
        return None
    dia, mes, anio = int(m.group(1)), MESES[sin_acentos(m.group(2))[:3]], int(m.group(3))
    hora, minuto = int(m.group(4) or 0), int(m.group(5) or 0)
    zona = re.search(r"([+-])(\d{2}):?(\d{2})\s*$", texto)
    tz = CDMX
    if zona:
        signo = 1 if zona.group(1) == "+" else -1
        tz = timezone(signo * timedelta(hours=int(zona.group(2)), minutes=int(zona.group(3))))
    return datetime(anio, mes, dia, hora, minuto, tzinfo=tz)


def hijo(nodo, *nombres):
    for n in nombres:
        for e in nodo.iter():
            if e.tag.split("}")[-1] == n and e is not nodo:
                return e
    return None


def xml_tolerante(xml):
    """Algunos feeds usan prefijos sin declarar (media:, dc:); se quitan y se vuelve a intentar."""
    try:
        return ET.fromstring(xml)
    except ET.ParseError:
        xml = re.sub(rb"<(/?)[A-Za-z0-9_]+:([A-Za-z])", rb"<\1\2", xml)
        xml = re.sub(rb"\s[A-Za-z0-9_]+:([A-Za-z0-9_]+)=", rb" \1=", xml)
        try:
            return ET.fromstring(xml)
        except ET.ParseError:
            # Último recurso: se rescatan las notas que sí estén bien formadas.
            raiz = ET.Element("rescate")
            for m in re.finditer(rb"<(item|entry|url)[\s>].*?</\1>", xml, re.S):
                try:
                    raiz.append(ET.fromstring(m.group(0)))
                except ET.ParseError:
                    continue
            if not len(raiz):
                raise
            return raiz


def parsear(xml, medio_fijo, ahora):
    raiz = xml_tolerante(xml)
    entradas = [e for e in raiz.iter() if e.tag.split("}")[-1] in ("item", "entry")]
    notas = []
    for e in entradas:
        titulo = limpiar((hijo(e, "title").text if hijo(e, "title") is not None else ""))
        nodo_liga = hijo(e, "link")
        liga = ""
        if nodo_liga is not None:
            liga = (nodo_liga.text or nodo_liga.get("href") or "").strip()
        nodo_fecha = hijo(e, "pubDate", "published", "updated", "date")
        cuando = fecha(nodo_fecha.text if nodo_fecha is not None else None)
        nodo_desc = hijo(e, "description", "summary")
        resumen = limpiar(nodo_desc.text if nodo_desc is not None else "")[:280]
        medio = medio_fijo
        nodo_fuente = hijo(e, "source")
        fuente = (nodo_fuente.text or "").strip() if nodo_fuente is not None else ""
        if not medio and fuente:
            medio = fuente
        for sufijo in {fuente, medio or ""} - {""}:  # Google News agrega " - Medio" al titular
            if titulo.lower().endswith(" - " + sufijo.lower()):
                titulo = titulo[: -len(" - " + sufijo)]
        if not titulo or not liga:
            continue
        notas.append({
            "titulo": titulo,
            "liga": liga,
            "medio": medio or "Sin medio",
            "publicada": cuando.isoformat() if cuando else None,
            "hora_aproximada": cuando is None,
            "visto": ahora.isoformat(),
            "resumen": resumen,
        })
    return notas


def parsear_sitemap(xml, medio, ahora, filtro_url=None):
    """Sitemap de noticias de Google (<url><loc> + <news:title> + <news:publication_date>)."""
    notas = []
    for u in xml_tolerante(xml).iter():
        if u.tag.split("}")[-1] != "url":
            continue
        loc, titulo, cuando = hijo(u, "loc"), hijo(u, "title"), hijo(u, "publication_date", "lastmod")
        liga = (loc.text or "").strip() if loc is not None else ""
        if not liga or (filtro_url and filtro_url not in liga):
            continue
        titulo = limpiar(titulo.text) if titulo is not None else ""
        if not titulo:
            continue
        d = fecha(cuando.text if cuando is not None else None)
        notas.append({"titulo": titulo, "liga": liga, "medio": medio,
                      "publicada": d.isoformat() if d else None, "hora_aproximada": d is None,
                      "visto": ahora.isoformat(), "resumen": ""})
    return notas


def parsear_wordpress(datos, medio, ahora):
    """API de WordPress (/wp-json/wp/v2/posts), para medios con el RSS roto."""
    notas = []
    for p in json.loads(datos):
        d = fecha((p.get("date_gmt") or "") + "+00:00") if p.get("date_gmt") else None
        notas.append({"titulo": limpiar(p.get("title", {}).get("rendered", "")), "liga": p.get("link", ""),
                      "medio": medio, "publicada": d.isoformat() if d else None,
                      "hora_aproximada": d is None, "visto": ahora.isoformat(), "resumen": ""})
    return [n for n in notas if n["titulo"] and n["liga"]]


def clave(nota):
    base = sin_acentos(re.sub(r"[^\w ]", "", nota["titulo"]))[:120]
    return hashlib.sha1(base.encode()).hexdigest()[:16]


def aparece(palabra, texto):
    """Las palabras de 4 letras o menos (PRI, PAN, INE) van completas; las largas valen como raíz."""
    p = re.escape(sin_acentos(palabra))
    return re.search(r"\b" + p + (r"\b" if len(palabra) <= 4 else ""), texto) is not None


def secciones(liga):
    """Partes de la ruta de la liga: muchos medios ponen la sección (/seguridad/, /deportes/)."""
    ruta = urllib.parse.urlparse(liga).path
    return {sin_acentos(p) for p in re.split(r"[/_.]", ruta) if p and not p.isdigit()}


def temas_de(nota, cfg):
    texto = sin_acentos(nota["titulo"] + " " + nota["resumen"])
    temas = [t for t, palabras in cfg.get("temas", {}).items() if any(aparece(p, texto) for p in palabras)]
    partes = secciones(nota["liga"])
    de_seccion = {tema for seccion, tema in cfg.get("secciones", {}).items() if seccion in partes}
    if "Deportes y espectáculos" in de_seccion:
        return ["Deportes y espectáculos"]  # la sección del medio manda sobre palabras sueltas
    return (temas + sorted(t for t in de_seccion if t not in temas)) or ["Otros"]


def etiquetar(nota, cfg):
    nota["temas"] = temas_de(nota, cfg)
    texto = sin_acentos(nota["titulo"] + " " + nota["resumen"])
    partes = secciones(nota["liga"])
    lugares = [sin_acentos(l) for l in cfg.get("lugares", [])]
    menciona = any(l in texto for l in lugares)
    fuera = bool(partes & set(cfg.get("secciones_no_locales", [])))
    nota["local"] = menciona or (nota.get("local_fijo", False) and not fuera)
    nota.pop("local_fijo", None)


def momento(nota):
    return datetime.fromisoformat(nota["publicada"] or nota["visto"])


def ventana_corte(dia):
    fin = datetime(dia.year, dia.month, dia.day, HORA_CORTE, tzinfo=CDMX)
    return fin - timedelta(days=1), fin


def dia_de_corte(cuando):
    """El corte del día D cubre de D-1 20:00 a D 20:00 (CDMX)."""
    return (cuando + timedelta(days=1)).date() if cuando.hour >= HORA_CORTE else cuando.date()


def cargar(ruta):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else []


def guardar(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ruta)


def recolectar(cfg, ahora):
    # Primero los feeds directos y luego Google News: al desduplicar se queda la liga del medio.
    fuentes = [dict(f, local=f.get("local", True)) for f in cfg.get("feeds", [])]
    for g in cfg.get("google_news", []):
        q = urllib.request.quote(g["q"] + " when:2d")
        # "local": true en la configuración, para medios locales cuyos titulares no nombran el lugar
        fuentes.append({"medio": g.get("medio"), "feed": GNEWS.format(q=q), "local": g.get("local", False),
                        "etiqueta": "Google News: " + g["q"]})
    lugares = [sin_acentos(l) for l in cfg.get("lugares", [])]
    notas, estado = [], []
    for f in fuentes:
        nombre = f.get("etiqueta") or f["medio"]
        url = f["feed"]
        if f.get("anti_cache"):
            url += ("&" if "?" in url else "?") + "v=" + ahora.strftime("%Y%m%d%H%M")
        try:
            crudo = leer_url(url)
            tipo = f.get("tipo", "rss")
            if tipo == "sitemap":
                nuevas = parsear_sitemap(crudo, f["medio"], ahora, f.get("filtro_url"))
            elif tipo == "wordpress":
                nuevas = parsear_wordpress(crudo, f["medio"], ahora)
            else:
                nuevas = parsear(crudo, f["medio"], ahora)
            if f.get("solo_lugares"):  # agregadores nacionales: solo lo que nombra al estado
                nuevas = [n for n in nuevas if any(l in sin_acentos(n["titulo"] + " " + n["resumen"]) for l in lugares)]
            for n in nuevas:
                n["local_fijo"] = f["local"]
                if f.get("sin_hora"):  # el medio publica solo la fecha
                    n["hora_aproximada"] = True
            notas += nuevas
            estado.append({"fuente": nombre, "ok": True, "notas": len(nuevas)})
        except Exception as err:  # una fuente caída no detiene el panel
            estado.append({"fuente": nombre, "ok": False, "error": type(err).__name__ + ": " + str(err)[:120]})
    return notas, estado


def procesar(cfg, ahora):
    carpeta = SALIDA / cfg["id"]
    notas, estado = recolectar(cfg, ahora)
    limite = ahora - timedelta(days=DIAS_RECIENTES)
    nuevas_por_dia = {}
    for n in notas:
        etiquetar(n, cfg)
        cuando = momento(n)
        if cuando < limite or cuando > ahora + timedelta(hours=1):
            continue
        nuevas_por_dia.setdefault(dia_de_corte(cuando).isoformat(), {})[clave(n)] = n
    for dia, nuevas in nuevas_por_dia.items():
        ruta = carpeta / "cortes" / f"{dia}.json"
        previas = {n["id"]: n for n in cargar(ruta)}
        for n in previas.values():  # los cambios de palabras clave aplican también a lo ya guardado
            n["temas"] = temas_de(n, cfg)
        for k, n in nuevas.items():
            if k not in previas:  # se conserva la primera vez que se vio
                n["id"] = k
                previas[k] = n
        guardar(ruta, sorted(previas.values(), key=momento, reverse=True))
    hoy = dia_de_corte(ahora)
    corte = cargar(carpeta / "cortes" / f"{hoy.isoformat()}.json")
    inicio, fin = ventana_corte(hoy)
    resumen = {
        "panel": cfg["nombre"],
        "actualizado": ahora.isoformat(timespec="minutes"),
        "corte": hoy.isoformat(),
        "ventana": [inicio.isoformat(timespec="minutes"), fin.isoformat(timespec="minutes")],
        "total": len(corte),
        "fuentes": estado,
    }
    guardar(carpeta / "estado.json", resumen)
    (carpeta / "index.html").write_text(pagina(cfg, resumen, corte), encoding="utf-8")
    return resumen


def fmt_hora(nota):
    d = momento(nota)
    return d.strftime("%d.%m %H:%M") + (" (aprox.)" if nota["hora_aproximada"] else "")


def pagina(cfg, resumen, corte):
    e = html.escape
    temas, medios = {}, {}
    for n in corte:
        for t in n["temas"]:
            temas[t] = temas.get(t, 0) + 1
        medios[n["medio"]] = medios.get(n["medio"], 0) + 1
    chips = " ".join(f'<button data-tema="{e(t)}">{e(t)} · {c}</button>'
                     for t, c in sorted(temas.items(), key=lambda x: -x[1]))
    opciones = "".join(f'<option>{e(m)}</option>' for m in sorted(medios))
    filas = "\n".join(
        f'<li data-temas="{e("|".join(n["temas"]))}" data-medio="{e(n["medio"])}" class="{"" if n["local"] else "nacional"}">'
        f'<span class="hora">{fmt_hora(n)}</span> <span class="medio">{e(n["medio"])}</span> '
        f'<a href="{e(n["liga"])}" rel="noopener" target="_blank">{e(n["titulo"])}</a> '
        f'<span class="temas">{e(", ".join(n["temas"]))}{"" if n["local"] else " · nacional"}</span></li>'
        for n in corte)
    caidas = [f["fuente"] for f in resumen["fuentes"] if not f["ok"]]
    aviso = (f'<p class="aviso">Fuentes que no respondieron en esta actualización: {e(", ".join(caidas))}</p>'
             if caidas else "")
    ini, fin = (datetime.fromisoformat(x).strftime("%d.%m.%Y %H:%M") for x in resumen["ventana"])
    act = datetime.fromisoformat(resumen["actualizado"]).strftime("%d.%m.%Y %H:%M")
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Noticias {e(cfg["nombre"])}</title>
<style>
:root{{--tinta:#1d2430;--papel:#faf8f3;--linea:#e3ded3;--suave:#6b6f78;--rojo:#c8341f}}
body{{margin:0;background:var(--papel);color:var(--tinta);font:15px/1.45 system-ui,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:16px}}
h1{{font-size:22px;margin:0 0 4px}} .meta{{color:var(--suave);margin:0 0 12px}}
.filtros{{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}}
button,select{{font:inherit;border:1px solid var(--linea);background:#fff;border-radius:14px;padding:3px 10px;cursor:pointer}}
button.activo{{background:var(--tinta);color:#fff}}
ul{{list-style:none;padding:0;margin:0}} li{{padding:8px 0;border-bottom:1px solid var(--linea)}}
.hora{{color:var(--suave);font-variant-numeric:tabular-nums}} .medio{{font-weight:600}}
.temas{{display:block;color:var(--suave);font-size:13px}} li.nacional{{opacity:.75}}
.aviso{{color:var(--rojo)}} a{{color:inherit}}
</style></head><body><main>
<h1>Noticias · {e(cfg["nombre"])}</h1>
<p class="meta">Actualizado automáticamente: {act} h (CDMX) · Corte del {datetime.fromisoformat(resumen["ventana"][1]).strftime("%d.%m.%Y")}: de {ini} a {fin} h · {resumen["total"]} notas</p>
{aviso}
<div class="filtros"><button data-tema="" class="activo">Todas</button> {chips}
<select id="medio"><option value="">Todos los medios</option>{opciones}</select>
<label><input type="checkbox" id="locales"> Solo notas locales</label></div>
<ul id="notas">
{filas}
</ul>
<p class="meta">Datos: <a href="estado.json">estado.json</a> · <a href="cortes/{resumen["corte"]}.json">cortes/{resumen["corte"]}.json</a></p>
</main>
<script>
let tema="",medio="",locales=false;
function filtrar(){{document.querySelectorAll("#notas li").forEach(li=>{{
 const okT=!tema||li.dataset.temas.split("|").includes(tema), okM=!medio||li.dataset.medio===medio;
 const okL=!locales||!li.classList.contains("nacional");
 li.style.display=okT&&okM&&okL?"":"none";}});}}
document.getElementById("locales").onchange=ev=>{{locales=ev.target.checked;filtrar();}};
document.querySelectorAll("button[data-tema]").forEach(b=>b.onclick=()=>{{
 tema=b.dataset.tema;document.querySelectorAll("button[data-tema]").forEach(x=>x.classList.toggle("activo",x===b));filtrar();}});
document.getElementById("medio").onchange=ev=>{{medio=ev.target.value;filtrar();}};
</script></body></html>
"""


def indice(resumenes):
    e = html.escape
    items = "".join(f'<li><a href="{e(r["id"])}/">{e(r["panel"])}</a> · {r["total"]} notas en el corte</li>'
                    for r in resumenes)
    (SALIDA / "index.html").write_text(
        '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="robots" content="noindex, nofollow">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Paneles de noticias</title>'
        '<style>body{margin:0;background:#faf8f3;color:#1d2430;font:16px/1.5 system-ui,sans-serif}'
        'main{max-width:720px;margin:0 auto;padding:16px}</style></head>'
        f'<body><main><h1>Paneles de noticias</h1><ul>{items}</ul></main></body></html>', encoding="utf-8")
    (SALIDA / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    (SALIDA / ".nojekyll").write_text("", encoding="utf-8")


def main():
    ahora = datetime.now(CDMX).replace(microsecond=0)
    resumenes = []
    for ruta in sorted(CONFIG.glob("*.json")):
        cfg = json.loads(ruta.read_text(encoding="utf-8"))
        r = procesar(cfg, ahora)
        r["id"] = cfg["id"]
        resumenes.append(r)
        caidas = sum(not f["ok"] for f in r["fuentes"])
        print(f'{cfg["id"]}: {r["total"]} notas en el corte {r["corte"]}; fuentes caídas: {caidas}')
    indice(resumenes)


if __name__ == "__main__":
    main()
