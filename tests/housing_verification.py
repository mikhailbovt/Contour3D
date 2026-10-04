"""Verify a saved example with native bpy only, without loading plugin code."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import bpy


def geometry_hash(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    try:
        value={"positions":[tuple(vertex.co) for vertex in mesh.vertices],
               "faces":[tuple(face.vertices) for face in mesh.polygons],
               "matrix":[tuple(row) for row in obj.matrix_world]}
        return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    finally:evaluated.to_mesh_clear()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    if args.output.exists() or args.report.exists():raise RuntimeError("Use new output paths")
    scene=bpy.context.scene
    assert scene["contour_example"]=="curved-housing-v1"
    assert abs(scene["crown_metres"]-.020)<1e-9
    assert not any(image.filepath and not image.packed_file for image in bpy.data.images if image.users)
    lid=bpy.data.objects["Crown lid"]
    assert lid.modifiers["Editable crown"].node_group is not None
    assert lid.modifiers["Retained surface sampling"].subdivision_type=="SIMPLE"
    assert lid.data.attributes.get("contour_protected_rim") is not None
    meshes=[obj for obj in scene.objects if obj.type=="MESH"]
    before={obj.name:geometry_hash(obj) for obj in meshes}
    shader=bpy.data.materials["Display phosphor"].node_tree.nodes["Principled BSDF"]
    shader.inputs["Emission Color"].default_value=(.12,.40,.8,1)
    bpy.context.view_layer.update()
    assert before=={obj.name:geometry_hash(obj) for obj in meshes}
    # A second, independent geometry edit uses the retained native Boolean source.
    cutter=bpy.data.objects["Vent aperture source"]
    for vertex in cutter.data.vertices:vertex.co.x*=1.10
    cutter.data.update();bpy.context.view_layer.update()
    after={obj.name:geometry_hash(obj) for obj in meshes}
    changed=sorted(name for name in before if before[name]!=after[name])
    assert changed==["Tapered housing","Vent aperture source"],changed
    report={"schema_version":1,"native_reopen_without_plugin_resources":"PASS",
            "retained_crown_and_rim_source":"PASS","independent_material_edit":"PASS",
            "independent_vent_pitch_edit":"PASS","changed_geometry":changed,
            "blender_version":bpy.app.version_string,"blender_python":sys.version,
            "independent_artistic_review":"NOT_CHECKED","comparison_against_C1":"NOT_CHECKED"}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    with args.report.open("x",encoding="utf8") as handle:json.dump(report,handle,indent=2);handle.write("\n")
    print("HOUSING_NATIVE "+json.dumps(report),flush=True)


if __name__=="__main__":main()
