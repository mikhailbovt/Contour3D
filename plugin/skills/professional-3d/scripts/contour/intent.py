"""Scoped fingerprints and region contracts for meaningful native edits."""
from __future__ import annotations

import math
import bpy
import numpy as np

from .common import digest, file_hash, finite_number, object_key, resolve_objects, source_identity, units, vector
from .geometry import arrays, bounds, evaluated_mesh, topology_signature, GEOMETRY_TYPES

FINGERPRINT_VERSION = "intent-3"


def scalar(value):
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, bpy.types.ID):
        return {"id_type": type(value).__name__, "name": value.name_full,
                "library": value.library.filepath if value.library else None}
    try:
        return [scalar(item) for item in value]
    except TypeError:
        return type(value).__name__


def rna_values(item, excluded=()):
    result = {}
    for prop in item.bl_rna.properties:
        name = prop.identifier
        if name in excluded or name == "rna_type" or prop.type == "COLLECTION" or prop.is_readonly:
            continue
        try:
            value = getattr(item, name)
            if prop.type != "POINTER" or isinstance(value, bpy.types.ID) or value is None:
                result[name] = scalar(value)
        except (AttributeError, RuntimeError, TypeError):
            result[name] = "NOT_CHECKED"
    return result


def driver_state(datablock):
    animation = getattr(datablock, "animation_data", None)
    if not animation:
        return []
    return [{"path": curve.data_path, "index": curve.array_index, "mute":curve.mute,
             "type":curve.driver.type,"expression":curve.driver.expression,
             "variables":[{"name":variable.name,"type":variable.type,
                           "targets":[{"id":scalar(target.id),"path":target.data_path,
                                        "bone":target.bone_target,"transform_type":target.transform_type,
                                        "transform_space":target.transform_space} for target in variable.targets]}
                          for variable in curve.driver.variables]} for curve in animation.drivers]


def shader_state(tree, stack=()):
    if tree is None:
        return None
    if tree.as_pointer() in stack:
        return {"cycle": tree.name}
    stack = (*stack, tree.as_pointer())
    nodes = []
    for node in sorted(tree.nodes, key=lambda item: item.name):
        entry = {"name": node.name, "type": node.bl_idname,
                 "properties": rna_values(node, {"location", "width", "height", "select", "color", "use_custom_color", "label", "parent", "node_tree"}),
                 "inputs": [{"name": socket.name, "identifier": socket.identifier,
                             "default": scalar(socket.default_value) if hasattr(socket, "default_value") else None}
                            for socket in node.inputs],
                 "outputs": [{"name": socket.name, "identifier": socket.identifier,
                              "default": scalar(socket.default_value) if hasattr(socket, "default_value") else None}
                             for socket in node.outputs]}
        if getattr(node, "node_tree", None):
            entry["group"] = shader_state(node.node_tree, stack)
        image = getattr(node, "image", None)
        if image:
            path = bpy.path.abspath(image.filepath, library=image.library)
            from pathlib import Path
            packed = image.packed_file
            entry["image"] = {"name": image.name, "source": image.source,
                              "colorspace": image.colorspace_settings.name,
                              "size": list(image.size),
                              "resource_path":str(Path(path).resolve()) if not packed and path else None,
                              "file_sha256": file_hash(path) if not packed and path and Path(path).is_file() else None,
                              "packed_sha256": __import__("hashlib").sha256(packed.data).hexdigest() if packed else None}
            if image.source == "GENERATED":
                data = np.empty(len(image.pixels), dtype=np.float32)
                image.pixels.foreach_get(data)
                entry["image"]["generated_pixels_sha256"] = __import__("hashlib").sha256(data.tobytes()).hexdigest()
        # Ramp control points are not writable RNA scalar fields.
        ramp = getattr(node, "color_ramp", None)
        if ramp:
            entry["ramp"] = {"interpolation": ramp.interpolation, "color_mode": ramp.color_mode,
                             "hue_interpolation": ramp.hue_interpolation,
                             "elements": [{"position": point.position, "color": list(point.color)} for point in ramp.elements]}
        nodes.append(entry)
    return {"nodes": nodes, "drivers":driver_state(tree), "links": sorted((link.from_node.name, link.from_socket.identifier,
                                               link.to_node.name, link.to_socket.identifier) for link in tree.links)}


