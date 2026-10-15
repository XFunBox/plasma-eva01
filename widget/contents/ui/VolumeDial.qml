import QtQuick
import QtQuick.Controls

Dial {
    id: dial
    implicitWidth: 64
    implicitHeight: 64
    from: 0; to: 1; stepSize: 0.01
    inputMode: Dial.Circular
    focusPolicy: Qt.StrongFocus
    Accessible.name: "Volumen"
    Accessible.description: Math.round(value * 100) + " por ciento"
    ToolTip.text: "Volumen: " + Math.round(value * 100) + "%"
    ToolTip.visible: hovered || pressed
    hoverEnabled: true
    background: Item {
        Repeater {
            model: 21
            Rectangle {
                required property int index
                readonly property real angle: (-140 + index * 14) * Math.PI / 180
                width: 2; height: 2; radius: 1
                x: parent.width / 2 + Math.sin(angle) * (parent.width / 2 - 3) - 1
                y: parent.height / 2 - Math.cos(angle) * (parent.height / 2 - 3) - 1
                color: dial.enabled && index / 20 <= dial.position ? "#a5d67b" : "#424345"
            }
        }
        Rectangle {
            anchors.centerIn: parent
            width: parent.width - 16; height: width; radius: width / 2
            border.color: dial.activeFocus ? "#b7ff3c" : "#55585a"
            border.width: dial.activeFocus ? 2 : 1
            gradient: Gradient {
                GradientStop { position: 0; color: "#373a3b" }
                GradientStop { position: 0.5; color: "#222526" }
                GradientStop { position: 1; color: "#0d0f10" }
            }
            Rectangle {
                anchors.fill: parent; anchors.margins: 3
                radius: width / 2; color: "transparent"; border.color: "#141617"
            }
            Item {
                anchors.fill: parent
                rotation: dial.angle
                Rectangle { width: 2; height: 8; radius: 1; anchors.horizontalCenter: parent.horizontalCenter; y: 5; color: dial.enabled ? "#b7ff3c" : "#696477" }
            }
        }
    }
    handle: Item {}
    HoverHandler { cursorShape: dial.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
}
