"""Real Blender renders and a bounded derived preview for visual authoring."""
from __future__ import annotations

import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector

from .common import digest, file_hash, object_key, resolve_objects, units, write_new
from .geometry import GEOMETRY_TYPES, arrays, bounds, inspect_scene

VIEWS = {"iso": (1.4, -1.8, 1.2), "front": (0, -1, .0001),
         "back": (0, 1, .0001), "side": (1, 0, .0001), "top": (0, .0001, 1)}
MODES = {"clay", "reflection", "material", "silhouette", "normal", "checker"}


def controls(obj):
    values = []
    import json
    for control in json.loads(obj.get("contour_controls", "[]")):
        values.append({**control, "kind": "object_property", "object": obj.name,
                       "value": float(obj[control["property"]])})
    for modifier in obj.modifiers:
        if modifier.type != "NODES" or modifier.node_group is None:
            continue
        for socket in modifier.node_group.interface.items_tree:
            if socket.item_type != "SOCKET" or socket.in_out != "INPUT" or socket.socket_type != "NodeSocketFloat":
                continue
            values.append({"kind": "modifier", "object": obj.name, "modifier": modifier.name,
                           "property": socket.identifier, "label": socket.name,
                           "value": float(modifier.get(socket.identifier, socket.default_value)),
                           "minimum": float(socket.min_value), "maximum": float(socket.max_value)})
    if obj.type == "MESH" and obj.data.shape_keys:
        for key in list(obj.data.shape_keys.key_blocks)[1:]:
            values.append({"kind": "shape_key", "object": obj.name, "name": key.name,
                           "label": key.name, "value": key.value,
                           "minimum": key.slider_min, "maximum": key.slider_max})
    return values


def evaluated_copies(names=None):
    selected = resolve_objects(names)
    selected_ids = {object_key(obj) for obj in selected}
    graph = bpy.context.evaluated_depsgraph_get()
    scale = units(bpy.context.scene)
    copies = []
    for instance in graph.object_instances:
        obj = instance.object
        original = obj.original
        parent = instance.parent.original if instance.parent else None
        if obj.type not in GEOMETRY_TYPES or original.hide_render or not instance.show_self:
            continue
        if names is not None and object_key(original) not in selected_ids and (parent is None or object_key(parent) not in selected_ids):
            continue
        mesh = obj.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
        if mesh is None:
            continue
        try:
            copied = mesh.copy()
            copied.transform(Matrix.Scale(scale, 4) @ instance.matrix_world)
            copied.calc_loop_triangles()
            copies.append({"source": original, "mesh": copied, "instance": instance.is_instance,
                           "id": digest([object_key(original), list(instance.persistent_id), [list(row) for row in instance.matrix_world]]) if instance.is_instance else object_key(original)})
        finally:
            obj.to_mesh_clear()
    return copies


def preview(copies, maximum_triangles=100000):
    if not 100 <= maximum_triangles <= 1000000:
        raise ValueError("Preview triangle budget must be 100..1000000")
    total = sum(len(item["mesh"].loop_triangles) for item in copies)
    result = []
    for item in copies:
        mesh = item["mesh"]
        positions, triangles = arrays(mesh)
        limit = max(1, int(maximum_triangles*len(triangles)/max(1, total)))
        source_indices = np.arange(len(triangles), dtype=int)
        if len(triangles) > limit:
            # Explicit deterministic sampling; never called a replacement mesh.
            source_indices = np.linspace(0, len(triangles)-1, limit, dtype=int)
            triangles = triangles[source_indices]
        used, inverse = np.unique(triangles.flatten(), return_inverse=True)
        material = next((mat for mat in mesh.materials if mat), None)
        color = [.16, .48, .51]
        roughness, metallic = .45, .08
        if material and material.node_tree:
            shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
            if shader:
                color = list(shader.inputs["Base Color"].default_value)[:3]
                roughness = float(shader.inputs["Roughness"].default_value)
                metallic = float(shader.inputs["Metallic"].default_value)
        obj = item["source"]
        result.append({"id": item["id"], "source_id": object_key(obj), "name": obj.name,
                       "instance": item["instance"], "positions_m": positions[used].flatten().tolist(),
                       "indices": inverse.tolist(), "color": color, "roughness": roughness, "metallic": metallic,
                       "evaluated_vertex_indices": used.tolist(), "evaluated_triangle_indices": source_indices.tolist(),
                       "source_triangles": len(mesh.loop_triangles), "preview_triangles": len(triangles),
                       "preview_sampled": len(triangles) != len(mesh.loop_triangles), "controls": controls(obj),
                       "bounds": bounds(positions), "role": str(obj.get("role", ""))})
    return {"objects": result, "source_triangles": total,
            "preview_triangles": sum(item["preview_triangles"] for item in result),
            "scope": "Derived evaluated mesh preview at this revision. Large meshes use explicitly labelled triangle sampling. Simplified material and recomputed normals are for navigation; use real Blender renders for surface/material acceptance."}


