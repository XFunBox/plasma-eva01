import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: deck
    objectName: "nervDeck"
    required property var controller
    property bool detailOpen: false
    property var audioLevels: [0, 0]
    property bool audioLevelsAvailable: false
    signal detailToggled(bool expanded)
    readonly property bool hasPlayers: controller.players && controller.players.length > 1
    readonly property int selectorSpace: hasPlayers ? 40 : 0
    readonly property color green: "#b7ff3c"
    readonly property color muted: "#a29ba9"
    readonly property string fallbackArt: Qt.resolvedUrl("../images/cover-fallback.svg")
    readonly property int coverSize: width < 400 ? 92 : 116
    implicitWidth: 440
    implicitHeight: (detailOpen ? 346 : 260) + selectorSpace
    Accessible.name: "NERV Deck, controles de música"

    function timeLabel(ms) {
        const seconds = Math.max(0, Math.floor(Number(ms || 0) / 1000));
        return Math.floor(seconds / 60) + ":" + (seconds % 60 < 10 ? "0" : "") + seconds % 60;
    }

    Rectangle {
        anchors.fill: parent
        radius: 13; color: "#101213"; border.color: "#8354a4"; border.width: 1
        Rectangle { anchors.fill: parent; anchors.margins: 2; radius: 11; color: "transparent"; border.color: "#1e1d23" }
    }
    Rectangle { x: 1; y: 38; width: parent.width - 2; height: 1; color: "#303033" }
    RowLayout {
        x: 16; y: 6; width: parent.width - 28; height: 28
        spacing: 8
        Text { text: "NERV DECK"; color: "#b786d3"; font.pixelSize: 10; font.letterSpacing: 4; textFormat: Text.PlainText }
        Text {
            Layout.fillWidth: true
            text: !deck.controller.available ? "EN ESPERA" : deck.controller.playing ? "PLAY" : "PAUSA"
            color: deck.muted; font.family: "monospace"; font.pixelSize: 8
            horizontalAlignment: Text.AlignRight; textFormat: Text.PlainText
        }
        DeckButton {
            objectName: "toggleDetails"
            implicitWidth: 28; implicitHeight: 28
            symbol: deck.detailOpen ? "collapse" : "expand"
            label: deck.detailOpen ? "Ocultar detalles" : "Mostrar detalles"
            onClicked: { deck.detailOpen = !deck.detailOpen; deck.detailToggled(deck.detailOpen); }
        }
    }
    ComboBox {
        id: playerSelector
        objectName: "playerSelector"
        x: 16; y: 46; width: parent.width - 32; height: 32
        visible: deck.hasPlayers
        model: ["Automático"].concat((deck.controller.players || []).map(function(player) { return String(player.label || "Reproductor"); }))
        currentIndex: deck.controller.selectedPlayerIndex + 1
        onActivated: function(index) { deck.controller.selectPlayer(index - 1); }
        Accessible.name: "Reproductor de música"
        font.pixelSize: 11
        palette.button: "#19181d"; palette.buttonText: "#eee9f7"; palette.text: "#eee9f7"
        palette.base: "#19181d"; palette.highlight: "#513267"; palette.highlightedText: "#b7ff3c"
        background: Rectangle { color: "#19181d"; border.color: playerSelector.activeFocus ? deck.green : "#49305e"; radius: 3 }
    }
    Rectangle {
        id: coverFrame
        x: 16; y: 48 + deck.selectorSpace
        width: deck.coverSize; height: 116
        radius: 5; color: "#08090a"; border.color: "#454048"
        Image {
            id: cover
            anchors.fill: parent; anchors.margins: 3
            asynchronous: true; fillMode: Image.PreserveAspectCrop
            source: deck.controller.artUrl || deck.fallbackArt
            sourceSize.width: 256; sourceSize.height: 256
            visible: status === Image.Ready
            Accessible.ignored: true
        }
        Image {
            anchors.fill: parent; anchors.margins: 3
            source: deck.fallbackArt; fillMode: Image.PreserveAspectCrop
            visible: cover.status !== Image.Ready
            Accessible.ignored: true
        }
    }
    Item {
        id: information
        x: coverFrame.x + coverFrame.width + 16; y: coverFrame.y
        width: parent.width - x - 16; height: 116
        Text {
            id: trackTitle
            objectName: "trackTitle"
            width: parent.width; y: 1
            text: deck.controller.title || (deck.controller.available ? "Sin título" : "Tu música, aquí")
            color: deck.green; font.pixelSize: 19; font.weight: Font.DemiBold
            elide: Text.ElideRight; textFormat: Text.PlainText
            Accessible.name: text
            ToolTip.text: text; ToolTip.visible: titleHover.hovered && truncated; ToolTip.delay: 700
            HoverHandler { id: titleHover }
        }
        Text {
            y: 28; width: parent.width
            text: deck.controller.artist || (deck.controller.available ? "Artista desconocido" : "Abre tu reproductor")
            color: "#a0cb76"; font.pixelSize: 10; font.letterSpacing: 1.3
            elide: Text.ElideRight; textFormat: Text.PlainText
        }
        Row {
            y: 53; width: parent.width; height: 58; spacing: 8
            AnalogMeter { width: (parent.width - 8) / 2; height: parent.height; channel: "L"; level: Number(deck.audioLevels[0] || 0); signalAvailable: deck.audioLevelsAvailable }
            AnalogMeter { width: (parent.width - 8) / 2; height: parent.height; channel: "R"; level: Number(deck.audioLevels[1] || 0); signalAvailable: deck.audioLevelsAvailable }
        }
    }
    RowLayout {
        x: 16; y: 168 + deck.selectorSpace
        width: parent.width - 32; height: 28; spacing: 8
        Text { text: deck.timeLabel(seekSlider.pressed ? seekSlider.value : deck.controller.positionMs); color: deck.muted; font.family: "monospace"; font.pixelSize: 9; textFormat: Text.PlainText }
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
                x: seekSlider.leftPadding; y: seekSlider.topPadding + seekSlider.availableHeight / 2 - 1.5
                width: seekSlider.availableWidth; height: 3; radius: 2; color: "#333c2c"
                Rectangle { width: parent.width * seekSlider.visualPosition; height: parent.height; radius: 2; color: seekSlider.enabled ? "#a5d67b" : "#6e5c7e" }
            }
            handle: Rectangle {
                x: seekSlider.leftPadding + seekSlider.visualPosition * (seekSlider.availableWidth - width)
                y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                width: 8; height: 8; radius: 4; color: seekSlider.enabled ? deck.green : "#6e5c7e"
                border.color: seekSlider.activeFocus ? "#ffffff" : color; border.width: 2
            }
            HoverHandler { cursorShape: seekSlider.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
        }
        Text { text: deck.timeLabel(deck.controller.durationMs); color: deck.muted; font.family: "monospace"; font.pixelSize: 9; textFormat: Text.PlainText }
    }
    Text {
        x: 16; y: 210 + deck.selectorSpace; width: 70
        text: deck.audioLevelsAvailable ? "STEREO\nSIGNAL" : "VU\nSTANDBY"
        color: deck.audioLevelsAvailable ? "#b99058" : "#999287"
        font.family: "monospace"; font.pixelSize: 8; lineHeight: 1.4; textFormat: Text.PlainText
    }
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.horizontalCenterOffset: -12
        y: 201 + deck.selectorSpace; height: 48; spacing: 12
        DeckButton {
            objectName: "previousButton"; symbol: "previous"; label: "Pista anterior"; round: true
            y: 5; implicitWidth: 38; implicitHeight: 38
            enabled: deck.controller.available && deck.controller.canPrevious
            onClicked: deck.controller.previous()
        }
        DeckButton {
            objectName: "playPauseButton"; symbol: deck.controller.playing ? "pause" : "play"; round: true
            label: deck.controller.playing ? "Pausar" : "Reproducir"; primary: true
            implicitWidth: 48; implicitHeight: 48; padding: 13
            enabled: deck.controller.available && deck.controller.canPlayPause
            onClicked: deck.controller.playPause()
        }
        DeckButton {
            objectName: "nextButton"; symbol: "next"; label: "Pista siguiente"; round: true
            y: 5; implicitWidth: 38; implicitHeight: 38
            enabled: deck.controller.available && deck.controller.canNext
            onClicked: deck.controller.next()
        }
    }
    VolumeDial {
        id: volumeDial
        objectName: "volumeSlider"
        x: parent.width - 81; y: 190 + deck.selectorSpace
        width: 58; height: 58; value: deck.controller.volume
        enabled: deck.controller.available && deck.controller.canSetVolume
        onMoved: deck.controller.setVolume(value)
    }
    Text {
        x: volumeDial.x - 4; y: volumeDial.y + 59; width: volumeDial.width + 8
        text: "VOLUME"; color: deck.muted; font.pixelSize: 7; font.letterSpacing: 1.5
        horizontalAlignment: Text.AlignHCenter; textFormat: Text.PlainText
    }
    Button {
        objectName: "emptyOpenPlayerButton"
        x: 16; y: coverFrame.y + 78; width: coverFrame.width; height: 34
        visible: !deck.controller.available
        text: "Abrir Spotifast"; focusPolicy: Qt.StrongFocus; Accessible.name: text
        contentItem: Text { text: parent.text; color: deck.green; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; textFormat: Text.PlainText }
        background: Rectangle { color: parent.down ? "#302039" : "#111714"; border.color: parent.activeFocus ? deck.green : "#60417c"; radius: 3 }
        onClicked: deck.controller.openPlayer()
    }
    Rectangle { x: 16; y: 269 + deck.selectorSpace; width: parent.width - 32; height: 1; color: "#343037"; visible: deck.detailOpen }
    ColumnLayout {
        x: 16; y: 280 + deck.selectorSpace; width: parent.width - 32; height: 54; spacing: 4
        visible: deck.detailOpen
        Text {
            Layout.fillWidth: true
            text: deck.controller.album || (deck.controller.available ? "Álbum sin indicar" : "Listo para conectar")
            color: deck.muted; font.pixelSize: 10; elide: Text.ElideRight; textFormat: Text.PlainText
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Text { Layout.fillWidth: true; text: deck.controller.playerName || "Esperando reproductor"; color: deck.muted; font.pixelSize: 10; elide: Text.ElideRight; textFormat: Text.PlainText }
            DeckButton {
                objectName: "shuffleButton"; symbol: "shuffle"; implicitWidth: 30; implicitHeight: 30
                visible: deck.controller.canShuffle
                label: deck.controller.shuffle ? "Desactivar aleatorio" : "Activar aleatorio"
                highlightedState: deck.controller.shuffle
                enabled: deck.controller.available && deck.controller.canShuffle
                onClicked: deck.controller.toggleShuffle()
            }
            DeckButton {
                objectName: "repeatButton"; symbol: deck.controller.repeatMode === 1 ? "repeatOne" : "repeat"; implicitWidth: 30; implicitHeight: 30
                visible: deck.controller.canRepeat
                label: deck.controller.repeatMode === 1 ? "Repetir pista" : deck.controller.repeatMode === 2 ? "Repetir lista" : "Repetición desactivada"
                highlightedState: deck.controller.repeatMode !== 0
                enabled: deck.controller.available && deck.controller.canRepeat
                onClicked: deck.controller.cycleRepeat()
            }
            DeckButton {
                objectName: "openPlayerButton"; symbol: "open"; implicitWidth: 30; implicitHeight: 30
                label: deck.controller.available ? "Abrir " + deck.controller.playerName : "Abrir Spotifast"
                onClicked: deck.controller.openPlayer()
            }
        }
    }
}
