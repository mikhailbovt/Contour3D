"""Evaluated geometry, instance-aware diagnostics and measured sections."""
from __future__ import annotations

from contextlib import contextmanager
import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .common import digest, finite_number, object_key, resolve_objects, source_identity, units, vector

GEOMETRY_TYPES = {"MESH", "CURVE", "SURFACE", "FONT", "META"}


@contextmanager
def evaluated_mesh(obj):
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(graph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
    if mesh is None:
        raise ValueError("Object has no evaluated mesh: " + obj.name)
    try:
        mesh.calc_loop_triangles()
        yield mesh, evaluated.matrix_world
    finally:
        evaluated.to_mesh_clear()


def arrays(mesh, matrix=None, scale=1.0):
    positions = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", positions)
    positions = positions.reshape((-1, 3))
    if matrix is not None:
        transform = np.asarray(matrix, dtype=np.float64)
        positions = (positions @ transform[:3, :3].T + transform[:3, 3]) * scale
    mesh.calc_loop_triangles()
    triangles = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", triangles)
    return positions, triangles.reshape((-1, 3))


def bounds(positions):
    if not len(positions):
        return None
    return {"minimum_m": positions.min(axis=0).tolist(),
            "maximum_m": positions.max(axis=0).tolist(),
            "extent_m": np.ptp(positions, axis=0).tolist()}


def topology_signature(mesh):
    return digest({"vertices": len(mesh.vertices),
                   "faces": [list(polygon.vertices) for polygon in mesh.polygons]})


def uv_diagnostics(mesh, positions, triangles):
    layer = mesh.uv_layers.active
    if layer is None:
        return {"status": "NOT_CHECKED", "reason": "No active UV layer; UVs may be unnecessary for this use."}
    if not len(triangles):
        return {"status": "UNKNOWN", "reason": "No triangles."}
    loop_indices = np.asarray([list(tri.loops) for tri in mesh.loop_triangles], dtype=np.int32)
    uv = np.asarray([list(item.uv) for item in layer.data], dtype=np.float64)[loop_indices]
    world = positions[triangles]
    a, b = world[:, 1] - world[:, 0], world[:, 2] - world[:, 0]
    du, dv = uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]
    length = np.linalg.norm(a, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        projection = np.sum(a*b, axis=1) / length
        height = np.sqrt(np.maximum(0, np.sum(b*b, axis=1)-projection**2))
        first = du / length[:, None]
        second = (dv - first*projection[:, None]) / height[:, None]
        gram_a = np.sum(first*first, axis=1)
        gram_c = np.sum(second*second, axis=1)
        gram_b = np.sum(first*second, axis=1)
        discr = np.sqrt(np.maximum(0, (gram_a-gram_c)**2+4*gram_b**2))
        low, high = (gram_a+gram_c-discr)*.5, (gram_a+gram_c+discr)*.5
        anisotropy = np.sqrt(high / low)
    area_uv = np.abs(du[:, 0]*dv[:, 1]-du[:, 1]*dv[:, 0])*.5
    area_world = np.linalg.norm(np.cross(a, b), axis=1)*.5
    valid = np.isfinite(anisotropy) & (low > 1e-20) & (area_world > 1e-18)
    data = {"status": "MEASURED", "layer": layer.name,
            "collapsed_uv_triangles": int(np.sum((area_uv <= 1e-14) & (area_world > 1e-18))),
            "measured_triangles": int(np.sum(valid)),
            "limitations": "Local triangle anisotropy only; overlaps, island padding and target texel density require separate acceptance."}
    if np.any(valid):
        data["anisotropy_median"] = float(np.median(anisotropy[valid]))
        data["anisotropy_p95"] = float(np.percentile(anisotropy[valid], 95))
        density = np.sqrt(area_uv[valid]/area_world[valid])
        data["uv_units_per_m_median"] = float(np.median(density))
        worst = np.flatnonzero(valid)[np.argsort(anisotropy[valid])[-8:][::-1]]
        data["largest_distortions"] = [{"triangle": int(index), "ratio": float(anisotropy[index]),
                                        "location_m": world[index].mean(axis=0).tolist()} for index in worst]
    return data


def section_segments(positions, triangles, normal, offset_m, epsilon=1e-9, max_segments=20000):
    offset_m = finite_number(offset_m, "section offset")
    epsilon = finite_number(epsilon, "section tolerance", 1e-15)
    normal = np.asarray(vector(normal), dtype=np.float64)
    norm = np.linalg.norm(normal)
    if norm < 1e-12:
        raise ValueError("Section normal must be nonzero")
    normal /= norm
    distances = positions @ normal - offset_m
    segments, coplanar = [], 0
    possible = triangles[(distances[triangles].min(axis=1) <= epsilon) &
                         (distances[triangles].max(axis=1) >= -epsilon)]
    truncated = False
    for triangle in possible:
        ds = distances[triangle]
        if np.all(np.abs(ds) <= epsilon):
            coplanar += 1
            continue
        points = []
        for i, j in [(0, 1), (1, 2), (2, 0)]:
            p, q = positions[triangle[i]], positions[triangle[j]]
            if abs(ds[i]) <= epsilon:
                points.append(p)
            if ds[i]*ds[j] < -epsilon**2:
                points.append(p + (q-p)*(ds[i]/(ds[i]-ds[j])))
        unique = []
        for point in points:
            if not any(np.linalg.norm(point-other) <= epsilon for other in unique):
                unique.append(point)
        if len(unique) == 2:
            segments.append([unique[0].tolist(), unique[1].tolist()])
            if len(segments) >= max_segments:
                truncated = True
                break
    return {"normal": normal.tolist(), "offset_m": offset_m, "segments": segments,
            "coplanar_triangles_omitted": coplanar, "truncated": truncated,
            "scope": "Triangle-plane intersections in evaluated world geometry, in metres; not analytic CAD sections."}


def sampled_thickness(positions, triangles, count=48):
    if not len(triangles):
        return {"status": "UNKNOWN", "reason": "Empty mesh"}
    tree = BVHTree.FromPolygons([Vector(point) for point in positions], triangles.tolist(), all_triangles=True)
    span = max(float(np.ptp(positions, axis=0).max()), 1e-6)
    epsilon = span*1e-6
    samples = []
    indices = np.linspace(0, len(triangles)-1, min(count, len(triangles)), dtype=int)
    for index in indices:
        points = positions[triangles[index]]
        normal = np.cross(points[1]-points[0], points[2]-points[0])
        length = np.linalg.norm(normal)
        if length <= 1e-18:
            continue
        normal /= length
        origin = points.mean(axis=0)
        hit, hit_normal, face, distance = tree.ray_cast(Vector(origin-normal*epsilon), Vector(-normal), span*2)
        samples.append({"triangle": int(index), "location_m": origin.tolist(),
                        "distance_m": float(distance+epsilon) if hit is not None else None})
    distances = [sample["distance_m"] for sample in samples if sample["distance_m"] is not None]
    return {"status": "MEASURED" if distances else "UNKNOWN", "samples": samples,
            "minimum_sampled_distance_m": min(distances) if distances else None,
            "missed_rays": sum(sample["distance_m"] is None for sample in samples),
            "scope": "Directional inward ray samples. Can hit another feature, depend on winding and miss thinner walls. Not a global minimum thickness certificate."}


def mesh_diagnostics(mesh, matrix, scale=1.0, thickness=False):
    positions, triangles = arrays(mesh, matrix, scale)
    if not np.isfinite(positions).all():
        raise ValueError("Nonfinite evaluated vertex coordinates")
    points = positions[triangles]
    cross = np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0])
    area = np.linalg.norm(cross, axis=1)*.5
    edge_faces = [[] for _ in mesh.edges]
    for polygon in mesh.polygons:
        for loop in polygon.loop_indices:
            edge_faces[mesh.loops[loop].edge_index].append(polygon.index)
    face_normals = []
    for polygon in mesh.polygons:
        indices = list(polygon.vertices)
        origin = positions[indices[0]]
        normal = np.zeros(3)
        for i in range(1, len(indices)-1):
            normal += np.cross(positions[indices[i]]-origin, positions[indices[i+1]]-origin)
        length = np.linalg.norm(normal)
        face_normals.append(normal/length if length > 1e-18 else normal)
    creases = mesh.attributes.get("crease_edge")
    variations = []
    for index, faces in enumerate(edge_faces):
        if len(faces) != 2:
            continue
        edge = mesh.edges[index]
        p, q = positions[list(edge.vertices)]
        length = float(np.linalg.norm(p-q))
        cosine = float(np.clip(np.dot(face_normals[faces[0]], face_normals[faces[1]]), -1, 1))
        angle = math.degrees(math.acos(cosine))
        sharp = bool(edge.use_edge_sharp) or bool(creases and creases.data[index].value > 0)
        variations.append({"edge": index, "angle_degrees": angle,
                           "normal_variation_per_m": math.radians(angle)/max(length, 1e-12),
                           "marked_sharp_or_creased": sharp, "location_m": ((p+q)*.5).tolist()})
    smooth = [item for item in variations if not item["marked_sharp_or_creased"]]
    tiny = np.flatnonzero(area <= 1e-12)
    result = {"vertices": len(positions), "polygons": len(mesh.polygons), "triangles": len(triangles),
              "bounds": bounds(positions), "topology_signature": topology_signature(mesh),
              "boundary_edges": sum(len(items) == 1 for items in edge_faces),
              "wire_edges": sum(not items for items in edge_faces),
              "edges_with_more_than_two_faces": sum(len(items) > 2 for items in edge_faces),
              "triangles_at_or_below_1e-12_m2": len(tiny),
              "tiny_triangle_locations_m": points[tiny[:32]].mean(axis=1).tolist(),
              "largest_unmarked_normal_variations": sorted(smooth, key=lambda item: item["normal_variation_per_m"], reverse=True)[:12],
              "curvature_scope": "Discrete dihedral/edge-length signal; scale/tessellation dependent, not principal curvature or G2 certification. Unmarked intended creases can appear here.",
              "uv": uv_diagnostics(mesh, positions, triangles), "artistic_quality": "NOT_CHECKED",
              "self_intersection": "NOT_CHECKED"}
    if thickness:
        result["thickness"] = sampled_thickness(positions, triangles)
    return result