def diagnostic_material(mode):
    mat = bpy.data.materials.new("Contour temporary " + mode)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    if mode in {"normal", "silhouette"}:
        shader = tree.nodes.new("ShaderNodeEmission")
        if mode == "normal":
            geom = tree.nodes.new("ShaderNodeNewGeometry")
            mapping = tree.nodes.new("ShaderNodeVectorMath")
            mapping.operation = "SCALE"
            mapping.inputs[3].default_value = .5
            tree.links.new(geom.outputs["Normal"], mapping.inputs[0])
            add = tree.nodes.new("ShaderNodeVectorMath")
            add.operation = "ADD"
            add.inputs[1].default_value = (.5, .5, .5)
            tree.links.new(mapping.outputs[0], add.inputs[0])
            tree.links.new(add.outputs[0], shader.inputs[0])
        else:
            shader.inputs[0].default_value = (1, 1, 1, 1)
    else:
        shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Base Color"].default_value = (.33, .42, .46, 1)
        shader.inputs["Roughness"].default_value = .15 if mode == "reflection" else .55
        shader.inputs["Metallic"].default_value = .75 if mode == "reflection" else 0
        if mode == "checker":
            checker = tree.nodes.new("ShaderNodeTexChecker")
            checker.inputs["Scale"].default_value = 12
            checker.inputs["Color1"].default_value = (.06, .12, .13, 1)
            checker.inputs["Color2"].default_value = (.8, .9, .88, 1)
            coords = tree.nodes.new("ShaderNodeTexCoord")
            tree.links.new(coords.outputs["UV"], checker.inputs["Vector"])
            tree.links.new(checker.outputs["Color"], shader.inputs["Base Color"])
    tree.links.new(shader.outputs[0], output.inputs["Surface"])
    return mat


