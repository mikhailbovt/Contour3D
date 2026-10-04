"""Read-only development instrumentation. Run inside the existing Blender process.

This measures geometry; it does not grade artistic quality or edit/save a scene.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy


def mesh_stats(mesh, matrix, unit_scale):
    mesh.calc_loop_triangles()
    verts = [matrix @ vertex.co for vertex in mesh.vertices]
    edge_use = [0] * len(mesh.edges)
    for poly in mesh.polygons:
        for loop_index in poly.loop_indices:
            edge_use[mesh.loops[loop_index].edge_index] += 1
    degenerate = 0
    minimum_area = None
    for tri in mesh.loop_triangles:
        a, b, c = (verts[index] for index in tri.vertices)
        area = (b - a).cross(c - a).length * 0.5 * unit_scale**2
        minimum_area = area if minimum_area is None else min(minimum_area, area)
        degenerate += int(not math.isfinite(area) or area <= 1e-12)
    bounds = None
    if verts:
        bounds = {
            "minimum_m": [min(v[axis] for v in verts) * unit_scale for axis in range(3)],
            "maximum_m": [max(v[axis] for v in verts) * unit_scale for axis in range(3)],
        }
    return {
        "vertices": len(mesh.vertices), "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
        "boundary_edges": sum(count == 1 for count in edge_use),
        "wire_edges": sum(count == 0 for count in edge_use),
        "edges_with_more_than_two_faces": sum(count > 2 for count in edge_use),
        "triangles_at_or_below_1e-12_m2": degenerate,
        "minimum_triangle_area_m2": minimum_area,
        "bounds": bounds,
        "uv_layers": [layer.name for layer in mesh.uv_layers],
    }


def audit_scene(selected_objects=None):
    started = time.monotonic()
    scene = bpy.context.scene
    graph = bpy.context.evaluated_depsgraph_get()
    unit_scale = scene.unit_settings.scale_length
    objects = []
    for obj in sorted(selected_objects if selected_objects is not None else scene.objects, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
        try:
            objects.append({
                "name": obj.name, "data": obj.data.name,
                "collections": sorted(collection.name for collection in obj.users_collection),
                "hide_render": obj.hide_render,
                "part": str(obj.get("part", "")),
                "source": mesh_stats(obj.data, obj.matrix_world, unit_scale),
                "evaluated": mesh_stats(mesh, evaluated.matrix_world, unit_scale),
                "modifiers": [{"name": m.name, "type": m.type,
                               "show_viewport": m.show_viewport, "show_render": m.show_render}
                              for m in obj.modifiers],
                "materials": [slot.material.name if slot.material else None
                              for slot in obj.material_slots],
            })
        finally:
            evaluated.to_mesh_clear()
    evaluated_total = sum(obj["evaluated"]["triangles"] for obj in objects)
    return {
        "schema_version": 1,
        "blender_version": bpy.app.version_string,
        "scene": scene.name, "source_file": Path(bpy.data.filepath).name,
        "frame": scene.frame_current,
        "unit_system": scene.unit_settings.system, "metres_per_blender_unit": unit_scale,
        "measurement_scope": "Scene mesh objects evaluated with the current viewport dependency graph. Excludes collection/Geometry Nodes instances, curves, non-mesh geometry and render-only modifier differences. Hidden objects are included and labelled.",
        "mesh_objects": len(objects),
        "source_triangles": sum(obj["source"]["triangles"] for obj in objects),
        "evaluated_triangles": evaluated_total,
        "render_visible_evaluated_triangles": sum(obj["evaluated"]["triangles"]
                                                 for obj in objects if not obj["hide_render"]),
        "objects_with_tiny_triangles": [obj["name"] for obj in objects
                                       if obj["evaluated"]["triangles_at_or_below_1e-12_m2"]],
        "largest_meshes": [{"name": obj["name"], "triangles": obj["evaluated"]["triangles"],
                            "fraction": obj["evaluated"]["triangles"] / evaluated_total if evaluated_total else 0}
                           for obj in sorted(objects, key=lambda item: item["evaluated"]["triangles"], reverse=True)[:20]],
        "quality_status": "NOT_CHECKED",
        "limitations": ["Boundary edges may be intentional sheet construction.",
                        "Triangle count is a cost signal, not a quality score.",
                        "Artistic quality, self-intersection, topology suitability, UV distortion and game integration were not graded."],
        "elapsed_seconds": round(time.monotonic() - started, 3), "objects": objects,
    }


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--objects", nargs="+", help="Exact scene object names to measure.")
    scope.add_argument("--collection", help="Exact scene collection name to measure, including children.")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; use a new evidence filename.")
    if output.suffix.lower() != ".json":
        parser.error("Output must be a JSON report.")
    selected_objects = None
    if args.objects:
        missing = sorted(set(args.objects) - set(bpy.context.scene.objects.keys()))
        if missing:
            parser.error("Requested objects are missing: " + ", ".join(missing))
        selected_objects = [bpy.context.scene.objects[name] for name in sorted(set(args.objects))]
        if not any(obj.type == "MESH" for obj in selected_objects):
            parser.error("The requested scope contains no mesh objects.")
    elif args.collection:
        collection = bpy.data.collections.get(args.collection)
        if collection is None:
            parser.error("Requested collection does not exist.")
        selected_objects = [obj for obj in collection.all_objects if obj.name in bpy.context.scene.objects]
        if not any(obj.type == "MESH" for obj in selected_objects):
            parser.error("The requested collection contains no scene mesh objects.")
    report = audit_scene(selected_objects)
    report["requested_scope"] = {"objects": args.objects, "collection": args.collection}
    if bpy.data.filepath:
        digest = hashlib.sha256()
        with open(bpy.data.filepath, "rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        report["source_sha256"] = digest.hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({key: report[key] for key in ["mesh_objects", "source_triangles", "evaluated_triangles", "largest_meshes", "elapsed_seconds"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