def inspect_scene(names=None, include_instances=True, thickness=False, sections=None):
    selected = resolve_objects(names)
    selected_keys = {object_key(obj) for obj in selected}
    graph = bpy.context.evaluated_depsgraph_get()
    scale = units(bpy.context.scene)
    objects = []
    for obj in selected:
        if obj.type not in GEOMETRY_TYPES:
            continue
        with evaluated_mesh(obj) as (mesh, matrix):
            record = {"id": object_key(obj), "name": obj.name, "type": obj.type,
                      "hide_render": obj.hide_render, "role": str(obj.get("role", "")),
                      "evaluated": mesh_diagnostics(mesh, matrix, scale, thickness),
                      "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
                      "render_modifier_differences": [m.name for m in obj.modifiers if m.show_viewport != m.show_render]}
            if obj.type == "MESH":
                record["source"] = mesh_diagnostics(obj.data, obj.matrix_world, scale)
            if sections:
                positions, triangles = arrays(mesh, matrix, scale)
                record["sections"] = [section_segments(positions, triangles, section["normal"], section["offset_m"]) for section in sections]
            objects.append(record)
    instances = []
    if include_instances:
        for instance in graph.object_instances:
            if not instance.is_instance or instance.object.type not in GEOMETRY_TYPES:
                continue
            original = instance.object.original
            parent = instance.parent.original if instance.parent else None
            if names is not None and object_key(original) not in selected_keys and (parent is None or object_key(parent) not in selected_keys):
                continue
            mesh = instance.object.to_mesh(preserve_all_data_layers=True, depsgraph=graph)
            if mesh is None:
                continue
            try:
                mesh.calc_loop_triangles()
                positions, triangles = arrays(mesh, instance.matrix_world, scale)
                instances.append({"id": digest([object_key(original), list(instance.persistent_id), [list(row) for row in instance.matrix_world]]),
                                  "source_object": original.name, "source_id": object_key(original),
                                  "parent": parent.name if parent else None,
                                  "triangles": len(triangles), "bounds": bounds(positions),
                                  "matrix_world": [list(row) for row in instance.matrix_world]})
            finally:
                instance.object.to_mesh_clear()
    report = {"schema_version": 2, **source_identity(), "objects": objects, "instances": instances,
              "evaluated_object_triangles": sum(item["evaluated"]["triangles"] for item in objects),
              "additional_instance_triangles": sum(item["triangles"] for item in instances),
              "measurement_scope": "Current viewport dependency graph at current frame. Converted meshes/curves/surfaces/text and optional collection/GN instances. Original hidden objects are labelled; render-only modifier differences are disclosed. Volumes, particles not represented as instances, full animation and render-only graph are unmeasured.",
              "quality_status": "NOT_CHECKED"}
    report["revision"] = digest(report)
    return report
