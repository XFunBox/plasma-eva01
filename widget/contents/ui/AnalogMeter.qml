import QtQuick

Rectangle {
    id: meter
    property real level: 0
    property string channel: "L"
    property bool signalAvailable: false
    color: "#080909"
    radius: 4
    border.color: "#353638"
    Accessible.role: Accessible.Indicator
    Accessible.name: "Nivel de audio " + channel
    Accessible.description: signalAvailable ? Math.round(level * 100) + " por ciento" : "Sin señal de nivel de audio"
    Rectangle {
        anchors.fill: parent; anchors.margins: 3; radius: 2
        gradient: Gradient {
            GradientStop { position: 0; color: "#292217" }
            GradientStop { position: 1; color: "#100e0a" }
        }
    }
    Canvas {
        id: face
        anchors.fill: parent; anchors.margins: 5
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections {
            target: meter
            function onLevelChanged() { face.requestPaint() }
            function onSignalAvailableChanged() { face.requestPaint() }
        }
        onPaint: {
            const c = getContext("2d");
            c.reset();
            const cx = width / 2, r = width * 0.42, cy = height + r * 0.4 + 7;
            const start = -2.42, end = -0.72;
            c.lineWidth = 1;
            c.beginPath(); c.arc(cx, cy, r, start, end);
            c.strokeStyle = "#cfa25d"; c.stroke();
            for (let i = 0; i <= 16; ++i) {
                const a = start + (end - start) * i / 16;
                const outer = r + (i % 4 === 0 ? 8 : 5);
                c.beginPath(); c.moveTo(cx + Math.cos(a) * (r - 2), cy + Math.sin(a) * (r - 2));
                c.lineTo(cx + Math.cos(a) * outer, cy + Math.sin(a) * outer);
                c.strokeStyle = i >= 13 ? "#ce6147" : "#dfb773"; c.stroke();
            }
            c.font = "8px monospace"; c.textAlign = "center"; c.fillStyle = "#dfb773";
            const labels = ["−20", "−10", "−3", "0", "+3"];
            for (let j = 0; j < labels.length; ++j) {
                const a = start + (end - start) * j / 4;
                c.fillText(labels[j], cx + Math.cos(a) * (r + 17), cy + Math.sin(a) * (r + 17) + 3);
            }
            c.fillStyle = "#b99152"; c.font = "9px monospace";
            c.fillText("VU · " + meter.channel, cx, height - 4);
            const value = meter.signalAvailable ? Math.max(0, Math.min(1, meter.level)) : 0;
            const angle = start + (end - start) * value;
            c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + Math.cos(angle) * (r + 4), cy + Math.sin(angle) * (r + 4));
            c.strokeStyle = "#f0c47c"; c.lineWidth = 1.5; c.stroke();
        }
    }
}
