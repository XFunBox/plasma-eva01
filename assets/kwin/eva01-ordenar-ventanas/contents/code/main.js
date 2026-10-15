/* KWin 6: distribución a petición, sin mover ventanas entre monitores. */
var evaSnapshots = {};

function evaRect(rect) {
    return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
}

function evaVisible(window) {
    if (!window.normalWindow || window.minimized || window.fullScreen ||
        window.hidden || window.skipTaskbar || !window.moveable || !window.resizeable) {
        return false;
    }
    if (/coucou/i.test(String(window.resourceClass) + " " + String(window.desktopFileName))) {
        return false;
    }
    var desktop = typeof workspace.currentDesktopForScreen === "function"
        ? workspace.currentDesktopForScreen(window.output) : workspace.currentDesktop;
    var desktops = window.desktops || [];
    if (!window.onAllDesktops && desktops.indexOf(desktop) < 0) {
        return false;
    }
    var activities = window.activities || [];
    return activities.length === 0 || activities.indexOf(workspace.currentActivity) >= 0;
}

function evaSlots(area, count) {
    if (count === 0) return [];
    var gap = 8;
    var x = Math.round(area.x) + gap;
    var y = Math.round(area.y) + gap;
    var width = Math.max(1, Math.floor(area.width) - gap * 2);
    var height = Math.max(1, Math.floor(area.height) - gap * 2);
    var slots = [];
    if (count === 3 && width >= height) {
        var left = Math.floor((width - gap) / 2);
        var top = Math.floor((height - gap) / 2);
        return [
            {x:x, y:y, width:left, height:height},
            {x:x+left+gap, y:y, width:width-left-gap, height:top},
            {x:x+left+gap, y:y+top+gap, width:width-left-gap, height:height-top-gap}
        ];
    }
    var columns = count === 1 ? 1 : count === 2 ? (width >= height ? 2 : 1)
        : Math.min(count, Math.max(1, Math.ceil(Math.sqrt(count * width / height / 1.6))));
    var rows = Math.ceil(count / columns);
    var rowHeight = (height - gap * (rows - 1)) / rows;
    for (var row = 0; row < rows; row++) {
        var inRow = Math.min(columns, count - row * columns);
        var cellWidth = (width - gap * (inRow - 1)) / inRow;
        for (var col = 0; col < inRow; col++) {
            var leftEdge = Math.round(x + col * (cellWidth + gap));
            var topEdge = Math.round(y + row * (rowHeight + gap));
            slots.push({x:leftEdge, y:topEdge,
                width:Math.max(1, Math.round(x + col * (cellWidth + gap) + cellWidth) - leftEdge),
                height:Math.max(1, Math.round(y + row * (rowHeight + gap) + rowHeight) - topEdge)});
        }
    }
    return slots;
}

function evaArrange() {
    var all = workspace.windowList();
    var groups = {};
    var eligible = all.filter(evaVisible);
    eligible.sort(function(a, b) {
        if (a === workspace.activeWindow) return -1;
        if (b === workspace.activeWindow) return 1;
        return a.frameGeometry.y - b.frameGeometry.y || a.frameGeometry.x - b.frameGeometry.x;
    });
    for (var i = 0; i < eligible.length; i++) {
        var window = eligible[i];
        var key = String(window.output.name);
        if (!groups[key]) groups[key] = [];
        groups[key].push(window);
    }
    var next = {};
    var arranged = 0;
    for (var screen in groups) {
        var windows = groups[screen];
        var area = workspace.clientArea(KWin.PlacementArea, windows[0]);
        var slots = evaSlots(area, windows.length);
        for (var j = 0; j < windows.length; j++) {
            var target = windows[j];
            var id = String(target.internalId);
            var context = String(workspace.currentDesktop.id) + ":" + workspace.currentActivity;
            next[id] = {geometry:evaRect(target.frameGeometry),
                maximized:Number(target.maximizeMode) || 0,
                tile:target.tile || null, context:context};
            target.tile = null;
            target.setMaximize(false, false);
            target.frameGeometry = slots[j];
            arranged++;
        }
    }
    // Un segundo ordenado no sustituye la distribución que se desea recuperar.
    for (var saved in next) {
        if (!evaSnapshots[saved] || evaSnapshots[saved].context !== next[saved].context) {
            evaSnapshots[saved] = next[saved];
        }
    }
    print("EVA01: ordenadas " + arranged + " ventanas");
}

function evaRestore() {
    var all = workspace.windowList();
    var restored = 0;
    var context = String(workspace.currentDesktop.id) + ":" + workspace.currentActivity;
    for (var i = 0; i < all.length; i++) {
        var window = all[i];
        var id = String(window.internalId);
        var saved = evaSnapshots[id];
        if (!saved || saved.context !== context || !evaVisible(window)) continue;
        window.tile = null;
        window.setMaximize(false, false);
        window.frameGeometry = saved.geometry;
        window.setMaximize((saved.maximized & 1) !== 0, (saved.maximized & 2) !== 0);
        if (saved.tile) {
            try { window.tile = saved.tile; } catch (error) { /* Zona eliminada. */ }
        }
        delete evaSnapshots[id];
        restored++;
    }
    print("EVA01: restauradas " + restored + " ventanas");
}

workspace.windowRemoved.connect(function(window) {
    delete evaSnapshots[String(window.internalId)];
});
registerShortcut("EVA01ArrangeWindows", "EVA-01: ordenar ventanas", "Meta+O", evaArrange);
registerShortcut("EVA01RestoreWindows", "EVA-01: restaurar ventanas", "Meta+Shift+O", evaRestore);
