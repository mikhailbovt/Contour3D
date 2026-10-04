"""Bounded native edits with rollback; JSON describes data, never executable code."""
from __future__ import annotations

import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

from .common import file_hash, finite_number, source_identity, units, vector, write_new
from .geometry import arrays, bounds, evaluated_mesh, mesh_diagnostics
from .intent import capture_contract, check_contract, select_vertices


class Transaction:
    def __init__(self):
        self.undo = []

    def copy_mesh(self, obj):
        old = obj.data
        new = old.copy()
        obj.data = new
        def restore():
            obj.data = old
            if new.users == 0:
                bpy.data.meshes.remove(new)
        self.undo.append(restore)
        return new

    def rollback(self):
        for action in reversed(self.undo):
            action()
        bpy.context.view_layer.update()


def control_access(control):
    obj = bpy.context.scene.objects.get(control.get("object", ""))
    if obj is None:
        raise ValueError("Control object missing")
    kind = control.get("kind")
    if kind == "object_property":
        key = control["property"]
        if key.startswith("_") or key not in obj or isinstance(obj[key], bool) or not isinstance(obj[key], (int, float)):
            raise ValueError("Object control must be an existing public scalar numeric custom property")
        def setter(value):
            obj[key] = int(round(value)) if isinstance(obj[key], int) else value
            obj.update_tag()
        return lambda: obj[key], setter
    if kind == "modifier":
        modifier = obj.modifiers.get(control["modifier"])
        if modifier is None:
            raise ValueError("Modifier missing")
        key = control["property"]
        if key.startswith("_"):
            raise ValueError("Private properties are not controls")
        if modifier.type == "NODES" and key in modifier:
            def setter(value):
                modifier[key] = value
                obj.update_tag()
            return lambda: modifier[key], setter
        prop = modifier.bl_rna.properties.get(key)
        if prop is None or prop.is_readonly or prop.type not in {"FLOAT", "INT"} or prop.is_array:
            raise ValueError("Control must be a writable scalar numeric modifier input")
        def setter(value):
            setattr(modifier, key, int(round(value)) if prop.type == "INT" else value)
            obj.update_tag()
        return lambda: getattr(modifier, key), setter
    if kind == "shape_key":
        keys = getattr(obj.data, "shape_keys", None)
        key = keys.key_blocks.get(control["name"]) if keys else None
        if key is None:
            raise ValueError("Shape-key control missing")
        return lambda: key.value, lambda value: setattr(key, "value", value)
    raise ValueError("Unsupported control kind")


def set_control(control, value, transaction):
    low = finite_number(control["minimum"], "control minimum")
    high = finite_number(control["maximum"], "control maximum", low)
    value = finite_number(value, "control value", low, high)
    getter, setter = control_access(control)
    original = getter()
    if isinstance(original, bool) or not isinstance(original, (int, float)):
        raise ValueError("Control is not a scalar number")
    transaction.undo.append(lambda: setter(original))
    setter(value)
    bpy.context.view_layer.update()
    return {"operation": "set_control", "object": control["object"], "before": original, "after": getter()}


def deform(operation, transaction):
    obj = bpy.context.scene.objects.get(operation.get("object", ""))
    if obj is None or obj.type != "MESH" or obj.library:
        raise ValueError("Local deformation requires a local mesh object")
    if abs(obj.matrix_world.determinant()) < 1e-15:
        raise ValueError("Local deformation needs an invertible object transform")
    if any(mod.type in {"ARMATURE", "CLOTH", "SOFT_BODY", "FLUID"} for mod in obj.modifiers):
        raise ValueError("Rigged/simulated deformation needs a pose-aware method; use native controls")
    center = np.asarray(vector(operation["center_m"]))
    radii = np.asarray(vector(operation["radii_m"]))
    if np.any(radii <= 0):
        raise ValueError("Falloff radii must be positive")
    delta = Vector(vector(operation["delta_m"]))
    if delta.length == 0:
        raise ValueError("Requested deformation is zero")
    maximum = finite_number(operation.get("maximum_displacement_m", .1), "maximum displacement", 1e-12)
    if delta.length > maximum:
        raise ValueError("Requested displacement exceeds declared limit")
    mesh = transaction.copy_mesh(obj)
    if mesh.shape_keys and not mesh.shape_keys.use_relative:
        raise ValueError("Absolute shape-key sequences require another method")
    positions, _ = arrays(mesh, obj.matrix_world, units(bpy.context.scene))
    weights = np.maximum(0, 1-np.sum(((positions-center)/radii)**2, axis=1))**3
    for selector in operation.get("protected_regions", []):
        indices = select_vertices(obj, mesh, positions, selector, False)
        weights[indices] = 0
    if not np.any(weights > 0):
        raise ValueError("Editable region has no nonzero influence")
    if mesh.shape_keys is None:
        obj.shape_key_add(name="Basis")
    name = operation.get("name", "Contour local deformation")
    if mesh.shape_keys.key_blocks.get(name):
        raise ValueError("Shape key already exists; use its native control for the next edit")
    key = obj.shape_key_add(name=name, from_mix=False)
    local_delta = obj.matrix_world.inverted_safe().to_3x3() @ (delta/units(bpy.context.scene))
    for point, weight in zip(key.data, weights):
        point.co += local_delta*float(weight)
    key.value = 1
    obj.data.update()
    bpy.context.view_layer.update()
    return {"operation": "deform", "object": obj.name, "native_control": key.name,
            "influenced_source_vertices": int(np.sum(weights > 0)),
            "maximum_source_displacement_m": float(weights.max())*delta.length,
            "coverage": "Retained relative shape key and compact C2 polynomial falloff in the declared source-space region; evaluated invariants are checked separately."}


