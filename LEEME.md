# Paneles de noticias por estado

Reemplazan los paneles que vivían en el GitHub personal de Dana (`danacorres.github.io/PanelNoticiasNL`, `/PanelNoticiasSINALOA` y `/Panel-BC`), que se borraron. No quedó copia de su código ni en el Internet Archive: estos se rehicieron a partir de lo que decían los criterios de los tres proyectos.

## Qué hacen
- Cada 30 minutos, un robot de GitHub (GitHub Actions) lee los feeds de los medios de cada estado y búsquedas de Google News, y publica una página por estado en GitHub Pages.
- Cada nota trae medio, hora de publicación (CDMX), liga, temas y si es local o nacional.
- **Guardan historia.** Las notas se archivan por corte (`cortes/AAAA-MM-DD.json`, de las 20:00 h del día anterior a las 20:00 h del día), así que no se reinician a medianoche como los anteriores.
- La página dice cuándo se actualizó y qué fuentes no respondieron, para que nadie concluya "no hubo notas" cuando lo que falló fue la fuente.
- **Son neutrales:** solo noticias del estado, sin nombres de clientes ni de actores. El filtro por actor se hace en el proyecto de Cowork. Los sitios de GitHub Pages son públicos, por eso las páginas llevan `noindex` y `robots.txt` para que no aparezcan en buscadores.

## Lo que hay en esta carpeta
| Archivo | Qué es |
|---|---|
| `generar.py` | El programa. Solo usa Python estándar, sin instalar nada |
| `config/<estado>.json` | Feeds, búsquedas de Google News, lugares y palabras clave de temas de cada estado |
| `.github/workflows/paneles.yml` | La programación del robot (cada 30 minutos y justo después del corte) |
| `docs/` | Lo que se publica. Lo genera el robot; no se edita a mano |

## Montarlo (una sola vez)
1. **Crear la organización de Norte en GitHub** (plan Free) con un correo institucional, no personal, y con **al menos dos dueños**. Así, si alguien sale, la organización no se pierde. Si prefieren que la liga no diga "Norte", se puede usar un nombre neutro.
2. Crear en la organización un repositorio **público** llamado `paneles` (GitHub Pages gratis pide repositorio público) y subir esta carpeta tal cual: `generar.py`, `config/`, `.github/` y este `LEEME.md`.
3. En el repositorio: **Settings → Actions → General → Workflow permissions → Read and write permissions**.
4. **Settings → Pages → Build and deployment:** *Deploy from a branch*, rama `main`, carpeta `/docs`.
5. **Actions → Actualizar paneles → Run workflow** para la primera corrida. En uno o dos minutos queda en `https://<organización>.github.io/paneles/`.

Si quieres, lo subo yo desde aquí con `git` cuando la organización exista y tengas sesión de GitHub en esta computadora.

## Ligas para los proyectos de Cowork
- Página: `https://<organización>.github.io/paneles/<estado>/` (estados: `nl`, `bc`, `sinaloa`).
- Datos del corte: `https://<organización>.github.io/paneles/<estado>/cortes/AAAA-MM-DD.json?v=AAAAMMDDhhmm`.
- Estado de la última corrida: `.../<estado>/estado.json`.
- Siempre con el parámetro `?v=` para que no llegue una copia vieja, y revisando que `actualizado` sea del día del corte.

## Mantenimiento
- **Agregar o quitar un medio:** editar `config/<estado>.json` en GitHub (botón del lápiz) y guardar. La siguiente corrida ya lo usa.
- **Revisar una vez al mes** que la fecha de "Actualizado automáticamente" sea reciente. GitHub pausa los robots de repositorios sin actividad por 60 días; los guardados del propio robot deberían mantenerlo activo, pero conviene confirmarlo.
- Google News devuelve como máximo 100 notas por búsqueda. Por eso conviene usar búsquedas por medio (`site:`) o por ciudad, en vez de una sola búsqueda general.
- **Medios que el panel no puede leer** y se revisan a mano: Brújula (BC), que solo publica en Facebook mientras su sitio está en mantenimiento. El Debate (Sinaloa) bloquea lectores y entra solo por Google News. El Vigía trae fecha sin hora ("aprox.").
- **Temas:** se asignan por palabras clave del titular y por la sección de la liga (`/seguridad/`, `/deportes/`). Se afinan en `config/<estado>.json` (`temas` y `secciones`). Con la versión del 02.11.2026, cerca del 20 % de las notas locales quedó en "Otros".
- Las ligas de Google News pasan por `news.google.com` antes de llegar al medio. Para citar, se abre la nota y se usa la liga del medio.
- Esto es una automatización: anotarla en el `CLAUDE.md` (qué hace, cuándo corre, dónde deja el resultado) cuando quede activa.
