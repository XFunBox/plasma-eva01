import QtQuick
import org.kde.taskmanager as TaskManager

Item {
    id: launcher
    required property var controller
    property var launcherModel: null
    Component {
        id: launcherFactory
        TaskManager.TasksModel { launcherList: ["applications:eva-01-audio.desktop"] }
    }
    Connections {
        target: launcher.controller
        function onLaunchRequested() {
            if (!launcher.launcherModel) launcher.launcherModel = launcherFactory.createObject(launcher);
            Qt.callLater(function() {
                const model = launcher.launcherModel;
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
}