def repair(operation, transaction):
    obj = bpy.context.scene.objects.get(operation.get("object", ""))
    if obj is None or obj.type != "MESH" or obj.library or obj.data.shape_keys:
        raise ValueError("Degenerate repair requires a local mesh without shape keys")
    if any(mod.type in {"ARMATURE", "CLOTH", "SOFT_BODY", "FLUID"} for mod in obj.modifiers) and not operation.get("allow_rigged_topology", False):
        raise ValueError("Rigged/simulated topology repair needs explicit current-frame authorization and a separate animation check")
    distance = finite_number(operation.get("distance_m", 1e-7), "repair distance", 1e-12, .001)
    before = mesh_diagnostics(obj.data, obj.matrix_world, units(bpy.context.scene))
    with evaluated_mesh(obj) as (evaluated, matrix):
        evaluated_before = mesh_diagnostics(evaluated, matrix, units(bpy.context.scene))
    mesh = transaction.copy_mesh(obj)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        transform = obj.matrix_world.copy()
        from mathutils import Matrix
        transform = Matrix.Scale(units(bpy.context.scene), 4) @ transform
        bmesh.ops.transform(bm, matrix=transform, verts=list(bm.verts))
        bmesh.ops.dissolve_degenerate(bm, dist=distance, edges=list(bm.edges))
        bmesh.ops.transform(bm, matrix=transform.inverted_safe(), verts=list(bm.verts))
        bm.to_mesh(mesh)
        mesh.update()
    finally:
        bm.free()
    bpy.context.view_layer.update()
    after = mesh_diagnostics(mesh, obj.matrix_world, units(bpy.context.scene))
    with evaluated_mesh(obj) as (evaluated, matrix):
        evaluated_after = mesh_diagnostics(evaluated, matrix, units(bpy.context.scene))
    before_tiny = max(before["triangles_at_or_below_1e-12_m2"], evaluated_before["triangles_at_or_below_1e-12_m2"])
    after_tiny = max(after["triangles_at_or_below_1e-12_m2"], evaluated_after["triangles_at_or_below_1e-12_m2"])
    if after_tiny >= before_tiny:
        raise ValueError("Repair did not reduce the measured tiny-triangle count; another cause/method is needed")
    return {"operation": "repair_degenerate", "object": obj.name,
            "tiny_triangles_before": before_tiny, "tiny_triangles_after": after_tiny,
            "source_tiny_triangles_before": before["triangles_at_or_below_1e-12_m2"],
            "source_tiny_triangles_after": after["triangles_at_or_below_1e-12_m2"],
            "evaluated_tiny_triangles_before": evaluated_before["triangles_at_or_below_1e-12_m2"],
            "evaluated_tiny_triangles_after": evaluated_after["triangles_at_or_below_1e-12_m2"],
            "source_triangles_before": before["triangles"], "source_triangles_after": after["triangles"],
            "coverage": "BMesh degenerate-edge dissolve at declared physical distance, validated on source and current-frame evaluated geometry. No blanket remesh or automatic removal of valid open boundaries. Rigged topology needs a separate animation/weight check."}


