"""Resource records validate actual selected inputs and native evidence binding."""
import base64,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plugin/skills/professional-3d/scripts'))
from contour.common import file_hash
from contour.visual import record_output,record_transfer
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9kAAAAASUVORK5CYII=')

class ResourceEvidence(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.image=self.root/'selected.png';self.image.write_bytes(PNG)
        self.input=self.root/'real.png';self.input.write_bytes(PNG)
        self.packet=self.root/'packet.json'
        self.packet.write_text(json.dumps({'schema_version':2,'kind':'CONTOUR_VISUAL_PACKET','revision':'r1',
            'source_sha256':'a'*64,'frame':3,'inspection':{'metres_per_blender_unit':.1},
            'renders':[{'path':'real.png','sha256':file_hash(self.input),'kind':'REAL_SCENE_RENDER','view':'iso','mode':'clay'}]}),encoding='utf-8')
    def tearDown(self):self.temp.cleanup()
    def record(self):return record_output(self.packet,self.image,'The actual prompt','detail',['trim'],['real.png'])
    def test_exact_input_selection_and_byte_drift(self):
        with self.assertRaisesRegex(ValueError,'exact packet renders'):
            record_output(self.packet,self.image,'Prompt','detail',input_renders=['not-supplied.png'])
        self.input.write_bytes(PNG+b'different')
        with self.assertRaisesRegex(ValueError,'Input render changed'):self.record()
    def test_transfer_checks_source_frame_native_and_scoped_pass(self):
        result=self.record();record=json.loads(Path(result['record']).read_text(encoding='utf-8'))
        self.assertEqual(record['frame'],3);self.assertEqual(len(record['inputs']),1)
        self.assertEqual(record['status'],'GENERATED_DRAFT')
        native=self.root/'native.blend';native.write_bytes(b'BLENDER serialization fixture; not a native render test')
        evidence={'status':'PASS','acceptance':{'status':'PASS'},'source':{'source_sha256':'a'*64,'frame':3,'metres_per_blender_unit':.1},'output':str(native)}
        path=self.root/'edit.json';path.write_text(json.dumps(evidence))
        self.assertEqual(record_transfer(result['record'],native,path,self.root/'transfer.json','Native trim checked')['status'],'PASS')
        evidence['source']['frame']=4;path.write_text(json.dumps(evidence))
        with self.assertRaisesRegex(ValueError,'another frame'):
            record_transfer(result['record'],native,path,self.root/'wrong.json','Mismatch')
        evidence['source']['frame']=3;evidence['acceptance']['status']='FAIL';path.write_text(json.dumps(evidence))
        with self.assertRaisesRegex(ValueError,'passing scoped edit'):
            record_transfer(result['record'],native,path,self.root/'failed.json','Mismatch')
    def test_raster_and_duplicate_rejection(self):
        self.image.write_bytes(b'HTML is not a PNG')
        with self.assertRaisesRegex(ValueError,'raster header'):self.record()
        self.image.write_bytes(PNG);self.record()
        with self.assertRaisesRegex(ValueError,'already has a resource record'):self.record()
if __name__=='__main__':unittest.main()
