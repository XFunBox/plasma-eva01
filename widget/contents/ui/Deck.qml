import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: deck
    objectName: "nervDeck"
    required property var controller
    property bool detailOpen: false
    signal detailToggled(bool expanded)
    readonly property bool hasPlayers: controller.players && controller.players.length > 1
    readonly property int selectorSpace: hasPlayers ? 40 : 0
    readonly property color green: "#b7ff3c"
    readonly property color muted: "#b4a9c4"
    readonly property string fallbackArt: Qt.resolvedUrl("../images/cover-fallback.svg")
    implicitWidth: 380
    implicitHeight: (detailOpen ? 330 : 190) + selectorSpace
    Accessible.name: "NERV Deck, controles de música"

    function timeLabel(ms) {
        const seconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
        return Math.floor(seconds / 60) + ":" + (seconds % 60 < 10 ? "0" : "") + seconds % 60;
    }

    Canvas {
        id: shell
        anchors.fill: parent
        property real breath: 0.45
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onBreathChanged: requestPaint()
        SequentialAnimation on breath {
            running: deck.controller.available && deck.controller.playing && deck.visible
            loops: Animation.Infinite
            NumberAnimation { to: 0.85; duration: 2200; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.35; duration: 2200; easing.type: Easing.InOutSine }
        }
        Connections {
            target: deck.controller
            function onPlayingChanged() { shell.requestPaint() }
            function onAvailableChanged() { shell.requestPaint() }
        }
        onPaint: {
            const c = getContext("2d");
            c.reset();
            const w = width - 1, h = height - 1;
            c.beginPath(); c.moveTo(12, 0.5); c.lineTo(w - 30, 0.5); c.lineTo(w, 30);
            c.lineTo(w, h - 12); c.lineTo(w - 12, h); c.lineTo(0.5, h); c.lineTo(0.5, 12); c.closePath();
            c.fillStyle = "#08080b"; c.fill(); c.strokeStyle = "#60417c"; c.lineWidth = 1; c.stroke();
            c.beginPath(); c.moveTo(12, h - 1); c.lineTo(w - 40, h - 1);
            c.strokeStyle = deck.controller.playing && deck.controller.available ? "rgba(183,255,60," + breath + ")" : "#644084";
            c.lineWidth = 2; c.stroke();
        }
    }

    RowLayout {
        x: 14; y: 8; width: parent.width - 44; height: 28
        spacing: 8
        Rectangle { width: 5; height: 14; color: deck.controller.available ? deck.green : "#e9b96b" }
        Text { text: "NERV DECK"; color: "#eae4f1"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 2; textFormat: Text.PlainText }
        Text {
            Layout.fillWidth: true
            text: !deck.controller.available ? "EN ESPERA" : deck.controller.playing ? "REPRODUCIENDO" : "EN PAUSA"
            color: deck.controller.available ? deck.muted : "#e9b96b"
            font.family: "monospace"; font.pixelSize: 9; elide: Text.ElideRight; horizontalAlignment: Text.AlignRight
            textFormat: Text.PlainText
        }
        DeckButton {
            objectName: "toggleDetails"
            implicitWidth: 32; implicitHeight: 32
            symbol: deck.detailOpen ? "collapse" : "expand"
            label: deck.detailOpen ? "Ocultar detalles" : "Mostrar detalles"
            onClicked: { deck.detailOpen = !deck.detailOpen; deck.detailToggled(deck.detailOpen); }
        }
    }

    ComboBox {
        id: playerSelector
        objectName: "playerSelector"
        x: 14; y: 40; width: parent.width - 28; height: 32
        visible: deck.hasPlayers
        model: ["Automático"].concat((deck.controller.players || []).map(function(player) { return String(player.label || "Reproductor"); }))
        currentIndex: deck.controller.selectedPlayerIndex + 1
        onActivated: function(index) { deck.controller.selectPlayer(index - 1); }
        Accessible.name: "Reproductor de música"
        font.pixelSize: 11
        palette.button: "#191321"; palette.buttonText: "#eee9f7"; palette.text: "#eee9f7"
        palette.base: "#191321"; palette.highlight: "#513267"; palette.highlightedText: "#b7ff3c"
        background: Rectangle { color: "#191321"; border.color: playerSelector.activeFocus ? deck.green : "#49305e"; radius: 3 }
    }

    RowLayout {
        id: trackRow
        x: 14; y: 44 + deck.selectorSpace
        width: parent.width - 28; height: deck.detailOpen ? 128 : 72
        spacing: 12
        Rectangle {
            Layout.preferredWidth: deck.detailOpen ? 128 : 72
            Layout.fillHeight: true
            color: "#14101c"; border.color: "#49305e"
            Image {
                id: cover
                anchors.fill: parent; anchors.margins: 1
                asynchronous: true; fillMode: Image.PreserveAspectCrop
                source: deck.controller.artUrl || deck.fallbackArt
                sourceSize.width: 256; sourceSize.height: 256
                visible: status === Image.Ready
                Accessible.ignored: true
            }
            Image {
                anchors.fill: parent; anchors.margins: 1
                source: deck.fallbackArt; fillMode: Image.PreserveAspectCrop
                visible: cover.status !== Image.Ready
                Accessible.ignored: true
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 4
            Text {
                id: trackTitle
                objectName: "trackTitle"
                Layout.fillWidth: true
                text: deck.controller.title || (deck.controller.available ? "Sin título" : "Tu música, aquí")
                color: "#f1edf7"; font.pixelSize: 15; font.bold: true
                elide: Text.ElideRight; textFormat: Text.PlainText
                Accessible.name: text
                ToolTip.text: text; ToolTip.visible: titleHover.hovered && truncated; ToolTip.delay: 700
                HoverHandler { id: titleHover }
            }
            Text {
                Layout.fillWidth: true
                text: deck.controller.artist || (deck.controller.available ? "Artista desconocido" : "Abre un reproductor para empezar")
                color: deck.muted; font.pixelSize: 11
                elide: Text.ElideRight; textFormat: Text.PlainText
            }
            Text {
                Layout.fillWidth: true
                visible: deck.detailOpen
                text: deck.controller.album || (deck.controller.available ? "Álbum sin indicar" : "Listo para conectar")
                color: "#b4a9c4"; font.pixelSize: 11
                elide: Text.ElideRight; textFormat: Text.PlainText
            }
            Item { Layout.fillHeight: true; visible: deck.detailOpen }
            RowLayout {
                visible: deck.controller.available
                spacing: 8
                DeckButton {
                    objectName: "previousButton"; symbol: "previous"; label: "Pista anterior"
                    enabled: deck.controller.available && deck.controller.canPrevious
                    onClicked: deck.controller.previous()
                }
                DeckButton {
                    objectName: "playPauseButton"; symbol: deck.controller.playing ? "pause" : "play"
                    label: deck.controller.playing ? "Pausar" : "Reproducir"; primary: true
                    implicitWidth: 48
                    enabled: deck.controller.available && deck.controller.canPlayPause
                    onClicked: deck.controller.playPause()
                }
                DeckButton {
                    objectName: "nextButton"; symbol: "next"; label: "Pista siguiente"
                    enabled: deck.controller.available && deck.controller.canNext
                    onClicked: deck.controller.next()
                }
            }
            Button {
                objectName: "emptyOpenPlayerButton"
                visible: !deck.controller.available
                text: "Abrir Spotifast"
                implicitHeight: 36
                implicitWidth: 144
                focusPolicy: Qt.StrongFocus
                Accessible.name: text
                contentItem: Text {
                    text: parent.text; color: deck.green; font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    textFormat: Text.PlainText
                }
                background: Rectangle {
                    color: parent.down ? "#39244f" : parent.hovered ? "#30203f" : "#191321"
                    border.color: parent.activeFocus ? deck.green : "#60417c"; radius: 3
                }
                onClicked: deck.controller.openPlayer()
            }
        }
    }

    RowLayout {
        x: 14; y: trackRow.y + trackRow.height + 4
        width: parent.width - 28; height: 28; spacing: 8
        Text { text: deck.timeLabel(seekSlider.pressed ? seekSlider.value : deck.controller.positionMs); color: deck.muted; font.family: "monospace"; font.pixelSize: 10; textFormat: Text.PlainText }
        Slider {
            id: seekSlider
            objectName: "seekSlider"
            Layout.fillWidth: true; Layout.preferredHeight: 28
            from: 0; to: Math.max(1, deck.controller.durationMs)
            value: deck.controller.positionMs
            enabled: deck.controller.available && deck.controller.canSeek && deck.controller.durationMs > 0
            Accessible.name: "Posición de reproducción"
            Accessible.description: deck.timeLabel(value) + " de " + deck.timeLabel(deck.controller.durationMs)
            onMoved: deck.controller.seekTo(value)
            background: Rectangle {
                x: seekSlider.leftPadding; y: seekSlider.topPadding + seekSlider.availableHeight / 2 - 2
                width: seekSlider.availableWidth; height: 4; radius: 2; color: "#34233f"
                Rectangle { width: parent.width * seekSlider.visualPosition; height: parent.height; radius: 2; color: seekSlider.enabled ? deck.green : "#6e5c7e" }
            }
            handle: Rectangle {
                x: seekSlider.leftPadding + seekSlider.visualPosition * (seekSlider.availableWidth - width)
                y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                width: 10; height: 10; radius: 5; color: seekSlider.enabled ? deck.green : "#6e5c7e"
                border.color: seekSlider.activeFocus ? "#ffffff" : color; border.width: 2
            }
            HoverHandler { cursorShape: seekSlider.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
        }
        Text { text: deck.timeLabel(deck.controller.durationMs); color: deck.muted; font.family: "monospace"; font.pixelSize: 10; textFormat: Text.PlainText }
    }

    RowLayout {
        x: 14; y: trackRow.y + trackRow.height + 34
        width: parent.width - 28; height: 36; spacing: 8
        Text { text: "VOL"; font.family: "monospace"; font.pixelSize: 9; color: deck.muted; textFormat: Text.PlainText }
        Slider {
            id: volumeSlider
            objectName: "volumeSlider"
            Layout.preferredWidth: 84; Layout.preferredHeight: 32
            from: 0; to: 1; stepSize: 0.01; value: deck.controller.volume
            enabled: deck.controller.available && deck.controller.canSetVolume
            Accessible.name: "Volumen"; Accessible.description: Math.round(value * 100) + " por ciento"
            onMoved: deck.controller.setVolume(value)
            background: Rectangle {
                x: volumeSlider.leftPadding; y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - 2
                width: volumeSlider.availableWidth; height: 4; radius: 2; color: "#34233f"
                Rectangle { width: parent.width * volumeSlider.visualPosition; height: parent.height; radius: 2; color: volumeSlider.enabled ? "#a786c5" : "#6e5c7e" }
            }
            handle: Rectangle {
                x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                width: 10; height: 10; radius: 5; color: volumeSlider.enabled ? "#d5b8ef" : "#6e5c7e"
                border.color: volumeSlider.activeFocus ? deck.green : color; border.width: 2
            }
            HoverHandler { cursorShape: volumeSlider.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
        }
        Text { text: Math.round(volumeSlider.value * 100) + "%"; font.family: "monospace"; font.pixelSize: 9; color: deck.muted; textFormat: Text.PlainText }
        Text {
            Layout.fillWidth: true
            text: !deck.detailOpen && deck.controller.available ? deck.controller.playerName : ""
            color: deck.muted; font.pixelSize: 9; elide: Text.ElideRight
            horizontalAlignment: Text.AlignRight; textFormat: Text.PlainText
        }
        DeckButton {
            objectName: "openPlayerButton"; symbol: "open";
            label: deck.controller.available ? "Abrir " + deck.controller.playerName : "Abrir Spotifast"
            onClicked: deck.controller.openPlayer()
        }
    }

    Rectangle {
        x: 14; y: height > 0 ? trackRow.y + trackRow.height + 82 : 0
        width: parent.width - 28; height: deck.detailOpen ? 1 : 0
        visible: deck.detailOpen; color: "#35233f"
    }
    RowLayout {
        x: 14; y: trackRow.y + trackRow.height + 92
        width: parent.width - 28; height: 36; spacing: 8
        visible: deck.detailOpen
        Text {
            Layout.fillWidth: true
            text: deck.controller.playerName || "Esperando reproductor"
            color: deck.muted; font.pixelSize: 11; elide: Text.ElideRight; textFormat: Text.PlainText
        }
        DeckButton {
            objectName: "shuffleButton"; symbol: "shuffle"
            visible: deck.controller.canShuffle
            label: deck.controller.shuffle ? "Desactivar aleatorio" : "Activar aleatorio"
            highlightedState: deck.controller.shuffle
            enabled: deck.controller.available && deck.controller.canShuffle
            onClicked: deck.controller.toggleShuffle()
        }
        DeckButton {
            objectName: "repeatButton"; symbol: deck.controller.repeatMode === 1 ? "repeatOne" : "repeat"
            visible: deck.controller.canRepeat
            label: deck.controller.repeatMode === 1 ? "Repetir pista" : deck.controller.repeatMode === 2 ? "Repetir lista" : "Repetición desactivada"
            highlightedState: deck.controller.repeatMode !== 0
            enabled: deck.controller.available && deck.controller.canRepeat
            onClicked: deck.controller.cycleRepeat()
        }
    }
}
