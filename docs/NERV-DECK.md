# NERV Deck

Widget de escritorio para KDE Plasma, con aspecto de consola EVA: negro mate, morado, verde vivo y ámbar en espera. Interfaz en español, controles accesibles por teclado y títulos tratados como texto, con puntos suspensivos cuando no caben.

## Requisitos y funcionamiento

Probado con Plasma **6.6.6** y Qt **6.10.2**. Usa el módulo MPRIS que Plasma ya incluye: no instala servicios, no necesita claves de API y no guarda credenciales de Spotify. Spotify o Spotifast deben estar abiertos y publicar su servicio MPRIS. Las pestañas de navegador y otros reproductores quedan fuera de la selección.

El paquete usa la API `org.kde.plasma.private.mpris` disponible en Plasma 6.6. El número de versión mínimo queda declarado en sus metadatos. Antes de usar una versión nueva de Plasma, comprobar la compatibilidad de esa API con las pruebas del repositorio.

## Instalar y añadir al escritorio

Desde la raíz del repositorio, como usuario normal:

```bash
python3 instalar-widget.py
python3 instalar-widget.py --apply
```

El primer comando simula sin escribir. El segundo instala únicamente `com.xfunbox.nervdeck` en `${XDG_DATA_HOME:-$HOME/.local/share}/plasma/plasmoids/`.

En Plasma, entrar en modo de edición del escritorio, abrir **Añadir widgets**, buscar **NERV Deck** y arrastrarlo al escritorio. Su tamaño inicial está pensado para unos 440 píxeles de ancho. El botón de la esquina superior derecha alterna la vista compacta y los detalles.