def assign_base_color(operation, transaction):
    """Transfer an inspected bitmap into native UV/shader data, preserving shared materials."""
    obj = bpy.context.scene.objects.get(operation.get("object", ""))
    if obj is None or obj.type != "MESH" or obj.library:
        raise ValueError("Texture transfer requires a local mesh")
    path = Path(operation["image"]).resolve()
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"} or not path.is_file():
        raise ValueError("Choose an existing inspected PNG/JPEG/WebP")
    if file_hash(path) != operation["image_sha256"]:
        raise ValueError("Selected image bytes changed")
    uv_name = operation["uv_layer"]
    if uv_name not in obj.data.uv_layers:
        raise ValueError("Texture transfer requires the declared existing UV layer")
    slot = operation.get("slot", 0)
    if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < len(obj.material_slots):
        raise ValueError("Choose an existing material slot")
    original = obj.material_slots[slot].material
    if original is None or original.node_tree is None:
        raise ValueError("Choose an existing node material")
    shader_name = operation.get("shader_node", "Principled BSDF")
    shader = original.node_tree.nodes.get(shader_name)
    if shader is None or shader.type != "BSDF_PRINCIPLED":
        raise ValueError("Choose the existing Principled shader explicitly")
    mesh = transaction.copy_mesh(obj)
    material = original.copy()
    transaction.undo.append(lambda: bpy.data.materials.remove(material, do_unlink=True))
    material.name = operation.get("material_name", original.name+" local image resource")
    # Object-linked slots must also be restored; data-linked slots live in the copied mesh.
    if obj.material_slots[slot].link == "OBJECT":
        transaction.undo.append(lambda: setattr(obj.material_slots[slot], "material", original))
        obj.material_slots[slot].material = material
    else:
        mesh.materials[slot] = material
    image = bpy.data.images.load(str(path), check_existing=False)
    transaction.undo.append(lambda: bpy.data.images.remove(image, do_unlink=True))
    image.colorspace_settings.name = "sRGB"
    image.pack()
    tree = material.node_tree
    texture = tree.nodes.new("ShaderNodeTexImage"); texture.image = image
    texture.name = "Contour inspected base colour"
    uv = tree.nodes.new("ShaderNodeUVMap"); uv.uv_map = uv_name
    tree.links.new(uv.outputs[0], texture.inputs["Vector"])
    tree.links.new(texture.outputs["Color"], tree.nodes[shader_name].inputs["Base Color"])
    bpy.context.view_layer.update()
    return {"operation":"assign_base_color", "object":obj.name, "slot":slot,
            "image_sha256":file_hash(path), "packed":bool(image.packed_file), "uv_layer":uv_name,
            "material":material.name, "coverage":"Native packed sRGB base-colour resource in a local material copy. Existing roughness/metallic remain independent; generated pixels are not calibrated PBR maps."}


def target_value(target):
    obj = bpy.context.scene.objects.get(target["object"])
    if obj is None:
        raise ValueError("Fit target object missing")
    with evaluated_mesh(obj) as (mesh, matrix):
        positions, _ = arrays(mesh, matrix, units(bpy.context.scene))
        if target["kind"] == "bounds_extent":
            return bounds(positions)["extent_m"][int(target["axis"])]
        if target["kind"] == "region_coordinate":
            indices = select_vertices(obj, mesh, positions, target["selector"], True)
            return float(positions[indices, int(target["axis"])].mean())
        if target["kind"] == "surface_ray_coordinate":
            origin = Vector(vector(target["origin_m"]))/units(bpy.context.scene)
            direction = Vector(vector(target["direction"]))
            if direction.length < 1e-12:
                raise ValueError("Fit ray direction is zero")
            inverse = matrix.inverted_safe()
            hit, location, normal, face = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).ray_cast(
                inverse @ origin, (inverse.to_3x3() @ direction).normalized())
            if not hit:
                raise ValueError("Fit measurement ray missed the surface")
            return float((matrix @ location)[int(target["axis"])])*units(bpy.context.scene)
    raise ValueError("Unsupported fit target")