def render_views(copies, output, views, modes, resolution=768, framing=None):
    if not copies:
        raise ValueError("Render scope has no visible geometry")
    if set(views)-set(VIEWS) or set(modes)-MODES:
        raise ValueError("Unknown render view or diagnostic mode")
    if not 128 <= resolution <= 2048:
        raise ValueError("Diagnostic resolution must be 128..2048")
    all_positions = np.concatenate([arrays(item["mesh"])[0] for item in copies if len(item["mesh"].vertices)])
    extent = np.ptp(all_positions, axis=0)
    center = Vector((all_positions.min(axis=0)+all_positions.max(axis=0))*.5)
    span = max(float(extent.max()), .001)
    if framing:
        center = Vector(framing["center_m"])
        span = float(framing["span_m"])
        if not math.isfinite(span) or span <= 0:
            raise ValueError("Invalid framing span")
    scene = bpy.data.scenes.new("Contour temporary inspection")
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("Contour temporary world")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.06, .07, .085, 1)
    background.inputs["Strength"].default_value = .3
    camera_data = bpy.data.cameras.new("Contour temporary camera")
    camera = bpy.data.objects.new("Contour temporary camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span*1.4
    owned_objects, lights, materials = [camera], [], []
    mesh_objects = []
    for item in copies:
        obj = bpy.data.objects.new("Contour temporary " + item["source"].name, item["mesh"])
        scene.collection.objects.link(obj)
        mesh_objects.append((obj, list(obj.data.materials)))
        owned_objects.append(obj)
    for index, direction in enumerate([(.5, -1.5, 2), (-1.5, -.1, .6), (1, 1.2, 1.4), (0, 0, 2.5)]):
        data = bpy.data.lights.new("Contour temporary strip", "AREA")
        data.energy = span*span*(230 if index == 0 else 90)
        data.shape = "RECTANGLE"
        data.size = span*2
        data.size_y = span*.13
        light = bpy.data.objects.new("Contour temporary strip", data)
        scene.collection.objects.link(light)
        light.location = center + Vector(direction)*span
        light.rotation_euler = (center-light.location).to_track_quat("-Z", "Y").to_euler()
        owned_objects.append(light)
        lights.append(data)
    rendered = []
    try:
        for mode in modes:
            material = diagnostic_material(mode) if mode != "material" else None
            if material:
                materials.append(material)
            for obj, original_materials in mesh_objects:
                obj.data.materials.clear()
                if material:
                    for index in range(max(1, len(original_materials))):
                        obj.data.materials.append(material)
                else:
                    for mat in original_materials:
                        obj.data.materials.append(mat)
            scene.view_settings.view_transform = "Raw" if mode in {"silhouette", "normal"} else "AgX"
            background.inputs["Color"].default_value = (0, 0, 0, 1) if mode == "silhouette" else (.06, .07, .085, 1)
            for view in views:
                direction = Vector(VIEWS[view]).normalized()
                camera.location = center + direction*span*3
                camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
                path = output/(view+"-"+mode+".png")
                if path.exists():
                    raise ValueError("Render path already exists")
                scene.render.filepath = str(path)
                bpy.ops.render.render(write_still=True, scene=scene.name)
                rendered.append({"path": path.name, "kind": "REAL_SCENE_RENDER", "view": view, "mode": mode,
                                 "sha256": file_hash(path), "camera_world": [list(row) for row in camera.matrix_world],
                                 "orthographic_scale_m": camera_data.ortho_scale, "resolution": resolution,
                                 "scope": "Isolated current-frame evaluated render scope; diagnostic overrides disclosed. Original scene data is not saved or modified."})
    finally:
        for obj in owned_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(scene)
        bpy.data.worlds.remove(world)
        bpy.data.cameras.remove(camera_data)
        for light in lights:
            bpy.data.lights.remove(light)
        for material in materials:
            bpy.data.materials.remove(material)
    return rendered, {"center_m": list(center), "span_m": span}


def make_packet(output, names=None, views=("iso", "front", "side"), modes=("clay", "reflection"),
                resolution=768, purpose="form", question="", render=True, framing=None, maximum_triangles=100000):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Packet needs a new directory")
    output.mkdir(parents=True)
    inspection = inspect_scene(names)
    copies = evaluated_copies(names)
    try:
        data = preview(copies, maximum_triangles)
        if not data["source_triangles"]:
            raise ValueError("A visual packet requires visible evaluated triangles")
        rendered, framing = render_views(copies, output, views, modes, resolution, framing) if render else ([], None)
        packet = {"schema_version": 2, "kind": "CONTOUR_VISUAL_PACKET", "revision": inspection["revision"],
                  "source_sha256": inspection["source_sha256"], "source_file": inspection["source_file"],
                  "blender_version": bpy.app.version_string, "frame": bpy.context.scene.frame_current,
                  "purpose": purpose, "question": question, "inspection": inspection, "preview": data,
                  "renders": rendered, "framing": framing, "generated_resources": [],
                  "imagegen": {"status": "READY_FOR_NATIVE_TOOL" if question else "NOT_REQUESTED",
                               "tool": "Built-in Codex imagegen; call via the host, not an API key/server",
                               "question": question, "maximum_initial_calls": 1, "maximum_refinements": 1,
                               "warning": "Generated designs are hypotheses; transfer into native source and inspect real renders."}}
        write_new(output/"packet.json", packet)
        write_new(output/"inspection.json", inspection)
        prompt = ("Purpose: "+purpose+"\nQuestion: "+question+"\n"
                  "Input images are real Blender renders of the same scene revision. Preserve the existing silhouette, "
                  "camera, fixed interfaces and declared dimensions unless the brief explicitly requests their change. "
                  "Propose only the design/detail/material needed to answer the question. Treat output as a design hypothesis. "
                  "Do not invent authoritative dimensions or claim that the image is the finished 3D model.\n")
        (output/"imagegen-prompt.txt").write_text(prompt, encoding="utf-8")
        return {"status": "PASS", "packet": str(output/"packet.json"), "revision": packet["revision"],
                "renders": len(rendered), "preview_triangles": data["preview_triangles"]}
    finally:
        for item in copies:
            if item["mesh"].users == 0:
                bpy.data.meshes.remove(item["mesh"])