def material_state(obj):
    return [{"name": slot.material.name if slot.material else None,
             "link": slot.link,
             "properties": rna_values(slot.material, {"node_tree", "preview", "name"}) if slot.material else None,
             "shader": shader_state(slot.material.node_tree) if slot.material else None}
            for slot in obj.material_slots]


def mesh_state(mesh, evaluated=False):
    return {"positions": [list(vertex.co) for vertex in mesh.vertices],
            "faces": [list(polygon.vertices) for polygon in mesh.polygons],
            "smooth": [polygon.use_smooth for polygon in mesh.polygons],
            "material_indices": [polygon.material_index for polygon in mesh.polygons],
            "uv": {layer.name: [[round(float(value), 5) if evaluated else float(value) for value in item.uv]
                                for item in layer.data] for layer in mesh.uv_layers},
            "sharp_edges": [edge.use_edge_sharp for edge in mesh.edges]}


def object_state(obj):
    geometry = None
    if obj.type in GEOMETRY_TYPES:
        with evaluated_mesh(obj) as (mesh, matrix):
            geometry = {"evaluated": mesh_state(mesh, evaluated=True)}
            if obj.type == "MESH":
                geometry["source"] = mesh_state(obj.data)
                keys = obj.data.shape_keys
                if keys:
                    geometry["shape_keys"] = [{"name": key.name, "value": key.value,
                                                "positions": [list(point.co) for point in key.data]}
                                               for key in keys.key_blocks]
    modifiers = []
    for modifier in obj.modifiers:
        entry = {"type": modifier.type, "properties": rna_values(modifier),
                 "custom_inputs": {key: scalar(modifier[key]) for key in modifier.keys()} if modifier.type == "NODES" else {}}
        if modifier.type == "NODES":
            entry["node_group"] = shader_state(modifier.node_group)
        modifiers.append(entry)
    dependencies = {"modifiers": modifiers,"drivers": driver_state(obj),
                    "shape_key_drivers": driver_state(obj.data.shape_keys) if obj.type == "MESH" and obj.data.shape_keys else [],
                    "parent": object_key(obj.parent) if obj.parent else None,
                    "constraints": [rna_values(constraint) for constraint in obj.constraints]}
    structure = {**dependencies,"modifiers":[{**entry,"custom_inputs":{}} for entry in modifiers]}
    return {"id": object_key(obj), "name": obj.name,
            "geometry": digest(geometry), "transform": digest([list(row) for row in obj.matrix_world]),
            "materials": digest(material_state(obj)),
            "dependencies": digest(dependencies), "dependency_structure":digest(structure),
            "coverage": "Source/evaluated mesh coordinates, face topology, source UVs, smoothing, material assignments, shape keys, current-frame transforms, shader/group socket defaults/links/ramps/image bytes, modifiers and object constraints. Evaluated UV hashes quantize to 5 decimal places because Blender bevel interpolation varies by a float ULP; geometry contracts also compare their raw values with a declared tolerance. Full animation, simulation caches, UDIM sequences and arbitrary nested non-ID RNA pointers are not certified."}


def evaluated_uv(obj):
    if obj.type not in GEOMETRY_TYPES:
        return {}
    with evaluated_mesh(obj) as (mesh, matrix):
        return {layer.name: [list(item.uv) for item in layer.data] for layer in mesh.uv_layers}


def compare_uv(old, current, tolerance):
    if set(old) != set(current):
        return False, None
    maximum = 0.0
    for name, values in old.items():
        if len(values) != len(current[name]):
            return False, None
        if values:
            maximum = max(maximum, float(np.abs(np.asarray(values)-current[name]).max()))
    return maximum <= tolerance, maximum


def snapshot(names=None):
    report = {"schema_version": 2, "fingerprint_version":FINGERPRINT_VERSION, **source_identity(),
              "objects": {obj.name: object_state(obj) for obj in resolve_objects(names)}}
    report["revision"] = digest(report)
    return report


