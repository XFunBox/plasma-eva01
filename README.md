# Plasma EVA-01

Mi configuración reutilizable de KDE Plasma: negro, morado y verde vivo, con atajos para teclado de 60 %, organización de ventanas y terminales EVA-01.

El instalador muestra una simulación por defecto. Solo escribe con `--apply`, guarda una copia previa y permite restaurarla. No cambia la barra de tareas, el fondo, las pantallas ni el número de escritorios virtuales.

## NERV Deck: widget de Spotify y Spotifast

Widget analógico compacto con botones redondos, rueda de volumen y medidores ámbar en reposo, nativo para el escritorio de **Plasma 6.6 o posterior**: carátula, canción y artista, controles, progreso y volumen. Se despliega para mostrar álbum, aleatorio y repetición. Detecta Spotify y Spotifast mediante MPRIS y permite elegir entre ellos si están abiertos a la vez. Sin un reproductor abierto muestra el estado de espera y un acceso a EVA-01 Audio.

Se instala por separado de la personalización del escritorio:

```bash
python3 instalar-widget.py
python3 instalar-widget.py --apply
```

Después, en el escritorio: **Modo de edición → Añadir widgets → NERV Deck**. No añadirlo a la barra. El instalador prepara los archivos y conserva una copia del paquete anterior; no modifica distribuciones de paneles ni inicia reproducción.

Para la ventana flotante, ejecutar `python3 instalar-ventana.py --apply` después de instalar el paquete. **Ctrl+Alt+M** la muestra con foco y la siguiente pulsación la oculta.

[Uso, requisitos, pruebas y restauración de NERV Deck](docs/NERV-DECK.md).

## Requisitos

- Linux con **KDE Plasma 6 ya instalado**. Las fuentes proceden de un equipo Ubuntu con Plasma 6.6.6; otras distribuciones/versiones necesitan comprobarse.
- Python 3.10 o posterior y `kwriteconfig6` de KDE Frameworks 6.
- `qdbus6` para pedir a KWin que recargue la configuración; con `--no-reload` se preparan los archivos sin contactar con la sesión.
- Zsh para el componente de terminales. Kitty, Konsole y Ptyxis son aplicaciones opcionales que se instalan por separado.

Este repositorio personaliza una instalación de KDE existente. No instala el sistema operativo ni paquetes con `sudo`.

## Instalar

Clonar el repositorio público y revisar primero la simulación:

```bash
git clone https://github.com/XFunBox/plasma-eva01.git
cd plasma-eva01
python3 instalar.py
```

El último comando solo muestra los cambios previstos. Para aplicarlos, ejecutar como usuario normal, desde la sesión de KDE:

```bash
python3 instalar.py --apply
```

Se pueden seleccionar componentes:

```bash
python3 instalar.py --components apariencia ventanas
python3 instalar.py --apply --components apariencia ventanas
```

Para preparar los archivos sin recarga por D-Bus:

```bash
python3 instalar.py --apply --no-reload
```

Después de aplicar, cerrar sesión e iniciarla de nuevo carga de forma fiable la apariencia y los atajos. Abrir una terminal nueva carga su perfil y prompt. La recarga de KWin no sustituye el reinicio de sesión de todas las aplicaciones.

## Componentes

| Componente | Qué aplica |
| --- | --- |
| `apariencia` | Esquema EVA01Dark, colores seleccionados de KDE e iconos Breeze Dark. |
| `atajos` | Asignaciones concretas de KWin para minimizar, maximizar, mosaico izquierdo, vista general y escritorios 1–2. |
| `ventanas` | Complemento propio de KWin, acceso en aplicaciones y acciones para ordenar y restaurar ventanas. |
| `terminales` | Paleta y prompt Zsh para Kitty y Konsole; paleta preparada para Ptyxis. |

### Atajos y ventanas