El botón de apertura muestra la ventana del reproductor activo si este lo permite. En espera usa el acceso `eva-01-audio.desktop` del paquete [Spotifast EVA-01](https://github.com/XFunBox/spotifast-eva01), que debe estar instalado para poder abrirlo desde ese botón.

No se modifica ningún panel ni ninguna preferencia de Spotify/Spotifast. Los cambios de volumen, búsqueda o transporte se envían únicamente cuando se interactúa con sus controles.

## Controles

- Carátula, título y artista del reproductor seleccionado.
- Anterior, reproducción/pausa y siguiente, habilitados según sus capacidades.
- Progreso y volumen; el tiempo se muestra en minutos y segundos.
- Vista desplegada con álbum, aleatorio y repetición: desactivada → pista → lista.
- Selector **Automático** o reproductor concreto cuando se detectan varios clientes compatibles. En automático tiene prioridad un cliente que esté reproduciendo.
- Si se cierra el reproductor seleccionado, el widget vuelve a elegir entre los restantes. Si no queda ninguno, muestra **En espera**.

Los dos medidores ámbar permanecen en reposo con **VU STANDBY**: MPRIS no proporciona niveles de audio. No se inventa movimiento de agujas. La rueda de volumen admite arrastre, rueda del ratón y teclas de dirección al enfocarla. Los controles que el reproductor no ofrece se ocultan o deshabilitan.

## Ventana flotante y Ctrl+Alt+M

Tras instalar el paquete, preparar el acceso y atajo desde la sesión KDE:

```bash
python3 instalar-ventana.py
python3 instalar-ventana.py --apply
```

Necesita PyQt6 (QtCore, QtGui, QtDBus y QtQml), el módulo QML `org.kde.kwindowsystem`, `gdbus` y `kbuildsycoca6`. En el equipo de origen ya estaban disponibles.

**Ctrl+Alt+M** muestra una ventana compacta por encima de las aplicaciones y le da el foco. La siguiente pulsación la oculta; **Escape** también la oculta. Arrastrar la cabecera permite moverla. El acceso «NERV Deck» del menú hace lo mismo. Una única instancia permanece en la sesión después del primer lanzamiento; no se añade un servicio de inicio automático. La vista del escritorio y la ventana comparten diseño y controles, y ambas reflejan el reproductor activo.

El atajo lo ejecuta KGlobalAccel mediante una entrada `.desktop`; en Wayland se reenvía el token de activación al proceso existente. El instalador comprueba conflictos y modifica únicamente la acción propia `_launch` de `com.xfunbox.nervdeck.desktop`, con copia de sus dos accesos y teclas previas. No restaura el archivo global de atajos completo.

Para deshacer el acceso/atajo, usar su copia exacta **antes de retirar el paquete** y cerrar la ventana:

```bash
gdbus call --session --dest com.xfunbox.NervDeck --object-path /NervDeck --method com.xfunbox.NervDeck.Quit
python3 instalar-ventana.py --restore /ruta/impresa/de/la/copia --apply
```

Si la ventana no está iniciada, la primera orden simplemente indicará que el servicio no existe. Las copias del acceso están en `${XDG_STATE_HOME:-$HOME/.local/state}/nerv-deck/shortcuts/`; las del paquete, en `nerv-deck/backups/`.

## Copia y restauración

Cada instalación imprime una copia privada bajo `${XDG_STATE_HOME:-$HOME/.local/state}/nerv-deck/backups/`. Se copia solo el paquete del widget, nunca la distribución de paneles o la configuración global de Plasma.

```bash
python3 instalar-widget.py --restore /ruta/impresa/de/la/copia
python3 instalar-widget.py --restore /ruta/impresa/de/la/copia --apply
```

Si el widget no existía antes de la instalación, restaurar esa copia retira el paquete. Quitar primero su instancia del escritorio para que no quede un widget apuntando a archivos ausentes. Si existía, la restauración devuelve el paquete anterior y conserva otra copia del estado que sustituye. Volver a añadir la instancia carga la versión restaurada.

## Pruebas y vistas previas

Para desarrollo se usan Python 3, PyQt6 con QtGui/QtQml, `python3-dbus`, PyGObject/GLib y `dbus-daemon`, además de KDE instalado. No hacen falta credenciales ni una sesión Spotify para las pruebas.

```bash
python3 -m unittest discover -s tests -v
node tests/test_ventanas.cjs
python3 tests/render_widget.py --mode compact --output /tmp/nerv-compacto.png
python3 tests/render_widget.py --mode expanded --output /tmp/nerv-desplegado.png
python3 tests/render_widget.py --mode idle --output /tmp/nerv-espera.png
```

`test_nerv_deck.py` arranca un bus privado sin activación de servicios del sistema y simula Spotify, Spotifast y un cliente ajeno. Comprueba descubrimiento, unidades de tiempo, avance del progreso sin señales de posición, órdenes de transporte, búsqueda, volumen, aleatorio/repetición, capacidades y desconexión. No usa el bus de la sesión ni reproduce audio. Las vistas previas renderizan los componentes QML reales con datos ficticios.

`test_floating_window.py` verifica lanzamiento, ocultación y reaparición de la misma instancia en un bus privado. Las pruebas del acceso cubren copia/restauración, conflicto y formato de teclas Qt. `test_shortcut_dbus.py` comprueba varias altas, retiradas y nuevas altas contra el daemon real de KGlobalAccel en un bus privado, con plataforma offscreen y HOME/XDG temporales, sin conexión al escritorio. En la sesión KDE de origen, la acción nativa mostró la ventana con foco y luego la ocultó; no se simuló una pulsación física de teclado.

El instalador se prueba con HOME/XDG temporales: simulación sin escrituras, sustitución con copia, restauración, conservación de archivos ajenos y rechazo de rutas o paquetes incorrectos. La UI también se cargó mediante el runtime real `plasmawindowed` en un entorno temporal, sin errores QML.

El registro serializa siempre cuatro enteros por `QKeySequence`, como exige el protocolo de KDE. En la versión de desarrollo, enviar solo un entero provocó abortos de KGlobalAccel dentro de KWin en Wayland. El fallo se reprodujo fuera de la sesión y se corrigió antes de publicar; la aplicación final conservó el proceso de KWin. No hace falta reiniciar KDE para instalar el acceso o usar el widget.

## Fuentes de KDE

- [Serialización D-Bus de QKeySequence](https://github.com/KDE/kglobalaccel/blob/master/src/kglobalshortcutinfo_dbus.cpp).
- [KGlobalAccel](https://api.kde.org/kglobalaccel.html) y [acciones de aplicaciones en kglobalacceld](https://github.com/KDE/kglobalacceld/blob/master/src/kserviceactioncomponent.cpp).

- [Paquetes y raíz PlasmoidItem en Plasma 6](https://develop.kde.org/docs/plasma/widget/porting_kf6/).
- [Modelo MPRIS de Plasma 6.6](https://invent.kde.org/plasma/plasma-workspace/-/blob/Plasma/6.6/libkmpris/mpris2model.h).
- [Propiedades y métodos del reproductor](https://invent.kde.org/plasma/plasma-workspace/-/blob/Plasma/6.6/libkmpris/playercontainer.h).

Código e imágenes SVG propios bajo MIT. El diseño y los recursos pertenecen a este repositorio; no se distribuyen carátulas ni datos de una cuenta musical.
