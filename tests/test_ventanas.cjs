const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// KWin necesita una sesión gráfica; este adaptador permite comprobar sus decisiones.
const desktop = {id: 'uno'};
const area = {x: 0, y: 0, width: 1920, height: 1080};
const screen = {name: 'izquierda'};
function window(id, output = screen, extra = {}) {
    return {
        internalId: id, output, normalWindow: true, minimized: false,
        fullScreen: false, hidden: false, skipTaskbar: false, moveable: true,
        resizeable: true, resourceClass: 'app', desktopFileName: 'app',
        desktops: [desktop], activities: [], frameGeometry: {x: 20, y: 30, width: 600, height: 400},
        maximizeMode: 0, tile: null,
        setMaximize() {}, ...extra
    };
}
const left = window('left');
const right = window('right', {name: 'derecha'});
const excluded = window('coucou', screen, {resourceClass: 'coucou'});
const minimized = window('minimized', screen, {minimized: true});
const hiddenDesktop = window('other', screen, {desktops: [{id: 'dos'}]});
const workspace = {
    currentDesktop: desktop, currentActivity: 'work', activeWindow: left,
    windowList: () => [left, right, excluded, minimized, hiddenDesktop],
    clientArea: (_, w) => ({...area, x: w.output === screen ? 0 : 1920}),
    windowRemoved: {connect() {}}
};
const shortcuts = {};
const context = vm.createContext({workspace, KWin: {PlacementArea: 0}, print() {},
    registerShortcut: (name, _label, _keys, fn) => { shortcuts[name] = fn; }});
vm.runInContext(fs.readFileSync(path.join(__dirname, '../assets/kwin/eva01-ordenar-ventanas/contents/code/main.js'), 'utf8'), context);

// Detecta ventanas perdidas, geometrías negativas y solapamientos en distribuciones normales.
for (const [width, height] of [[1920, 1080], [1080, 1920]]) {
    for (let count = 1; count <= 9; count++) {
        const slots = context.evaSlots({x: -1920, y: 0, width, height}, count);
        assert.equal(slots.length, count);
        for (let i = 0; i < slots.length; i++) {
            const s = slots[i];
            assert(s.width > 0 && s.height > 0);
            assert(s.x >= -1920 && s.y >= 0);
            assert(s.x + s.width <= -1920 + width);
            assert(s.y + s.height <= height);
            for (let j = 0; j < i; j++) {
                const t = slots[j];
                assert(s.x + s.width <= t.x || t.x + t.width <= s.x ||
                    s.y + s.height <= t.y || t.y + t.height <= s.y);
            }
        }
    }
}
const before = JSON.stringify(left.frameGeometry);
const excludedBefore = JSON.stringify(excluded.frameGeometry);
shortcuts.EVA01ArrangeWindows();
assert(left.frameGeometry.x < 1920);
assert(right.frameGeometry.x >= 1920);
assert.equal(left.output, screen);
assert.equal(JSON.stringify(excluded.frameGeometry), excludedBefore);
assert.equal(minimized.frameGeometry.width, 600);
assert.equal(hiddenDesktop.frameGeometry.width, 600);
shortcuts.EVA01ArrangeWindows();
shortcuts.EVA01RestoreWindows();
assert.equal(JSON.stringify(left.frameGeometry), before);
console.log('OK: geometrías, exclusiones, monitores y restauración de ventanas.');