| Atajo | Acción |
| --- | --- |
| Windows + M | Minimizar |
| Windows + X | Maximizar o restaurar |
| Windows + H | Mitad izquierda |
| Windows + W | Vista general |
| Ctrl + Alt + 1 / 2 | Escritorio 1 / 2, si existen |
| Windows + O | Ordenar ventanas de cada monitor |
| Windows + Shift + O | Restaurar la distribución anterior |

No se reasigna Windows + L, que se conserva para bloquear la sesión. Alt + Espacio es el acceso habitual a KRunner y no se modifica. No se crean escritorios adicionales ni se activan los atajos históricos de escritorios 3–4.

El organizador conserva cada ventana en su monitor y respeta el espacio que dejan los paneles. Excluye ventanas minimizadas, a pantalla completa, diálogos y Coucou. La distribución anterior se guarda en memoria: se pierde al reiniciar KWin o cerrar sesión. Algunas aplicaciones pueden imponer tamaños mínimos.

### Terminales

El prompt Zsh dedicado muestra usuario, máquina, ruta y reloj con segundos. No sustituye el `.zshrc` general ni modifica conexiones SSH. Los perfiles usan rutas calculadas durante la instalación, sin un nombre de usuario fijo.

El componente prepara una paleta `EVA-01` para Ptyxis. **No modifica automáticamente su perfil activo**: abrir Preferencias y elegir la paleta EVA-01 para el perfil deseado. Kitty y Konsole reciben la configuración y el perfil del instalador. Esta decisión evita trasladar el UUID de un perfil personal a otros equipos.

## Copias y restauración

Cada aplicación imprime la ruta de su copia privada, bajo `${XDG_STATE_HOME:-$HOME/.local/state}/plasma-eva01/backups/`. Las copias se quedan en el equipo y no forman parte del repositorio.

Usar la ruta exacta impresa por el instalador:

```bash
python3 instalar.py --restore /ruta/a/la/copia
python3 instalar.py --restore /ruta/a/la/copia --apply --no-reload
```

Cerrar las aplicaciones afectadas antes de restaurar y volver a iniciar sesión después. La restauración recupera los archivos completos guardados y elimina los archivos instalados que antes no existían. En archivos compartidos como `kdeglobals` o `kglobalshortcutsrc`, también revierte cambios posteriores hechos en ese mismo archivo: comprobar la fecha de la copia antes de usarla.

No editar el manifiesto de las copias ni moverlas entre usuarios o equipos. Si una aplicación falla durante la instalación, conservar la copia indicada para recuperar el estado anterior.

## Pruebas

Desde la raíz del repositorio:

```bash
python3 -m unittest discover -s tests -v
node tests/test_ventanas.cjs
zsh -n assets/terminales/prompt.zsh
```

Las pruebas Python usan directorios HOME/XDG temporales y `kwriteconfig6` real, sin cambiar el escritorio. La prueba JavaScript comprueba las decisiones del script con un adaptador de la API de KWin; no reemplaza una prueba visual con ventanas reales. Node.js y Zsh solo se necesitan para las comprobaciones correspondientes.

## Procedencia y alcance

- El complemento `eva01-ordenar-ventanas` y el esquema EVA01Dark se compararon con los archivos instalados antes de incorporarlos.
- Las paletas de Konsole/Ptyxis y el prompt se recuperaron de los recursos locales; la configuración de Kitty se limpió para conservar el último valor efectivo de cada ajuste.
- El instalador antiguo de apariencia llamaba a otro script que cambiaba el panel. Esa dependencia no se utiliza aquí.
- No se incluyen volcados completos de `.config`, UUID de perfiles, historiales de terminal, credenciales, copias antiguas, paquetes de terceros ni archivos de las notas de Obsidian.

Referencias de KDE: [empaquetado e instalación de scripts KWin](https://develop.kde.org/docs/plasma/kwin/) y [API de scripting](https://develop.kde.org/docs/plasma/kwin/api/).

Código propio bajo MIT. El esquema `assets/EVA01Dark.colors` conserva sus autores y la licencia LGPL-2.0-or-later de la base KDE; véase `LICENSES.md`.