def fit(operation, baseline, transaction):
    controls = operation["controls"]
    targets = operation["targets"]
    budget = operation.get("maximum_candidates", 18)
    if not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= 60:
        raise ValueError("Fit budget must be 1..60 candidates")
    if not 1 <= len(controls) <= 8 or not targets:
        raise ValueError("Fit needs 1..8 controls and explicit targets")
    access = [control_access(control) for control in controls]
    originals = [getter() for getter, setter in access]
    for (_, setter), original in zip(access, originals):
        transaction.undo.append(lambda setter=setter, original=original: setter(original))
    intervals = [(finite_number(control["minimum"]), finite_number(control["maximum"])) for control in controls]
    if any(low >= high for low, high in intervals):
        raise ValueError("Invalid fit interval")
    for target in targets:
        finite_number(target["target_m"])
        finite_number(target.get("tolerance_m", 1e-5), "target tolerance", 1e-12)
        if target.get("axis") not in [0, 1, 2]:
            raise ValueError("Target axis must be 0, 1 or 2")
    trials = []
    best = [max(low,min(high,finite_number(value,"initial fit control")))
            for value,(low,high) in zip(originals,intervals)]
    best_cost = math.inf
    steps = [(high-low)/4 for low, high in intervals]
    def candidate(values):
        nonlocal best, best_cost
        for (_, setter), value in zip(access, values):
            setter(value)
        bpy.context.view_layer.update()
        check = check_contract(baseline)
        measurements = []
        cost = math.inf
        if check["status"] == "PASS":
            measurements = [target_value(target) for target in targets]
            cost = sum(((measured-target["target_m"])/target.get("tolerance_m", 1e-5))**2
                       for measured, target in zip(measurements, targets))
        trials.append({"controls": list(values), "constraint_status": check["status"],
                       "measurements_m": measurements, "cost": cost if math.isfinite(cost) else None})
        if cost < best_cost:
            best, best_cost = list(values), cost
    candidate(best)
    while len(trials) < budget and best_cost > 1:
        improved = False
        for index, ((low, high), step) in enumerate(zip(intervals, steps)):
            previous = best_cost
            center = list(best)
            for direction in [-1, 1]:
                if len(trials) >= budget:
                    break
                values = list(center)
                values[index] = max(low, min(high, center[index]+direction*step))
                candidate(values)
            improved |= best_cost < previous
        if not improved:
            steps = [step*.5 for step in steps]
    for (_, setter), value in zip(access, best):
        setter(value)
    bpy.context.view_layer.update()
    measurements = [target_value(target) for target in targets]
    accepted = all(abs(measured-target["target_m"]) <= target.get("tolerance_m", 1e-5)
                   for measured, target in zip(measurements, targets))
    if not accepted:
        error = ValueError("Fit exhausted its bounded budget without reaching all target tolerances")
        error.trials = trials
        raise error
    return {"operation": "fit_controls", "before": originals, "after": best,
            "target_status": "PASS", "measurements_m": measurements, "trials": trials}


def apply_plan(plan, output, report_path=None):
    output = Path(output).resolve()
    if output.suffix.lower() != ".blend" or output.exists():
        raise ValueError("Edit output must be a new .blend file")
    if report_path and Path(report_path).exists():
        raise ValueError("Edit report must be a new file")
    if report_path and (Path(report_path).resolve() == output or Path(report_path).suffix.lower() != ".json"):
        raise ValueError("Use a distinct new JSON report path")
    source = source_identity()
    if source["source_sha256"] is not None and not all(key in plan for key in
            ["source_sha256", "frame", "metres_per_blender_unit"]):
        raise ValueError("A saved-source edit needs its file hash, frame and physical unit scale")
    expected = plan.get("source_sha256")
    if expected is not None and expected != source["source_sha256"]:
        raise ValueError("Edit request belongs to another source revision")
    if plan.get("frame", source["frame"]) != source["frame"] or \
            plan.get("metres_per_blender_unit", source["metres_per_blender_unit"]) != source["metres_per_blender_unit"]:
        raise ValueError("Edit request frame or physical unit scale is stale")
    if plan.get("schema_version") != 2 or not plan.get("operations"):
        raise ValueError("Expected a version 2 plan with explicit operations")
    baseline = capture_contract(plan["constraints"])
    transaction = Transaction()
    report = {"schema_version": 2, "source": source, "baseline": baseline,
              "operations": [], "artistic_quality": "NOT_CHECKED", "global_collision": "NOT_CHECKED"}
    try:
        for operation in plan["operations"]:
            kind = operation.get("kind")
            if kind == "set_control":
                result = set_control(operation["control"], operation["value"], transaction)
            elif kind == "deform":
                result = deform(operation, transaction)
            elif kind == "repair_degenerate":
                result = repair(operation, transaction)
            elif kind == "assign_base_color":
                result = assign_base_color(operation, transaction)
            elif kind == "fit_controls":
                result = fit(operation, baseline, transaction)
            else:
                raise ValueError("Unsupported operation: " + str(kind))
            report["operations"].append(result)
        report["acceptance"] = check_contract(baseline)
        if report["acceptance"]["status"] != "PASS":
            raise ValueError("A protected constraint failed or could not be verified")
        output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output))
        report.update(status="PASS", output=str(output))
    except Exception as error:
        transaction.rollback()
        report.update(status="FAIL", reason=str(error), output=None,
                      rollback=check_contract(baseline), trials=getattr(error, "trials", []))
        if "acceptance" not in report:
            report["acceptance"] = {"status": "FAIL", "reason": str(error)}
    if report_path:
        write_new(report_path, report)
    return report
