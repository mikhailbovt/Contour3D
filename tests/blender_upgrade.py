"""Blender-native regression fixtures with measured outcomes, not artistic grades."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'plugin/skills/professional-3d/scripts'))
from contour.common import file_hash, source_identity
from contour.geometry import arrays, evaluated_mesh, inspect_scene, mesh_diagnostics, section_segments
from contour.intent import capture_contract, check_contract, object_state, snapshot
from contour.edits import apply_plan
from contour.episodes import build
from contour.packet import make_packet
from contour.delivery import delivery

OUT = Path(sys.argv[sys.argv.index('--')+1]).resolve()
OUT.mkdir(parents=True, exist_ok=False)
EVIDENCE = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.scale_length = 1


def grid(name='Editable', count=12):
    verts = [(x/count-.5, y/count-.5, 0) for y in range(count+1) for x in range(count+1)]
    faces = [(y*(count+1)+x, y*(count+1)+x+1, (y+1)*(count+1)+x+1, (y+1)*(count+1)+x)
             for y in range(count) for x in range(count)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    attribute = mesh.attributes.new('rim', 'FLOAT', 'POINT')
    for vertex in mesh.vertices:
        attribute.data[vertex.index].value = int(abs(vertex.co.x) > .4 or abs(vertex.co.y) > .4)
    return obj


def unchanged(obj, properties=None):
    rule = {'kind':'object_unchanged','object':obj.name}
    if properties:
        rule['properties'] = properties
    return rule


def plan(operations, constraints):
    identity = source_identity()
    return {'schema_version':2,'source_sha256':identity['source_sha256'],
            'frame':identity['frame'],'metres_per_blender_unit':identity['metres_per_blender_unit'],
            'operations':operations,'constraints':constraints}


def apply(label, spec):
    return apply_plan(spec, OUT/(label+'.blend'), OUT/(label+'.json'))


class NativeUpgrade(unittest.TestCase):
    def setUp(self):
        reset()

    def test_known_sections_uv_instances_and_curves(self):
        mesh = bpy.data.meshes.new('UV rectangle')
        mesh.from_pydata([(0,0,0),(2,0,0),(2,1,0),(0,1,0)], [], [(0,1,2,3)])
        obj = bpy.data.objects.new('Rectangle', mesh)
        bpy.context.scene.collection.objects.link(obj)
        uv = mesh.uv_layers.new()
        for point, coord in zip(uv.data, [(0,0),(1,0),(1,1),(0,1)]):
            point.uv = coord
        measured = mesh_diagnostics(mesh, Matrix.Identity(4))
        self.assertAlmostEqual(measured['uv']['anisotropy_median'], 2, places=6)
        positions, triangles = arrays(mesh, Matrix.Identity(4))
        section = section_segments(positions, triangles, [1,0,0], 1)
        length = sum(float(np.linalg.norm(np.asarray(pair[1])-pair[0])) for pair in section['segments'])
        self.assertAlmostEqual(length, 1)
        with self.assertRaises(ValueError):
            section_segments(positions, triangles, [1,0,0], float('nan'))
        collection = bpy.data.collections.new('Instance source')
        collection.objects.link(obj)
        instance = bpy.data.objects.new('Assembly instance', None)
        instance.instance_type = 'COLLECTION'; instance.instance_collection = collection
        instance.location.x = 3
        bpy.context.scene.collection.objects.link(instance)
        curve = bpy.data.curves.new('Curve source', 'CURVE'); curve.dimensions = '3D'; curve.bevel_depth = .05
        spline = curve.splines.new('POLY'); spline.points.add(1)
        spline.points[0].co = (0,0,1,1); spline.points[1].co = (1,0,1,1)
        curve.use_fill_caps = True
        handle = bpy.data.objects.new('Curve handle', curve); bpy.context.scene.collection.objects.link(handle)
        bpy.context.view_layer.update()
        before = snapshot()
        report = inspect_scene(thickness=True)
        self.assertEqual(snapshot()['revision'], before['revision'])
        # Blender emits two linked-object instances for a multiply-linked source.
        self.assertGreaterEqual(len(report['instances']), 1)
        self.assertGreater(next(item for item in report['objects'] if item['type']=='CURVE')['evaluated']['triangles'], 0)
        EVIDENCE['measurement'] = {'known_uv_anisotropy':2,'measured_section_length_m':length,
                                  'instances':len(report['instances']), 'curve_conversion':'PASS','read_only':'PASS'}

    def test_material_group_and_context_are_protected(self):
        obj = grid()
        mat = bpy.data.materials.new('Shared shader'); mat.use_nodes = True; obj.data.materials.append(mat)
        group = bpy.data.node_groups.new('Shared colour', 'ShaderNodeTree')
        group.interface.new_socket(name='Colour', in_out='OUTPUT', socket_type='NodeSocketColor')
        rgb = group.nodes.new('ShaderNodeRGB'); out = group.nodes.new('NodeGroupOutput')
        group.links.new(rgb.outputs[0], out.inputs[0])
        group_node = mat.node_tree.nodes.new('ShaderNodeGroup'); group_node.node_tree = group
        mat.node_tree.links.new(group_node.outputs[0], mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
        baseline = capture_contract([unchanged(obj, ['materials'])])
        self.assertEqual(check_contract(baseline)['status'], 'PASS')
        rgb.outputs[0].default_value = (.1,.5,.1,1)
        # RGB output defaults must be included, not just group input socket values.
        self.assertEqual(check_contract(baseline)['status'], 'FAIL')
        baseline = capture_contract([unchanged(obj)])
        bpy.context.scene.unit_settings.scale_length = .001
        self.assertEqual(check_contract(baseline)['status'], 'FAIL')
        bpy.context.scene.unit_settings.scale_length = 1
        bpy.context.scene.frame_set(2)
        self.assertEqual(check_contract(baseline)['status'], 'FAIL')
        with self.assertRaises(ValueError):
            capture_contract([{'kind':'bounds_unchanged','object':obj.name,'tolerance_m':-1}])
        EVIDENCE['shared_shader_and_scene_context'] = 'PASS'

    def test_deformation_world_units_rollback_and_next_edit(self):
        obj = grid(); obj.scale = (2,1,.5)
        bpy.context.scene.unit_settings.scale_length = .1
        datum = grid('Protected neighbour'); datum.location.z = -2
        solid = obj.modifiers.new('Wall', 'SOLIDIFY'); solid.thickness = .03
        bpy.context.view_layer.update()
        constraints = [unchanged(datum), unchanged(obj,['materials','transform','dependencies']),
                       {'kind':'region_position','object':obj.name,'selector':{'kind':'attribute','name':'rim'},
                        'evaluated':True,'tolerance_m':1e-7,'normal_tolerance_degrees':.05}]
        operation = {'kind':'deform','object':obj.name,'name':'Retained local crown',
                     'center_m':[0,0,0],'radii_m':[.06,.03,.02],'delta_m':[0,0,.002],
                     'maximum_displacement_m':.003,'protected_regions':[{'kind':'attribute','name':'rim'}]}
        source_mesh = obj.data
        bad = apply('rollback',plan([operation], constraints+[unchanged(obj,['geometry'])]))
        self.assertEqual(bad['status'],'FAIL'); self.assertEqual(bad['rollback']['status'],'PASS')
        self.assertIs(obj.data,source_mesh); self.assertFalse((OUT/'rollback.blend').exists())
        good = apply('deformed',plan([operation], constraints))
        self.assertEqual(good['status'],'PASS', good.get('reason'))
        with evaluated_mesh(obj) as (evaluated, matrix):
            positions, _ = arrays(evaluated,matrix,.1)
            center_top = float(positions[:,2].max())
        self.assertAlmostEqual(center_top,.002,places=7)
        bpy.ops.wm.open_mainfile(filepath=str(OUT/'deformed.blend'), load_ui=False, use_scripts=False)
        obj = bpy.context.scene.objects['Editable']
        control = {'kind':'shape_key','object':obj.name,'name':'Retained local crown','minimum':0,'maximum':1}
        next_edit = apply('deformed-next',plan([{'kind':'set_control','control':control,'value':.5}],constraints))
        self.assertEqual(next_edit['status'],'PASS',next_edit.get('reason'))
        self.assertEqual(obj.data.shape_keys.key_blocks['Retained local crown'].value,.5)
        EVIDENCE['local_deformation'] = {'world_peak_m':center_top,'rollback':'PASS',
                                      'evaluated_region_and_normals':'PASS','native_reopen_and_next_edit':'PASS'}

    def test_bounded_fit_and_exhaustion(self):
        obj = grid(); obj.shape_key_add(name='Basis'); key = obj.shape_key_add(name='Height')
        for point in key.data:
            point.co.z = .02
        datum = grid('Datum'); datum.location.z = -.1
        control = {'kind':'shape_key','object':obj.name,'name':'Height','minimum':0,'maximum':1}
        target = {'kind':'region_coordinate','object':obj.name,'selector':{'kind':'attribute','name':'rim'},
                  'axis':2,'target_m':.015,'tolerance_m':1e-6}
        fit = {'kind':'fit_controls','controls':[control],'targets':[target],'maximum_candidates':12}
        report = apply('fit',plan([fit],[unchanged(datum)]))
        self.assertEqual(report['status'],'PASS',report.get('reason'))
        self.assertAlmostEqual(key.value,.75)
        target['target_m'] = .05; fit['maximum_candidates'] = 3
        report = apply('fit-exhausted',plan([fit],[unchanged(datum)]))
        self.assertEqual(report['status'],'FAIL'); self.assertEqual(key.value,.75)
        self.assertEqual(len(report['trials']),3); self.assertFalse((OUT/'fit-exhausted.blend').exists())
        stale = plan([{'kind':'set_control','control':control,'value':.2}],[unchanged(datum)])
        stale['source_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            apply('stale',stale)
        EVIDENCE['bounded_fit'] = {'native_value':.75,'trials':len(report['trials']),
                                 'budget_failure_rollback':'PASS','stale_hash_rejected':'PASS'}

    def test_repair_and_read_only_render_packet(self):
        build('imported-repair',OUT/'repair-source.blend')
        obj = bpy.context.scene.objects['Imported repair fixture']
        datum = bpy.context.scene.objects['Protected fixture datum']
        before_hash = file_hash(OUT/'repair-source.blend')
        constraints = [unchanged(datum),unchanged(obj,['materials','transform','dependencies']),
                       {'kind':'bounds_unchanged','object':obj.name,'tolerance_m':1e-8}]
        report = apply('repaired',plan([{'kind':'repair_degenerate','object':obj.name}],constraints))
        self.assertEqual(report['status'],'PASS',report.get('reason'))
        self.assertEqual(report['operations'][0]['tiny_triangles_before'],1)
        self.assertEqual(report['operations'][0]['tiny_triangles_after'],0)
        self.assertEqual(before_hash,file_hash(OUT/'repair-source.blend'))
        state = snapshot()
        packet = make_packet(OUT/'read-only-packet',views=['iso'],modes=['reflection'],resolution=256)
        self.assertEqual(snapshot()['revision'],state['revision'])
        self.assertEqual(packet['renders'],1)
        self.assertFalse(any(scene.name.startswith('Contour temporary') for scene in bpy.data.scenes))
        EVIDENCE['repair_and_packet'] = {'tiny_before':1,'tiny_after':0,'source_hash_unchanged':'PASS',
                                       'shader_bounds_and_neighbour':'PASS','real_render_read_only':'PASS'}

    def test_assembly_evaluated_interface(self):
        build('assembly',OUT/'bridge-source.blend')
        obj = bpy.context.scene.objects['Editable bridge']
        constraints = [unchanged(item) for item in bpy.context.scene.objects if item != obj]
        constraints += [{'kind':'region_position','object':obj.name,'selector':{'kind':'attribute','name':'fixed_mount_band'},
                         'evaluated':True,'tolerance_m':1e-7,'normal_tolerance_degrees':.05}]
        control = {'kind':'shape_key','object':obj.name,'name':'Bridge arch','minimum':0,'maximum':1.5}
        report = apply('bridge-next',plan([{'kind':'set_control','control':control,'value':1.2}],constraints))
        self.assertEqual(report['status'],'PASS',report.get('reason'))
        EVIDENCE['assembly_evaluated_interface'] = report['acceptance']['checks'][-1]

    def test_packed_local_texture_and_static_export_roundtrip(self):
        obj=grid();datum=grid('Shared material neighbour');datum.location.x=1.3
        mat=bpy.data.materials.new('Shared material');mat.use_nodes=True
        obj.data.materials.append(mat);datum.data.materials.append(mat)
        uv=obj.data.uv_layers.new(name='Texture UV')
        for polygon in obj.data.polygons:
            for loop_index in polygon.loop_indices:
                vertex=obj.data.vertices[obj.data.loops[loop_index].vertex_index]
                uv.data[loop_index].uv=(vertex.co.x+.5,vertex.co.y+.5)
        # A native test resource, unrelated to the user-facing imagegen result.
        image=bpy.data.images.new('Native test texel',width=2,height=2)
        image.generated_color=(.1,.4,.3,1)
        image.filepath_raw=str(OUT/'native-test-resource.png');image.file_format='PNG';image.save()
        bpy.data.images.remove(image)
        # External image material survives Blender's relative-path remapping.
        external=bpy.data.images.load(str(OUT/'native-test-resource.png'))
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=external
        mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        initial=OUT/'texture-origin'/'source.blend';initial.parent.mkdir()
        bpy.ops.wm.save_as_mainfile(filepath=str(initial))
        external.filepath=bpy.path.relpath(external.filepath)
        material_baseline=capture_contract([unchanged(datum,['materials'])])
        moved=OUT/'texture-relocated.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(moved))
        bpy.ops.wm.open_mainfile(filepath=str(moved),load_ui=False,use_scripts=False)
        self.assertEqual(check_contract(material_baseline)['status'],'PASS')
        obj=bpy.data.objects['Editable'];datum=bpy.data.objects['Shared material neighbour'];mat=datum.material_slots[0].material
        bpy.context.scene.unit_settings.scale_length=.1
        bpy.context.view_layer.update()
        operation={'kind':'assign_base_color','object':obj.name,'image':str(OUT/'native-test-resource.png'),
                   'image_sha256':file_hash(OUT/'native-test-resource.png'),'uv_layer':'Texture UV'}
        spec=plan([operation],[unchanged(datum),unchanged(obj,['geometry','transform','dependencies'])])
        report=apply('texture-native',spec)
        self.assertEqual(report['status'],'PASS',report.get('reason'))
        self.assertIs(datum.material_slots[0].material,mat)
        self.assertIsNot(obj.material_slots[0].material,mat)
        self.assertTrue(any(image.packed_file for image in bpy.data.images))
        bpy.ops.wm.open_mainfile(filepath=str(OUT/'texture-native.blend'),load_ui=False,use_scripts=False)
        state=snapshot()
        export=delivery(OUT/'static.glb',OUT/'static-export.json',['Editable'],triangle_budget=400)
        self.assertEqual(export['status'],'PASS',export.get('reason'))
        self.assertEqual(snapshot()['revision'],state['revision'])
        self.assertEqual(export['roundtrip']['triangles'],288)
        self.assertGreater((OUT/'static.glb').stat().st_size,100)
        EVIDENCE['packed_texture_and_export']={'local_material_isolation':'PASS','native_reopen_packed_image':'PASS','external_image_path_remapping':'PASS',
                                             'source_unmodified_by_export':'PASS','roundtrip':export['roundtrip']}


suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeUpgrade)
result = unittest.TextTestRunner(verbosity=2).run(suite)
(OUT/'verification.json').write_text(json.dumps({'status':'PASS' if result.wasSuccessful() else 'FAIL',
    'tests':result.testsRun,'evidence':EVIDENCE,'blender':bpy.app.version_string},indent=2),encoding='utf-8')
if not result.wasSuccessful():
    raise SystemExit(1)
