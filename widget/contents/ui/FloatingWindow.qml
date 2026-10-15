import QtQuick
import QtQuick.Window
import org.kde.kwindowsystem as KWindow

Window {
    id: window
    visible: false
    title: "NERV Deck"
    color: "transparent"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
    width: deck.implicitWidth
    height: deck.implicitHeight
    minimumWidth: deck.implicitWidth
    maximumWidth: deck.implicitWidth
    minimumHeight: deck.implicitHeight
    maximumHeight: deck.implicitHeight
    function showWithToken(token) {
        if (token) KWindow.KWindowSystem.setCurrentXdgActivationToken(token);
        show();
        raise();
        Qt.callLater(function() {
            KWindow.KWindowSystem.activateWindow(window);
            window.requestActivate();
            deck.forceActiveFocus();
        });
    }
    MediaController { id: media }
    PlayerLauncher { controller: media }
    Deck {
        id: deck
        anchors.fill: parent
        controller: media
        focus: true
        Keys.onEscapePressed: window.hide()
    }
    MouseArea {
        x: 8; y: 2; width: parent.width - 100; height: 32
        acceptedButtons: Qt.LeftButton
        onPressed: window.startSystemMove()
        cursorShape: Qt.SizeAllCursor
    }
}
