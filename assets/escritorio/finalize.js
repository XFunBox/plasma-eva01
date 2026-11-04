workspace.windowList().forEach(function(w) {
    if (String(w.resourceClass).indexOf('eva01-desktop-') !== 0) return;
    w.desktops = [];
    w.noBorder = true;
    w.skipTaskbar = true;
    w.skipPager = true;
    w.skipSwitcher = true;
    w.minimized = false;
    w.setMaximize(false, false);
    w.keepBelow = false;
    workspace.raiseWindow(w);
    w.keepBelow = true;
    print('EVA_WIDGET_FINAL '+JSON.stringify({cls:String(w.resourceClass),all:w.onAllDesktops,desktop:w.desktopWindow,border:w.noBorder,skip:w.skipSwitcher,output:w.output.name}));
});
