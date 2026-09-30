# Radar de Traspasos

Buscador de negocios en traspaso y venta en España. Un robot revisa los portales cada 6 horas, resume con IA los anuncios nuevos y los publica en una web estática. Coste: 0 € (más ~10 €/año de dominio y céntimos de IA).

```
GitHub Actions (cada 6 h)                         ← el "agente"
  └─ python -m scraper.run
       1. lee el sitemap de cada portal
       2. descarga SOLO las fichas nuevas (respeta robots.txt y pausas)
       3. normaliza: precio, provincia, sector, tipo
       4. descarta: compradores, solares/pisos, extranjero
       5. deduplica (mismo negocio en varios portales)
       6. resume con Claude (o plantilla si no hay clave)
       7. marca como "retirado" lo que desaparece del portal
       8. guarda en site/src/data/listings.json
  └─ git commit + push
Cloudflare Pages detecta el push → compila Astro → publica la web
```

---

## ¿Necesito un agente?

**No.** El agente es el workflow de GitHub Actions (`.github/workflows/update.yml`): un servidor gratuito de GitHub que se enciende cada 6 horas, ejecuta el robot, sube los datos y se apaga. No tienes que tener nada encendido.

La IA solo interviene para escribir los resúmenes, a través de la API de Claude. Para eso necesitas **una clave de API** (paso 3). Si no la pones, todo funciona igual y los resúmenes salen de una plantilla con los datos del anuncio.

Lo que necesitas son tres cuentas gratuitas:

| Cuenta | Para qué | Coste |
|---|---|---|
| GitHub | guardar el código y ejecutar el robot | gratis |
| Cloudflare | alojar la web | gratis |
| Claude Console (opcional) | resúmenes con IA | ~0,001 $ por anuncio |

---

## Paso a paso

### 1. Sube el código a GitHub

1. Entra en https://github.com/new, nombre `radar-traspasos`, **Public** (minutos de Actions ilimitados; en privado tienes 2.000 min/mes, que también bastan).
2. No marques "Add README". Crea el repo.
3. En tu ordenador, dentro de la carpeta descomprimida:

```bash
git init
git add .
git commit -m "Esqueleto inicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/radar-traspasos.git
git push -u origin main
```

### 2. Da permiso de escritura al robot

GitHub → tu repo → **Settings → Actions → General → Workflow permissions** → marca **Read and write permissions** → **Save**.

Sin esto el robot no puede guardar los anuncios.

### 3. (Opcional) Resúmenes con IA

1. Entra en https://platform.claude.com, inicia sesión y añade crédito (5 $ te dan para miles de resúmenes).
2. **API Keys → Create Key**. Copia la clave (empieza por `sk-ant-`). Solo se muestra una vez.
3. GitHub → repo → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `ANTHROPIC_API_KEY`
   - Secret: la clave

Coste con Claude Haiku 4.5: unos 700 tokens de entrada y 100 de salida por anuncio ≈ 0,0012 $. Solo se resumen los anuncios nuevos, nunca los ya publicados.

### 4. Variable con la URL de tu web

GitHub → **Settings → Secrets and variables → Actions → pestaña Variables → New repository variable**
- Name: `SITE_URL`
- Value: `https://radar-traspasos.pages.dev` (la cambiarás por tu dominio en el paso 7)

### 5. Primera ejecución (carga inicial)

GitHub → pestaña **Actions** → **Actualizar anuncios** → **Run workflow** → en "Máximo de anuncios nuevos por portal" pon `150` → **Run workflow**.

Tarda unos 30 min (bizalia exige 10 s entre peticiones). Cuando termine verás un commit nuevo de `traspasos-bot` con `listings.json` lleno. Repítelo 2–3 veces para completar la carga; después el cron se encarga solo con los valores por defecto (60 y 30 nuevos por ejecución).

Si falla, abre la ejecución y lee el paso "Revisar portales…": el log dice cuántas fichas encontró, cuáles descartó y por qué.

### Portales incluidos

| Portal | Cómo descubre anuncios | Pausa | Nuevos por ejecución |
|---|---|---|---|
| negociosenventa.es | sitemap.xml | 3 s | 60 |
| bizalia.com | sitemap (solo `/en-venta/`, último año) | 10 s (su Crawl-delay) | 30 |
| Transmisión de Empresas (Ministerio) | su buscador con Chromium sin interfaz (Playwright), hasta 15 páginas | 3 s | 40 |

