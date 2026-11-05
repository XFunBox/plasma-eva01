"""Pruebas aisladas: archivos reales, DBus y systemd simulados; nunca sesión KDE."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('barra_install', ROOT / 'instalar-barra.py')
barra = importlib.util.module_from_spec(spec) if spec else None
if spec and (ROOT / 'instalar-barra.py').exists():
    spec.loader.exec_module(barra)
SERVICE_STATUS = getattr(barra, 'service_status', None)

# This double executes generated JavaScript, rather than matching script text.
JS = r'''
const fs=require('fs'); const input=JSON.parse(fs.readFileSync(0,'utf8'));
let state=input.state, output=[];
function widget(w,p){return {id:w.id,type:w.type,set index(v){
 p.widgets.splice(p.widgets.indexOf(w),1);p.widgets.splice(v,0,w);
}};}
function wrap(p){return new Proxy({id:p.id,
 widgets(){return p.widgets.map(w=>widget(w,p));},
 addWidget(w){for(const x of state){const n=x.widgets.findIndex(y=>y.id===w.id);if(n>=0){const obj=x.widgets.splice(n,1)[0];p.widgets.push(obj);return widget(obj,p);}}throw Error('widget missing');},
 readConfig(k,d){return p.config[k]===undefined?d:p.config[k];},
 writeConfig(k,v){p.config[k]=v;},
 remove(){state=state.filter(x=>x!==p);}
 },{get(t,k){return k in t?t[k]:p[k];},set(t,k,v){if(k!=="currentConfigGroup")p[k]=v;return true;}});}
function panels(){return state.map(wrap);}
function panelById(id){const p=state.find(p=>p.id===id);return p?wrap(p):null;}
function Panel(){const p={id:Math.max(...state.map(p=>p.id))+1,screen:0,widgets:[],config:{}};state.push(p);return wrap(p);}
function print(v){output.push(v);}
try{eval(input.script);process.stdout.write(JSON.stringify({state,output}));}
catch(e){process.stdout.write(JSON.stringify({state,error:String(e)}));}
'''


class BarraTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / "instalar-barra.py").exists(), "Falta el instalador opcional de barra")
        self.tmp = tempfile.TemporaryDirectory(prefix='barra con espacios ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.roots = {key: self.base / key for key in ('config', 'data', 'state')}
        self.assets = self.base / 'assets'
        (self.assets / 'tema').mkdir(parents=True)
        (self.assets / 'tema/metadata.json').write_text('{"KPlugin":{"Id":"eva-islas-estados"}}')
        (self.assets / 'barra_sync.py').write_text('# daemon fixture\n')
        self.config('plasmarc').write_text('[Theme]\nname=old\n')
        self.config('plasma-org.kde.plasma.desktop-appletsrc').write_text('layout de evidencia\n')
        self.state = [self.panel(3, [self.widget(10,'org.kde.plasma.kickoff'),self.widget(11,'org.kde.plasma.icontasks'),self.widget(12,'org.kde.plasma.pager'),self.widget(13,'org.kde.plasma.systemtray')]),self.panel(22,[self.widget(20,'org.kde.plasma.icontasks'),self.widget(21,'org.kde.plasma.digitalclock')]),self.panel(30,[self.widget(31,'other')])]
        self.calls=[]
        self.patches=[patch.object(barra,'ASSETS',self.assets),patch.object(barra,'evaluate',self.evaluate),patch.object(barra,'run',self.run_command),patch.object(barra,'service_status',return_value={'enabled':False,'active':False}),patch.object(barra.core,'roots_from_env',return_value=self.roots),patch.object(barra.os,'geteuid',return_value=1000),patch.object(barra.shutil,'which',return_value='/usr/bin/example')]
        for item in self.patches:
            item.start();self.addCleanup(item.stop)

    @staticmethod
    def widget(id,type):
        return {'id':id,'type':type,'launchers':['applications:keep.desktop'],'other':'keep'}

    @staticmethod
    def panel(id,widgets):
        return {'id':id,'screen':0,'location':'top','alignment':'left','height':30,'offset':4,'hiding':'none','floating':False,'lengthMode':'fill','minimumLength':200,'maximumLength':900,'widgets':widgets,'config':{}}

    def config(self,name):
        path=self.roots['config']/name;path.parent.mkdir(parents=True,exist_ok=True);return path

    def evaluate(self,script):
        result=subprocess.run(['node','-e',JS],input=json.dumps({'state':self.state,'script':script}),text=True,capture_output=True,check=True)
        doc=json.loads(result.stdout);self.state=doc['state']
        if 'error' in doc:raise ValueError(doc['error'])
        return json.loads(doc['output'][-1])

    def run_command(self,command):
        self.calls.append(command)
        if command[0]=='kwriteconfig6':
            self.config('plasmarc').write_text('[Theme]\nname=eva-islas-estados\n')

    def backup(self):
        return next((self.roots['state']/'plasma-eva01/backups').iterdir())

    def manifest(self):
        return json.loads((self.backup()/'manifest.json').read_text())

    def rewrite_manifest(self,doc):
        barra.save_manifest(self.backup(),doc)

    def test_explicit_panels_required(self):
        with self.assertRaises(SystemExit):barra.main([])
        self.assertFalse(self.roots['state'].exists())

    def test_dry_run_writes_nothing_and_does_not_contact_session(self):
        with patch.object(barra,'evaluate',side_effect=AssertionError('DBus during dryrun')):
            barra.main(['--panels','3','22'])
        self.assertFalse(self.roots['state'].exists());self.assertFalse(self.calls)

    def test_apply_moves_widgets_and_restore_preserves_new_favorites_and_unrelated_panel(self):
        unrelated=copy.deepcopy(self.state[2])
        barra.main(['--apply','--panels','3','22'])
        self.assertEqual([w['id'] for w in self.state[0]['widgets']],[10,11])
        self.assertEqual([w['id'] for w in self.state[3]['widgets']],[12,13])
        self.assertEqual(self.state[0]['height'],52);self.assertEqual(self.state[3]['height'],44)
        self.state[0]['widgets'][1]['launchers']=['applications:new.desktop']
        self.state.append(self.panel(88,[self.widget(89,'later')]))
        barra.main(['--apply','--restore',str(self.backup())])
        self.assertEqual([w['id'] for w in self.state[0]['widgets']],[10,11,12,13])
        self.assertEqual(self.state[0]['height'],30)
        self.assertEqual(self.state[0]['widgets'][1]['launchers'],['applications:new.desktop'])
        self.assertEqual(self.state[2],unrelated);self.assertEqual(self.state[3]['id'],88)
        self.assertIn('name=old',self.config('plasmarc').read_text())
        self.assertFalse((self.roots['data']/'eva-panel-sync/barra_sync.py').exists())

    def test_restore_dryrun_validates_without_dbus_or_writes(self):
        barra.main(['--apply','--panels','3','22'])
        before=(self.backup()/'manifest.json').read_bytes()
        with patch.object(barra,'evaluate',side_effect=AssertionError('DBus dryrun')):
            barra.main(['--restore',str(self.backup())])
        self.assertEqual((self.backup()/'manifest.json').read_bytes(),before)

    def test_foreign_widget_blocks_restore_before_service_or_file_changes(self):
        barra.main(['--apply','--panels','3','22'])
        self.state[3]['widgets'].append(self.widget(99,'foreign'))
        self.calls.clear()
        with self.assertRaisesRegex(ValueError,'ajenos'):barra.main(['--apply','--restore',str(self.backup())])
        self.assertFalse(self.calls);self.assertIn('eva-islas',self.config('plasmarc').read_text())

    def test_missing_original_widget_blocks_restore(self):
        barra.main(['--apply','--panels','3','22']);self.state[0]['widgets'].pop()
        with self.assertRaisesRegex(ValueError,'widget'):barra.main(['--apply','--restore',str(self.backup())])

    def test_restore_rejects_tampered_file_hash_and_foreign_root(self):
        barra.main(['--apply','--panels','3','22']);doc=self.manifest()
        doc['roots']['config']='/tmp/other';self.rewrite_manifest(doc)
        with self.assertRaisesRegex(ValueError,'rutas'):barra.main(['--restore',str(self.backup())])
        doc['roots']['config']=str(self.roots['config']);self.rewrite_manifest(doc)
        entry=next(e for e in doc['entries'] if e['existed'])
        (self.backup()/entry['backup']).write_text('tampered')
        with self.assertRaisesRegex(ValueError,'adulterad'):barra.main(['--restore',str(self.backup())])

    def test_restore_rejects_escape_path_even_with_updated_checksum(self):
        barra.main(['--apply','--panels','3','22']);doc=self.manifest()
        doc['entries'][0]['path']='../escape';self.rewrite_manifest(doc)
        with self.assertRaisesRegex(ValueError,'permitid'):barra.main(['--restore',str(self.backup())])

    def test_partial_create_is_recorded_and_recoverable(self):
        original=self.evaluate
        def failure(script):
            value=original(script)
            if isinstance(value,dict) and 'created' in value:raise subprocess.CalledProcessError(1,'qdbus6')
            return value
        with patch.object(barra,'evaluate',side_effect=failure):
            with self.assertRaises(subprocess.CalledProcessError):barra.main(['--apply','--panels','3','22'])
        barra.main(['--apply','--restore',str(self.backup())])
        self.assertEqual([p['id'] for p in self.state],[3,22,30])

    def test_systemd_not_found_is_clean_install_and_bus_failure_is_not_hidden(self):
        result=subprocess.CompletedProcess([],0,'LoadState=not-found\nUnitFileState=\nActiveState=inactive\n','')
        with patch.object(barra.subprocess,'run',return_value=result):
            self.assertEqual(SERVICE_STATUS(),{'enabled':False,'active':False})
        with patch.object(barra.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'systemctl')):
            with self.assertRaises(subprocess.CalledProcessError):SERVICE_STATUS()

    def test_missing_qt_dependency_fails_before_creating_backup(self):
        original=self.run_command
        def command(args):
            if args[0]=='/usr/bin/python3':
                raise subprocess.CalledProcessError(1,args)
            return original(args)
        with patch.object(barra,'run',side_effect=command):
            with self.assertRaises(subprocess.CalledProcessError):barra.main(['--apply','--panels','3','22'])
        self.assertFalse(self.roots['state'].exists())

    def test_clean_install_does_not_stop_nonexistent_service(self):
        original=self.run_command
        def command(args):
            if args[:3]==['systemctl','--user','stop']:
                raise subprocess.CalledProcessError(5,args)
            return original(args)
        with patch.object(barra,'run',side_effect=command):
            barra.main(['--apply','--panels','3','22'])
        self.assertEqual([w['id'] for w in self.state[0]['widgets']],[10,11])

    def test_duplicate_apply_refused_and_service_stopped_before_mutations(self):
        with patch.object(barra,'service_status',return_value={'active':True,'enabled':True}):
            barra.main(['--apply','--panels','3','22'])
        self.assertEqual(next(c for c in self.calls if c[0]=='systemctl'),['systemctl','--user','stop','eva-panel-sync.service'])
        with self.assertRaisesRegex(ValueError,'instalaci'):barra.main(['--apply','--panels','3','22'])


if __name__=='__main__':unittest.main()
