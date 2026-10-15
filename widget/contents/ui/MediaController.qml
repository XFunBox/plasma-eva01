import QtQuick
import QtQml.Models
import org.kde.plasma.private.mpris as Mpris

// API nativa de Plasma 6.6: libkmpris/playercontainer.h y mpris2model.h.
// https://invent.kde.org/plasma/plasma-workspace/-/tree/Plasma/6.6/libkmpris
Item {
    id: root
    visible: false
    signal launchRequested()
    property var entries: []
    property string selectedId: ""
    readonly property var players: entries.map(function(e) { return {id: e.id, label: e.label}; })
    readonly property int selectedPlayerIndex: entries.findIndex(function(e) { return e.id === selectedId; })
    readonly property var currentEntry: {
        if (selectedPlayerIndex >= 0) return entries[selectedPlayerIndex];
        for (let e of entries) {
            if (e.player && e.player.playbackStatus === Mpris.PlaybackStatus.Playing) return e;
        }
        return entries.length ? entries[0] : null;
    }
    readonly property var currentPlayer: currentEntry ? currentEntry.player : null
    readonly property bool available: currentPlayer !== null
    readonly property string title: available ? (currentPlayer.track || "Sin título") : "En espera"
    readonly property string artist: available ? (currentPlayer.artist || playerName) : "Tu música, cuando quieras"
    readonly property string album: available ? currentPlayer.album : ""
    readonly property string playerName: currentEntry ? currentEntry.label : "Spotify · Spotifast"
    readonly property string artUrl: {
        const url = available ? currentPlayer.artUrl : "";
        return /^(https?:\/\/|file:\/\/\/)/i.test(url) ? url : "";
    }
    readonly property bool playing: available && currentPlayer.playbackStatus === Mpris.PlaybackStatus.Playing
    readonly property real durationMs: available ? finite(currentPlayer.length / 1000, 0) : 0
    property real positionMs: 0
    readonly property real volume: available ? clamp(finite(currentPlayer.volume, 0), 0, 1) : 0
    readonly property bool canPlayPause: available && currentPlayer.canControl
        && (playing ? currentPlayer.canPause : currentPlayer.canPlay)
    readonly property bool canPrevious: available && currentPlayer.canGoPrevious
    readonly property bool canNext: available && currentPlayer.canGoNext
    readonly property bool canSeek: available && currentPlayer.canSeek && durationMs > 0
    readonly property bool canSetVolume: available && currentPlayer.canControl
    readonly property bool canShuffle: available && currentPlayer.canControl
        && currentPlayer.shuffle !== Mpris.ShuffleStatus.Unknown
    readonly property bool canRepeat: available && currentPlayer.canControl
        && currentPlayer.loopStatus !== Mpris.LoopStatus.Unknown
    readonly property bool shuffle: available && currentPlayer.shuffle === Mpris.ShuffleStatus.On
    readonly property int repeatMode: !available ? 0
        : currentPlayer.loopStatus === Mpris.LoopStatus.Track ? 1
        : currentPlayer.loopStatus === Mpris.LoopStatus.Playlist ? 2 : 0

    function finite(value, fallback) { return Number.isFinite(Number(value)) ? Math.max(0, Number(value)) : fallback; }
    function clamp(value, low, high) { return Math.max(low, Math.min(high, value)); }
    function syncPosition() {
        const player = currentPlayer;
        positionMs = player ? clamp(finite(player.position / 1000, 0), 0, finite(player.length / 1000, 0) || Infinity) : 0;
    }
    function refreshPosition() {
        if (currentPlayer) currentPlayer.updatePosition();
        syncPosition();
    }
    function rebuildPlayers() {
        let result = [];
        for (let i = 1; i < delegates.count; ++i) {
            const item = delegates.objectAt(i);
            if (!item || !item.container) continue;
            const entry = (item.desktopEntry || "").toLowerCase();
            const identity = (item.identity || "").toLowerCase();
            if (!/spotify|spotifast|eva-01-audio/.test(entry)
                && !/^(spotify|spotifast|eva-01 audio)$/.test(identity)) continue;
            result.push({id: entry + ":" + item.container.instancePid + ":" + item.identity,
                         label: item.identity || item.desktopEntry, player: item.container});
        }
        entries = result;
        if (selectedId && !result.some(function(e) { return e.id === selectedId; })) selectedId = "";
        syncPosition();
    }
    function selectPlayer(index) {
        selectedId = Number.isInteger(index) && index >= 0 && index < entries.length ? entries[index].id : "";
    }
    function playPause() { if (canPlayPause) currentPlayer.PlayPause(); }
    function previous() { if (canPrevious) currentPlayer.Previous(); }
    function next() { if (canNext) currentPlayer.Next(); }
    function seekTo(ms) {
        if (canSeek && Number.isFinite(Number(ms))) currentPlayer.position = Math.round(clamp(Number(ms), 0, durationMs) * 1000);
    }
    function setVolume(value) {
        if (canSetVolume && Number.isFinite(Number(value))) currentPlayer.volume = clamp(Number(value), 0, 1);
    }
    function toggleShuffle() {
        if (canShuffle) currentPlayer.shuffle = shuffle ? Mpris.ShuffleStatus.Off : Mpris.ShuffleStatus.On;
    }
    function cycleRepeat() {
        if (canRepeat) currentPlayer.loopStatus = repeatMode === 0 ? Mpris.LoopStatus.Track
            : repeatMode === 1 ? Mpris.LoopStatus.Playlist : Mpris.LoopStatus.None;
    }
    function openPlayer() {
        if (available && currentPlayer.canRaise) currentPlayer.Raise();
        else launchRequested();
    }
    onCurrentPlayerChanged: refreshPosition()
    onDurationMsChanged: syncPosition()
    Mpris.Mpris2Model { id: sources }
    Instantiator {
        id: delegates
        model: sources
        delegate: QtObject {
            required property int index
            required property var container
            required property string identity
            required property string desktopEntry
            onContainerChanged: Qt.callLater(root.rebuildPlayers)
            onIdentityChanged: Qt.callLater(root.rebuildPlayers)
            onDesktopEntryChanged: Qt.callLater(root.rebuildPlayers)
        }
        onObjectAdded: Qt.callLater(root.rebuildPlayers)
        onObjectRemoved: Qt.callLater(root.rebuildPlayers)
    }
    Connections {
        target: root.currentPlayer
        function onPositionChanged() { root.syncPosition(); }
        function onPlaybackStatusChanged() { root.refreshPosition(); }
    }
    Timer {
        interval: 500
        repeat: true
        running: root.playing
        onTriggered: root.refreshPosition()
    }
}