La bolsa del Ministerio no tiene sitemap y carga los resultados con JavaScript, por eso usa Playwright. El workflow ya instala Chromium. Si algún día cambian el buscador y deja de encontrar anuncios, el log dirá `el buscador no devolvió enlaces a fichas`: ajusta `_SEARCH_BUTTONS` / `_NEXT_SELECTORS` en `scraper/sources/transmisionempresas.py`. Para probarlo en local: `python -m playwright install chromium` y `python -m scraper.run discover transmisionempresas`.

Wallapop y Milanuncios **no** están incluidos: sus condiciones prohíben el scraping y tienen protección anti-bot.

### 6. Publica la web en Cloudflare Pages

1. https://dash.cloudflare.com → **Workers & Pages → Create → Pages → Connect to Git** → autoriza GitHub → elige `radar-traspasos`.
2. Configuración de build:
   - Framework preset: **Astro**
   - Build command: `npm run build`
   - Build output directory: `dist`
   - **Root directory (advanced): `site`**
3. **Environment variables** (Production):
   - `NODE_VERSION` = `22`
   - `SITE_URL` = `https://radar-traspasos.pages.dev`
   - `PUBLIC_SITE_NAME` = el nombre de tu web
   - `PUBLIC_CONTACT_EMAIL` = tu email
4. **Save and Deploy**. En 1–2 min tienes la web en `https://radar-traspasos.pages.dev`.
5. Para no gastar builds de más: proyecto → **Settings → Builds → Build watch paths** → Include paths: `site/*`. Así solo se recompila cuando cambian los anuncios o la web.

A partir de aquí todo es automático: robot → commit → Cloudflare recompila → web actualizada.

### 7. Dominio propio (necesario para AdSense)

1. Cloudflare → **Domain Registration → Register Domains** → compra el dominio (~10 €/año, a precio de coste).
2. Proyecto de Pages → **Custom domains → Set up a custom domain** → escribe el dominio → Cloudflare configura el DNS solo.
3. Actualiza `SITE_URL` con el dominio nuevo en **GitHub (variable)** y en **Cloudflare (env var)**, y relanza el deploy.
4. Edita `site/src/pages/aviso-legal.astro` y `privacidad.astro` con tu nombre y NIF (obligatorio por la LSSI).
5. Da de alta la web en Google Search Console y envía `https://tudominio.es/sitemap-index.xml`.

### 8. AdSense

Espera a tener unas semanas de datos, la guía y la página de precios con contenido. Luego:

1. https://adsense.google.com → añade tu dominio → Google te da un código `ca-pub-XXXXXXXXXXXXXXXX`.
2. Cloudflare → env vars: `PUBLIC_ADSENSE_CLIENT` = `ca-pub-...` y, cuando crees un bloque de anuncios, `PUBLIC_ADSENSE_SLOT` = su id.
3. Sustituye el contenido de `site/public/ads.txt` por la línea que te da Google.
4. En AdSense → **Privacidad y mensajes** activa el mensaje de consentimiento GDPR (obligatorio en Europa).
5. Redeploy y solicita la revisión.

---

## Probar en tu ordenador

```bash
# Robot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium          # solo para transmisionempresas
pytest -q                                            # tests offline
python -m scraper.run discover negociosenventa       # qué URLs ve en el sitemap
python -m scraper.run parse https://www.negociosenventa.es/<ficha>   # qué extrae de una ficha
python -m scraper.run --max-new 5 --dry-run          # ejecución real sin guardar
python -m scraper.run --max-new 5                    # ejecución real

# Web
cd site && npm install && npm run dev                # http://localhost:4321
```

---

## Añadir un portal nuevo

1. Mira su `robots.txt` y su `sitemap.xml` (o busca la línea `Sitemap:` en robots.txt). Anota el patrón de URL de las fichas.
2. Crea `scraper/sources/<id>.py` copiando `bizalia.py`. La función `parse(html, url)` devuelve un dict con las mismas claves. `value_after(lines, "Etiqueta")` devuelve el texto que sigue a una etiqueta visible, así que casi nunca hace falta tocar selectores CSS.
3. Añade la fuente a `SOURCES` en `scraper/config.py` (`detail_regex`, `delay`, `max_new_per_run`).
4. Guarda una ficha de ejemplo en `tests/fixtures/` y añade un test como `test_parser_bizalia`.
5. `python -m scraper.run parse <url>` para comprobarlo con una ficha real.

