#!/usr/bin/python3
"""Cierra únicamente los paneles dedicados, sin afectar otras ventanas."""
import os, signal
from Xlib import X, display
d = display.Display()
r = d.screen().root
a = d.intern_atom
p = r.get_full_property(a('_NET_CLIENT_LIST'), X.AnyPropertyType)
for i in p.value if p is not None else []:
    w = d.create_resource_object('window', int(i))
    if (w.get_wm_class() or ('', ''))[0].startswith('eva01-desktop-'):
        pid = w.get_full_property(a('_NET_WM_PID'), X.AnyPropertyType)
        if pid is not None:
            os.kill(int(pid.value[0]), signal.SIGTERM)
d.sync()
