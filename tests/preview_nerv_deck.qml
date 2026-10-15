import QtQuick
import QtQuick.Window
import "../widget/contents/ui" as Nerv

Window {
    id: preview
    visible: true
    width: deck.implicitWidth + 40
    height: deck.implicitHeight + 40
    color: "#15111d"
    title: "NERV Deck · vista previa"
    QtObject {
        id: model
        property bool available: previewMode !== "idle"
        property string title: available ? "Night Drive // 01" : "En espera"
        property string artist: available ? "After Hours" : "Tu música, cuando quieras"
        property string album: "Signal Sessions"
        property string artUrl: ""
        property string playerName: available ? "EVA-01 Audio" : "Spotify · Spotifast"
        property bool playing: available
        property real positionMs: available ? 63000 : 0
        property real durationMs: available ? 244000 : 0
        property real volume: available ? 0.7 : 0
        property bool canPlayPause: available
        property bool canPrevious: available
        property bool canNext: available
        property bool canSeek: available
        property bool canSetVolume: available
        property bool canShuffle: available
        property bool canRepeat: available
        property bool shuffle: false
        property int repeatMode: 0
        property var players: available ? [{id: "demo", label: "EVA-01 Audio"}] : []
        property int selectedPlayerIndex: -1
        function playPause() { playing = !playing; }
        function previous() { title = "Pista anterior"; }
        function next() { title = "Pista siguiente"; }
        function seekTo(value) { positionMs = value; }
        function setVolume(value) { volume = value; }
        function toggleShuffle() { shuffle = !shuffle; }
        function cycleRepeat() { repeatMode = (repeatMode + 1) % 3; }
        function selectPlayer(index) { selectedPlayerIndex = index; }
        function openPlayer() {}
    }
    Nerv.Deck {
        id: deck
        x: 20; y: 20
        width: implicitWidth; height: implicitHeight
        controller: model
        detailOpen: previewMode === "expanded"
    }
    Timer {
        interval: 450; running: true
        onTriggered: deck.grabToImage(function(result) {
            if (!result.saveToFile(capturePath)) console.error("No se pudo guardar la vista previa");
            Qt.quit();
        });
    }
}