def select_vertices(obj, mesh, positions, selector, evaluated=False):
    if not isinstance(selector, dict):
        raise ValueError("Region selector must be an object")
    kind = selector.get("kind")
    if kind == "attribute":
        attribute = mesh.attributes.get(selector["name"])
        if not attribute or attribute.domain != "POINT" or attribute.data_type not in {"FLOAT", "INT", "BOOLEAN"}:
            raise ValueError("Missing scalar point attribute: " + selector["name"])
        threshold = finite_number(selector.get("threshold", .999), "attribute threshold")
        indices = [i for i, value in enumerate(attribute.data) if value.value >= threshold]
    elif kind == "vertex_group":
        if evaluated:
            raise ValueError("Use a point attribute for evaluated region correspondence")
        group = obj.vertex_groups.get(selector["name"])
        if group is None:
            raise ValueError("Missing vertex group: " + selector["name"])
        threshold = finite_number(selector.get("threshold", .999), "group threshold", 0, 1)
        indices = [vertex.index for vertex in mesh.vertices
                   if any(link.group == group.index and link.weight >= threshold for link in vertex.groups)]
    elif kind == "sphere":
        center = np.asarray(vector(selector["center_m"]))
        radius = float(selector["radius_m"])
        if not math.isfinite(radius) or radius <= 0:
            raise ValueError("Region radius must be positive")
        indices = np.flatnonzero(np.linalg.norm(positions-center, axis=1) <= radius).tolist()
    elif kind == "indices":
        indices = selector["indices"]
        if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= len(mesh.vertices) for i in indices):
            raise ValueError("Invalid region indices")
        if selector.get("topology_signature") != topology_signature(mesh):
            raise ValueError("Region topology signature is stale")
    else:
        raise ValueError("Unsupported selector: " + str(kind))
    if not indices:
        raise ValueError("Region selects no vertices")
    return sorted(set(indices))


def capture_region(obj, selector, evaluated=True):
    def capture(mesh, matrix):
        positions, _ = arrays(mesh, matrix, units(bpy.context.scene))
        indices = select_vertices(obj, mesh, positions, selector, evaluated)
        normal_transform = matrix.to_3x3().inverted_safe().transposed()
        normals = [(normal_transform @ mesh.vertices[index].normal).normalized() for index in indices]
        return {"topology_signature": topology_signature(mesh), "indices": indices,
                "positions_m": positions[indices].tolist(), "normals": [list(normal) for normal in normals]}
    if evaluated:
        with evaluated_mesh(obj) as (mesh, matrix):
            return capture(mesh, matrix)
    if obj.type != "MESH":
        raise ValueError("Source region requires a mesh")
    return capture(obj.data, obj.matrix_world)


def capture_contract(constraints):
    if not isinstance(constraints, list) or not constraints:
        raise ValueError("A constrained edit needs at least one explicit invariant")
    records = []
    for rule in constraints:
        obj = bpy.context.scene.objects.get(rule.get("object", ""))
        if obj is None:
            raise ValueError("Constraint object missing: " + str(rule.get("object")))
        kind = rule.get("kind")
        if kind == "object_unchanged":
            properties = rule.get("properties", ["geometry", "transform", "materials", "dependencies"])
            if not properties or set(properties)-{"geometry", "transform", "materials", "dependencies", "dependency_structure"}:
                raise ValueError("Unsupported protected property")
            record = {"rule": rule, "state": object_state(obj)}
            if "geometry" in properties:
                finite_number(rule.get("evaluated_uv_tolerance", 1e-6), "evaluated UV tolerance", 0)
                record["evaluated_uv"] = evaluated_uv(obj)
        elif kind == "region_position":
            finite_number(rule.get("tolerance_m", 0), "region tolerance", 0)
            if "normal_tolerance_degrees" in rule:
                finite_number(rule["normal_tolerance_degrees"], "normal tolerance", 0, 180)
            record = {"rule": rule, "region": capture_region(obj, rule["selector"], rule.get("evaluated", True))}
        elif kind == "bounds_unchanged":
            finite_number(rule.get("tolerance_m", 0), "bounds tolerance", 0)
            with evaluated_mesh(obj) as (mesh, matrix):
                positions, _ = arrays(mesh, matrix, units(bpy.context.scene))
                record = {"rule": rule, "bounds": bounds(positions)}
            if record["bounds"] is None:
                raise ValueError("Cannot protect empty bounds")
        else:
            raise ValueError("Unsupported constraint kind: " + str(kind))
        records.append(record)
    return {"schema_version": 2, "fingerprint_version":FINGERPRINT_VERSION, **source_identity(), "records": records,
            "scope": "Explicit object properties and selected current-frame region positions; optional sampled normals. PASS only covers those properties."}


