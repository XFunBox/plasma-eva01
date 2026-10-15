import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string symbol: "play"
    property string label: ""
    property bool primary: false
    property bool highlightedState: false
    readonly property color ink: !enabled ? "#696477" : primary ? "#08080b" : highlightedState ? "#b7ff3c" : "#eee9f7"
    implicitWidth: 36
    implicitHeight: 36
    padding: 8
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: label
    ToolTip.text: label
    ToolTip.visible: hovered
    ToolTip.delay: 650
    HoverHandler { cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor }
    background: Rectangle {
        color: control.primary ? (control.down ? "#93d421" : "#b7ff3c") : control.down ? "#4b3165" : control.hovered ? "#30203f" : "#191321"
        border.color: control.activeFocus ? "#eee9f7" : control.highlightedState ? "#b7ff3c" : "#49305e"
        border.width: control.activeFocus ? 2 : 1
        radius: 3
        opacity: control.enabled ? 1 : 0.6
        Behavior on color { ColorAnimation { duration: 100 } }
    }
    contentItem: Canvas {
        id: glyph
        implicitWidth: 20
        implicitHeight: 20
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections {
            target: control
            function onInkChanged() { glyph.requestPaint() }
            function onSymbolChanged() { glyph.requestPaint() }
        }
        onPaint: {
            const c = getContext("2d");
            c.reset(); c.scale(width / 20, height / 20);
            c.strokeStyle = control.ink; c.fillStyle = control.ink;
            c.lineWidth = 1.7; c.lineCap = "round"; c.lineJoin = "round";
            const s = control.symbol;
            if (s === "play") {
                c.beginPath(); c.moveTo(6, 3); c.lineTo(16, 10); c.lineTo(6, 17); c.closePath(); c.fill();
            } else if (s === "pause") {
                c.fillRect(5, 3, 3, 14); c.fillRect(12, 3, 3, 14);
            } else if (s === "previous" || s === "next") {
                if (s === "previous") { c.translate(20, 0); c.scale(-1, 1); }
                c.beginPath(); c.moveTo(4, 4); c.lineTo(13, 10); c.lineTo(4, 16); c.closePath(); c.fill();
                c.fillRect(14, 4, 2, 12);
            } else if (s === "expand" || s === "collapse") {
                c.beginPath(); c.moveTo(4, s === "expand" ? 7 : 13); c.lineTo(10, s === "expand" ? 13 : 7); c.lineTo(16, s === "expand" ? 7 : 13); c.stroke();
            } else if (s === "open") {
                c.beginPath(); c.moveTo(10, 4); c.lineTo(16, 4); c.lineTo(16, 10); c.moveTo(16, 4); c.lineTo(8, 12);
                c.moveTo(7, 4); c.lineTo(4, 4); c.lineTo(4, 16); c.lineTo(16, 16); c.lineTo(16, 13); c.stroke();
            } else if (s === "shuffle") {
                c.beginPath(); c.moveTo(3, 5); c.lineTo(6, 5); c.lineTo(13, 15); c.lineTo(17, 15);
                c.moveTo(14, 12); c.lineTo(17, 15); c.lineTo(14, 18);
                c.moveTo(3, 15); c.lineTo(6, 15); c.lineTo(13, 5); c.lineTo(17, 5);
                c.moveTo(14, 2); c.lineTo(17, 5); c.lineTo(14, 8); c.stroke();
            } else if (s === "repeat" || s === "repeatOne") {
                c.beginPath(); c.moveTo(4, 8); c.lineTo(4, 5); c.lineTo(16, 5); c.lineTo(13, 2);
                c.moveTo(16, 5); c.lineTo(13, 8); c.moveTo(16, 12); c.lineTo(16, 15); c.lineTo(4, 15); c.lineTo(7, 18);
                c.moveTo(4, 15); c.lineTo(7, 12); c.stroke();
                if (s === "repeatOne") { c.font = "bold 8px sans-serif"; c.fillText("1", 8, 13); }
            }
        }
    }
}
