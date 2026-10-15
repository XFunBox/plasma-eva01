import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid

PlasmoidItem {
    id: applet
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    preferredRepresentation: fullRepresentation
    toolTipMainText: "NERV Deck"
    toolTipSubText: media.available ? media.artist + " · " + media.title : "Tu consola de Spotify y Spotifast"
    toolTipTextFormat: Text.PlainText
    MediaController { id: media }
    PlayerLauncher { controller: media }
    fullRepresentation: Deck {
        controller: media
        Layout.minimumWidth: 360
        Layout.minimumHeight: implicitHeight
        Layout.preferredWidth: implicitWidth
        Layout.preferredHeight: implicitHeight
        Layout.maximumHeight: implicitHeight
    }
}