def check_contract(baseline):
    if baseline.get("fingerprint_version") != FINGERPRINT_VERSION:
        return {"status":"FAIL","checks":[],"reason":"Fingerprint algorithm changed; recapture this contract on the original source", "artistic_quality":"NOT_CHECKED"}
    checks = [{"kind": "scene_context", "status": "PASS" if
               bpy.context.scene.frame_current == baseline["frame"] and
               units(bpy.context.scene) == baseline["metres_per_blender_unit"] else "FAIL",
               "coverage": "Captured frame and physical unit scale"}]
    for record in baseline["records"]:
        rule = record["rule"]
        obj = bpy.context.scene.objects.get(rule["object"])
        result = {"kind": rule["kind"], "object": rule["object"]}
        if obj is None:
            result.update(status="FAIL", reason="Protected object missing")
        elif rule["kind"] == "object_unchanged":
            current = object_state(obj)
            properties = rule.get("properties", ["geometry", "transform", "materials", "dependencies"])
            changed = [prop for prop in properties if current[prop] != record["state"][prop]]
            if "geometry" in properties:
                uv_ok, uv_shift = compare_uv(record["evaluated_uv"], evaluated_uv(obj),
                                             rule.get("evaluated_uv_tolerance", 1e-6))
                result["maximum_evaluated_uv_shift"] = uv_shift
                result["evaluated_uv_tolerance"] = rule.get("evaluated_uv_tolerance", 1e-6)
                if not uv_ok and "geometry" not in changed:
                    changed.append("geometry")
            result.update(status="FAIL" if changed else "PASS", changed_properties=changed,
                          coverage=current["coverage"])
        elif rule["kind"] == "bounds_unchanged":
            with evaluated_mesh(obj) as (mesh, matrix):
                positions, _ = arrays(mesh, matrix, units(bpy.context.scene))
                current = bounds(positions)
            if current is None:
                result.update(status="FAIL", reason="Protected geometry is empty")
            else:
                shift = max(abs(current[key][i]-record["bounds"][key][i])
                            for key in ["minimum_m", "maximum_m"] for i in range(3))
                result.update(status="PASS" if shift <= rule.get("tolerance_m", 0) else "FAIL",
                              maximum_bound_shift_m=shift, coverage="Bounding box only; does not certify full silhouette or interior shape")
        else:
            try:
                current = capture_region(obj, rule["selector"], rule.get("evaluated", True))
                old = record["region"]
                if current["topology_signature"] != old["topology_signature"] or current["indices"] != old["indices"]:
                    result.update(status="UNKNOWN", reason="Region correspondence changed; resolve it on the new topology")
                else:
                    delta = np.asarray(current["positions_m"])-np.asarray(old["positions_m"])
                    maximum = float(np.linalg.norm(delta, axis=1).max())
                    result.update(status="PASS" if maximum <= rule.get("tolerance_m", 0) else "FAIL",
                                  samples=len(delta), maximum_shift_m=maximum, tolerance_m=rule.get("tolerance_m", 0))
                    if "normal_tolerance_degrees" in rule:
                        dot = np.sum(np.asarray(current["normals"])*np.asarray(old["normals"]), axis=1)
                        angle = float(np.degrees(np.arccos(np.clip(dot, -1, 1))).max())
                        result["maximum_normal_change_degrees"] = angle
                        if angle > rule["normal_tolerance_degrees"]:
                            result["status"] = "FAIL"
            except (ValueError, RuntimeError) as error:
                result.update(status="UNKNOWN", reason=str(error))
        checks.append(result)
    return {"status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
            "checks": checks, "scope": baseline["scope"], "artistic_quality": "NOT_CHECKED",
            "global_collision": "NOT_CHECKED", "full_animation": "NOT_CHECKED"}
