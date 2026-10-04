"""Independent small geometry fixtures for the read-only probe, inside Blender."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

import bpy

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("probe",ROOT/"plugin/skills/professional-3d/scripts/scene_probe.py")
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def fixture(name,vertices,faces):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    return obj


def main():
    if bpy.data.filepath:raise RuntimeError("Run fixtures in a fresh factory Blender")
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    sheet=fixture("Intentional open sheet",[(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[(0,1,2,3)])
    sheet.scale=(2,3,4)
    solid=sheet.modifiers.new("Test evaluated thickness","SOLIDIFY");solid.thickness=.25;solid.offset=0
    degenerate=fixture("Known collinear triangle",[(0,0,0),(1,0,0),(2,0,0)],[(0,1,2)])
    bpy.context.view_layer.update()
    before=[tuple(vertex.co) for vertex in sheet.data.vertices]
    report=probe.audit_scene([sheet,degenerate])
    entries={item["name"]:item for item in report["objects"]}
    sheet_result=entries[sheet.name]
    assert sheet_result["source"]["triangles"]==2
    assert sheet_result["source"]["boundary_edges"]==4
    assert sheet_result["evaluated"]["triangles"]==12
    assert sheet_result["evaluated"]["boundary_edges"]==0
    assert sheet_result["evaluated"]["bounds"]=={"minimum_m":[-2.0,-3.0,-.5],"maximum_m":[2.0,3.0,.5]}
    assert entries[degenerate.name]["evaluated"]["triangles_at_or_below_1e-12_m2"]==1
    assert report["quality_status"]=="NOT_CHECKED"
    assert before==[tuple(vertex.co) for vertex in sheet.data.vertices]
    assert sheet.modifiers[0].thickness==.25
    previous_argv=sys.argv
    try:
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/"report.json"
            sys.argv=["blender","--","--output",str(output),"--objects",sheet.name]
            probe.main()
            data=json.loads(output.read_text())
            assert data["mesh_objects"]==1 and data["evaluated_triangles"]==12
            original=output.read_bytes()
            try:probe.main()
            except SystemExit as exc:assert exc.code==2
            else:raise AssertionError("Existing report was not rejected")
            assert output.read_bytes()==original
            missing=Path(temporary)/"missing.json"
            sys.argv=["blender","--","--output",str(missing),"--objects","Nonexistent"]
            try:probe.main()
            except SystemExit as exc:assert exc.code==2
            else:raise AssertionError("Missing scope was not rejected")
            assert not missing.exists()
    finally:sys.argv=previous_argv
    print("BLENDER_INTEGRATION PASS: evaluated geometry, unit transforms, degeneracy, intentional open sheet, unchanged scene, scope and non-overwrite",flush=True)


if __name__=="__main__":main()
