# Paneles de noticias por estado

Reemplazan los paneles que vivían en el GitHub personal de Dana (`danacorres.github.io/PanelNoticiasNL`, `/PanelNoticiasSINALOA` y `/Panel-BC`), que se borraron. No quedó copia de su código ni en el Internet Archive: estos se rehicieron a partir de lo que decían los criterios de los tres proyectos.

## Qué hacen
- Cada 30 minutos, un robot de GitHub (GitHub Actions) lee los feeds de los medios de cada estado y búsquedas de Google News, y publica una página por estado en GitHub Pages.
- Alrededor del corte corre más seguido: 19:47, 19:57, 20:03, 20:13 y 20:23 h CDMX (desde el 06.11.2026). GitHub retrasa las corridas programadas de 15 a 55 minutos en horas de carga: la de las 20:03 llegó a las 20:52 el 02.11, a las 20:42 el 04.11 y a las 20:18 el 05.11. Con varias corridas, alguna suele llegar a tiempo. Las notas se archivan por su hora de publicación, así que una corrida tardía completa el corte sin mezclarlo con el siguiente.
- Cada nota trae medio, hora de publicación (CDMX), liga, temas y si es local o nacional.
- **Guardan historia.** Las notas se archivan por corte (`cortes/AAAA-MM-DD.json`, de las 20:00 h del día anterior a las 20:00 h del día), así que no se reinician a medianoche como los anteriores.
- La página dice cuándo se actualizó y qué fuentes no respondieron, para que nadie concluya "no hubo notas" cuando lo que falló fue la fuente.
- **Son neutrales:** solo noticias del estado, sin nombres de clientes ni de actores. El filtro por actor se hace en el proyecto de Cowork. Los sitios de GitHub Pages son públicos, por eso las páginas llevan `noindex` y `robots.txt` para que no aparezcan en buscadores.

## Lo que hay en esta carpeta
| Archivo | Qué es |
|---|---|
| `generar.py` | El programa. Solo usa Python estándar, sin instalar nada |
| `config/<estado>.json` | Feeds, búsquedas de Google News, lugares y palabras clave de temas de cada estado |
| `.github/workflows/paneles.yml` | La programación del robot (cada 30 minutos y cinco corridas extra alrededor del corte) |
| `docs/` | Lo que se publica. Lo genera el robot; no se edita a mano |

## Dónde vive (desde el 02.11.2026)
- Repositorio: https://github.com/Strategic-North/paneles (organización Strategic-North, cuenta stratnorth).
- Paneles: https://strategic-north.github.io/paneles/nl/ · /bc/ · /sinaloa/
- La primera corrida en GitHub respondió con 58 de 59 fuentes. La que faltó fue El Vigía, que bloquea los servidores de GitHub; ahora entra por Google News (`site:elvigia.net`).

**Para cambiar algo desde esta carpeta:** primero `git pull` (el robot sube datos cada media hora), luego editar `config/` o `generar.py`, hacer commit y `git push`. No generar `docs/` a mano: lo genera el robot.

## Cómo se montó (02.11.2026; ya hecho, sirve si hay que rehacerlo)
1. Organización de Norte en GitHub (plan Free) con correo institucional: `Strategic-North`.
2. Repositorio **público** `paneles` (GitHub Pages gratis pide repositorio público) con `generar.py`, `config/`, `.github/` y este `README.md`.
3. **Settings → Actions → General → Workflow permissions → Read and write permissions**.
4. **Settings → Pages → Build and deployment:** *Deploy from a branch*, rama `main`, carpeta `/docs`.
5. **Actions → Actualizar paneles → Run workflow** para una corrida a mano (sale casi al instante, sin esperar la fila de las programadas).

**Pendiente: segundo dueño.** La organización tiene un solo dueño (cuenta stratnorth). Para que no se pierda si alguien sale, alguien del equipo con cuenta de GitHub y correo institucional se agrega en github.com/orgs/Strategic-North/people → *Invite member* → rol *Owner*.

## Ligas para los proyectos de Cowork
- Página: `https://<organización>.github.io/paneles/<estado>/` (estados: `nl`, `bc`, `sinaloa`).
- Datos del corte: `https://<organización>.github.io/paneles/<estado>/cortes/AAAA-MM-DD.json?v=AAAAMMDDhhmm`.
- Estado de la última corrida: `.../<estado>/estado.json`.
- Siempre con el parámetro `?v=` para que no llegue una copia vieja, y revisando que `actualizado` sea del día del corte.

## Mantenimiento
- **Agregar o quitar un medio:** editar `config/<estado>.json` en GitHub (botón del lápiz) y guardar. La siguiente corrida ya lo usa.
- **Medios locales por Google News:** si un medio no tiene feed, entra con una búsqueda `site:`. Con `"local": true` en esa búsqueda, sus notas cuentan como locales aunque el titular no nombre el lugar (así entran Ensenada.net y EnsenadaHoy desde el 06.11.2026; de EnsenadaHoy solo `/noticias`, porque el resto del sitio son clasificados y empleos).
- **Alertas de nota roja en Baja California** (desde el 06.11.2026): búsquedas fijas de policías municipales detenidos, deslindes del Ayuntamiento de Ensenada y funcionarios detenidos. Casi siempre traen cero notas; sirven para que el día que pase algo aparezca en el panel. El barrido a mano del proyecto de Ensenada sigue igual.
- **Revisar una vez al mes** que la fecha de "Actualizado automáticamente" sea reciente. GitHub pausa los robots de repositorios sin actividad por 60 días; los guardados del propio robot deberían mantenerlo activo, pero conviene confirmarlo.
- Google News devuelve como máximo 100 notas por búsqueda. Por eso conviene usar búsquedas por medio (`site:`) o por ciudad, en vez de una sola búsqueda general.
- **Medios que el panel no puede leer** y se revisan a mano: Brújula (BC), que solo publica en Facebook mientras su sitio está en mantenimiento. El Debate (Sinaloa) bloquea lectores y entra solo por Google News. El Vigía trae fecha sin hora ("aprox.").
- **Temas:** se asignan por palabras clave del titular y por la sección de la liga (`/seguridad/`, `/deportes/`). Se afinan en `config/<estado>.json` (`temas` y `secciones`). Con la versión del 02.11.2026, cerca del 20 % de las notas locales quedó en "Otros".
- Las ligas de Google News pasan por `news.google.com` antes de llegar al medio. Para citar, se abre la nota y se usa la liga del medio.
- Esto es una automatización: anotarla en el `CLAUDE.md` (qué hace, cuándo corre, dónde deja el resultado) cuando quede activa.
