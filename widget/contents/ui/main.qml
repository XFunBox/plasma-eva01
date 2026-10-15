import QtQuick
import QtQuick.Layouts
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasmoid
import org.kde.taskmanager as TaskManager

PlasmoidItem {
    id: applet
    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground
    preferredRepresentation: fullRepresentation
    toolTipMainText: "NERV Deck"
    toolTipSubText: media.available ? media.artist + " · " + media.title : "Tu consola de Spotify y Spotifast"
    toolTipTextFormat: Text.PlainText
    MediaController { id: media }
    property var launcherModel: null
    Component {
        id: launcherFactory
        TaskManager.TasksModel { launcherList: ["applications:eva-01-audio.desktop"] }
    }
    Connections {
        target: media
        function onLaunchRequested() {
            if (!applet.launcherModel) applet.launcherModel = launcherFactory.createObject(applet);
            Qt.callLater(function() {
                const model = applet.launcherModel;
                for (let row = 0; row < model.rowCount(); ++row) {
                    const index = model.index(row, 0);
                    const url = String(model.data(index, TaskManager.AbstractTasksModel.LauncherUrlWithoutIcon));
                    if (url === "applications:eva-01-audio.desktop") {
                        model.requestNewInstance(index);
                        return;
                    }
                }
            });
        }
    }
    fullRepresentation: Deck {
        controller: media
        Layout.minimumWidth: 360
        Layout.minimumHeight: implicitHeight
        Layout.preferredWidth: implicitWidth
        Layout.preferredHeight: implicitHeight
        Layout.maximumHeight: implicitHeight
    }
}
