"""Local app request/serving boundaries; no network services or native-file writes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'plugin/skills/professional-3d/scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('workbench',SCRIPTS/'workbench.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)


class WorkbenchBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.packet={'schema_version':2,'kind':'CONTOUR_VISUAL_PACKET','revision':'r1','source_file':'scene.blend',
                     'source_sha256':'a'*64,'frame':1,'inspection':{'metres_per_blender_unit':1},'renders':[],
                     'preview':{'objects':[{'id':'part','source_id':'source','name':'Part','instance':False,
                                          'controls':[{'kind':'shape_key','minimum':0,'maximum':1}]}]}}
        (self.root/'packet.json').write_text(json.dumps(self.packet),encoding='utf-8')
        (self.root/'secret.blend').write_bytes(b'private')
        self.server=app.make_server(self.root/'packet.json')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
        self.valid={'source_revision':'r1','intent':'Change the crown','selection':{'id':'part','point_m':[0,0,0]},
                    'protected_regions':[{'id':'part','center_m':[0,0,0],'radius_m':.01}],
                    'control_changes':[{'id':'part','index':0,'value':.5}]}

    def tearDown(self):
        self.server.shutdown();self.thread.join(2);self.server.server_close();self.temp.cleanup()

    def request(self,path='/',data=None,headers=None):
        req=Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,
                    headers=headers or {})
        try:
            with urlopen(req,timeout=3) as response:
                return response.status,response.read(),response.headers
        except HTTPError as error:
            with error: return error.code,error.read(),error.headers

    def test_real_bundle_is_served_without_external_sources(self):
        code,body,headers=self.request()
        self.assertEqual(code,200);self.assertIn(b'Contour3D',body)
        self.assertIn("connect-src 'self'",headers['Content-Security-Policy'])
        self.assertEqual(self.request('/vendor/three.core.js')[0],200)
        self.assertEqual(self.request('/data/packet.json')[0],200)

    def test_only_selected_files_and_valid_host(self):
        for path in ['/data/secret.blend','/data/../secret.blend','/data/%2e%2e/secret.blend','/../../README.md']:
            self.assertEqual(self.request(path)[0],404)
        self.assertEqual(self.request(headers={'Host':'attacker.invalid'})[0],403)

    def test_write_is_revision_bound_request_artifact(self):
        code,body,_=self.request('/api/requests',self.valid,{'Origin':self.url})
        self.assertEqual(code,201)
        result=json.loads(body);saved=json.loads(Path(result['request_path']).read_text(encoding='utf-8'))
        self.assertEqual(saved['native_edit'],'NOT_RUN');self.assertEqual(saved['frame'],1)
        self.assertEqual(saved['metres_per_blender_unit'],1)
        self.assertEqual(saved['protected_regions'][0]['source_id'],'source')
        self.assertEqual((self.root/'secret.blend').read_bytes(),b'private')

    def test_origin_stale_invalid_control_and_numeric_rejections(self):
        self.assertEqual(self.request('/api/requests',self.valid,{'Origin':'https://attacker.invalid'})[0],403)
        for mutation in [('source_revision','old'),('control_changes',[{'id':'part','index':0,'value':2}]),
                         ('selection',{'id':'part','point_m':[float('nan'),0,0]}),('intent','')]:
            value={**self.valid,mutation[0]:mutation[1]}
            self.assertEqual(self.request('/api/requests',value,{'Origin':self.url})[0],400)
        self.assertFalse((self.root/'requests').exists())

    def test_path_rejection_before_write(self):
        with self.assertRaises(ValueError): app.within(self.root,'../outside.json')
        with self.assertRaises(ValueError): app.within(self.root,'C:\\private.json')


if __name__=='__main__': unittest.main()