Si un portal no tiene sitemap, el camino es parsear su página de listado ordenada por "más recientes"; se añade en `sitemap.py` como otra función de descubrimiento.

## La web (Astro + volt-ui)

La interfaz usa [volt-ui](https://github.com/Andersseen/volt-ui), una librería de componentes **Angular** con Tailwind v4, integrada en Astro con [`@analogjs/astro-angular`](https://analogjs.org):

- `site/src/components/ng/`: componentes Angular que usan volt-ui (`VoltCard`, `VoltBadge`, `VoltButton`, `VoltInput`, `VoltNativeSelect`, `VoltTable`, `VoltBreadcrumbs`, `VoltAlert`, `VoltSkeleton`…).
  - `explorer.component.ts`: filtros + rejilla de anuncios en **orden aleatorio** (distinto en cada visita, botón *Barajar*) con carga continua al hacer scroll. Es la única parte que se hidrata en el navegador (`client:load`).
  - `listing-card`, `listing-detail`, `stats-table`, `breadcrumbs`: se renderizan en el build, sin JavaScript en el navegador.
- Tema: `sage` (verde) + estilo `soft`, en `site/src/styles/global.css`. Para cambiarlo, sustituye la línea `@import "@voltui/components/themes/presets/sage-soft.css"` por otro preset (`volt`, `ember`, `dusk`, `glacier` × `sharp`, `soft`, `brutal`, `ghost`, `retro`).
- Modo oscuro automático según el sistema, con botón para cambiarlo en la cabecera.
- El HTML inicial de cada página incluye 24 anuncios (elegidos al azar en cada build) para que Google los indexe; al cargar, el navegador baraja todo el catálogo.

## Mantenimiento

- **Un portal cambia su diseño**: verás anuncios con precio o sector vacíos. Ejecuta `parse` sobre una ficha, ajusta las etiquetas en su parser y actualiza el fixture.
- **GitHub desactiva el cron** tras 60 días sin actividad en el repo. Los commits del robot cuentan como actividad, pero si un día deja de haber anuncios nuevos, GitHub te avisa por email: vuelve a activarlo en la pestaña Actions.
- **Anuncios retirados**: se muestran con aviso y `noindex`, y se borran a los 180 días (`PRUNE_RETIRED_AFTER_DAYS`).
- **Peticiones de retirada**: añade la URL a `data/state.json` → `skipped` y borra la entrada de `listings.json`.

## Límites legales que el código ya aplica

- Respeta `robots.txt` y `Crawl-delay`, se identifica con un User-Agent propio que apunta a `/bot/`.
- Solo guarda título, sector, ubicación, precio, facturación, superficie y fecha. **La descripción original se usa para generar el resumen y no se guarda.** Tampoco fotos ni contactos.
- Enlaza siempre al anuncio original con `rel="nofollow"`.
- Tiene página de retirada de anuncios y aviso legal.

Antes de monetizar a escala, escribe a cada portal ofreciendo tráfico a cambio de permiso o de un feed. Wallapop y Milanuncios prohíben el scraping en sus condiciones: no están incluidos.

## Estructura

```
.github/workflows/update.yml   el robot programado
scraper/
  config.py                    fuentes, límites, rutas
  fetch.py                     HTTP con robots.txt y pausas
  sitemap.py                   descubrimiento de fichas
  sources/                     un parser por portal
  normalize.py                 precios, 52 provincias, sectores, tipo
  dedupe.py                    duplicados entre portales
  summarize.py                 resúmenes con Claude o plantilla
  run.py                       pipeline y CLI
data/state.json                URLs descartadas + log de ejecuciones
tests/                         tests offline con fixtures
site/                          web Astro
  src/data/listings.json       los anuncios (lo escribe el robot)
  src/pages/                   inicio, ficha, sector, provincia, sector+provincia,
                               buscador, precios, guía, legales
```
