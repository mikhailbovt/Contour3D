"""Original executable construction episodes. Not externally certified assets."""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import uuid
import bpy
import bmesh

from .common import finite_number

ASSETS = Path(__file__).resolve().parents[2]/"assets"


def housing_module():
    spec = importlib.util.spec_from_file_location("contour_housing", ASSETS/"curved_housing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mesh(name, vertices, faces, material, role="surface"):
    obj = housing_module().mesh_object(name, vertices, faces, material, role)
    obj["contour_id"] = str(uuid.uuid4())
    return obj


def materials():
    example = housing_module()
    return {"coat": example.material("Deep teal ceramic coating", (.024, .14, .15), .15, .32),
            "metal": example.material("Satin aluminium", (.42, .48, .51), .85, .28),
            "polymer": example.material("Graphite engineering polymer", (.026, .037, .043), 0, .46),
            "accent": example.material("Amber identification", (.9, .43, .055), .1, .42)}


def prepare():
    if bpy.data.filepath:
        raise ValueError("Construction episodes require a fresh scene, not a user's loaded project")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    return materials()


def cube(name, dimensions, location, material, bevel=.001):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    housing_module().bevel(obj, bevel, 3)
    obj["contour_id"] = str(uuid.uuid4())
    return obj


def cylinder(name, radius, depth, location, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = len(polygon.vertices) == 4
    housing_module().bevel(obj, .0005, 2)
    obj["contour_id"] = str(uuid.uuid4())
    return obj


def crown_source(obj, width, depth, crown=.016, seat=.30, driver_source=None):
    group = bpy.data.node_groups.new(obj.name+" retained crown field", "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    value = group.interface.new_socket(name="Crown (m)", in_out="INPUT", socket_type="NodeSocketFloat")
    value.default_value = crown
    value.min_value, value.max_value = 0, .045
    input_node = group.nodes.new("NodeGroupInput")
    output_node = group.nodes.new("NodeGroupOutput")
    pos = group.nodes.new("GeometryNodeInputPosition")
    separate = group.nodes.new("ShaderNodeSeparateXYZ")
    group.links.new(pos.outputs[0], separate.inputs[0])
    def arithmetic(operation, a, b=None):
        node = group.nodes.new("ShaderNodeMath")
        node.operation = operation
        for index, item in enumerate([a, b]):
            if isinstance(item, (int, float)):
                node.inputs[index].default_value = item
            elif item is not None:
                group.links.new(item, node.inputs[index])
        return node.outputs[0]
    x = arithmetic("POWER", arithmetic("DIVIDE", separate.outputs["X"], width/2), 4)
    y = arithmetic("POWER", arithmetic("DIVIDE", separate.outputs["Y"], depth/2), 4)
    inside = arithmetic("SUBTRACT", 1, arithmetic("ADD", x, y))
    weight = arithmetic("POWER", arithmetic("MAXIMUM", 0, arithmetic("DIVIDE", arithmetic("SUBTRACT", inside, seat), 1-seat)), 2)
    magnitude = arithmetic("MULTIPLY", weight, input_node.outputs["Crown (m)"])
    combine = group.nodes.new("ShaderNodeCombineXYZ")
    group.links.new(magnitude, combine.inputs["Z"])
    set_position = group.nodes.new("GeometryNodeSetPosition")
    group.links.new(input_node.outputs["Geometry"], set_position.inputs["Geometry"])
    group.links.new(combine.outputs[0], set_position.inputs["Offset"])
    group.links.new(set_position.outputs[0], output_node.inputs[0])
    modifier = obj.modifiers.new("Retained crown", "NODES")
    modifier.node_group = group
    modifier[value.identifier] = crown
    source = driver_source or obj
    if driver_source is None:
        obj["crown_m"] = crown
        obj["contour_controls"] = json.dumps([{"property": "crown_m", "label": "Crown (m)", "minimum": 0, "maximum": .045}])
    fcurve = modifier.driver_add('["'+value.identifier+'"]')
    driver = fcurve.driver
    driver.type = "SCRIPTED"
    driver.expression = "crown"
    variable = driver.variables.new()
    variable.name = "crown"
    variable.type = "SINGLE_PROP"
    variable.targets[0].id = source
    variable.targets[0].data_path = '["crown_m"]'
    return modifier


def disk_surface(name, width, depth, z, material, bands=14, sectors=64):
    outline = housing_module().shell_loop(width, depth, sectors)
    vertices = [(0, 0, z)]
    for ring in range(1, bands+1):
        vertices.extend((x*ring/bands, y*ring/bands, z) for x, y in outline)
    faces = [(0, 1+j, 1+(j+1)%sectors) for j in range(sectors)]
    for ring in range(bands-1):
        a, b = 1+ring*sectors, 1+(ring+1)*sectors
        faces.extend((a+j, b+j, b+(j+1)%sectors, a+(j+1)%sectors) for j in range(sectors))
    obj = mesh(name, vertices, faces, material)
    rim = obj.data.attributes.new("seat", "FLOAT", "POINT")
    for point in list(rim.data)[1+(bands-1)*sectors:]:
        point.value = 1
    return obj


def loft_episode():
    mats = prepare()
    # Sparse native subdivision cage: landmarks share angular correspondence.
    stations = [(0, .040, .032, -.015), (.004, .040, .032, -.015),
                (.045, .067, .040, -.003), (.110, .060, .038, .015),
                (.171, .035, .030, .024), (.175, .035, .030, .024)]
    count = 32
    vertices = [(cx+rx*math.cos(2*math.pi*j/count), ry*math.sin(2*math.pi*j/count), z)
                for z, rx, ry, cx in stations for j in range(count)]
    faces = [(i*count+j, i*count+(j+1)%count, (i+1)*count+(j+1)%count, (i+1)*count+j)
             for i in range(len(stations)-1) for j in range(count)]
    obj = mesh("Asymmetric transition source", vertices, faces, mats["coat"])
    obj.shape_key_add(name="Basis")
    key = obj.shape_key_add(name="Shoulder spread")
    for i, point in enumerate(key.data):
        ring = i//count
        if ring in [2, 3]:
            point.co.x += .012*math.cos(2*math.pi*(i%count)/count)
    rim = obj.data.attributes.new("fixed_ends", "FLOAT", "POINT")
    for i, datum in enumerate(rim.data):
        datum.value = 1 if i//count in [0, 1, 4, 5] else 0
    subdiv = obj.modifiers.new("Retained sparse cage", "SUBSURF")
    subdiv.levels = subdiv.render_levels = 2
    solid = obj.modifiers.new("Retained 2.5 mm wall", "SOLIDIFY")
    solid.thickness, solid.offset = .0025, -1
    for index, (z, rx, ry, cx) in enumerate([stations[0], stations[-1]]):
        loops = [[(cx+(rx+extra)*math.cos(2*math.pi*j/64), (ry+extra)*math.sin(2*math.pi*j/64), height)
                  for j in range(64)] for extra, height in [(.001, z-.002), (.006, z-.002), (.006, z+.003), (.001, z+.003)]]
        collar = housing_module().rings_mesh("Protected collar "+str(index+1), loops+[loops[0]], mats["metal"], role="protected")
        bm = bmesh.new(); bm.from_mesh(collar.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-8)
        bm.to_mesh(collar.data); bm.free()
        housing_module().bevel(collar, .0005, 2)
    return "Choose sections/cage by silhouette and interface; do not pair profiles with arbitrary cyclic offsets. Shoulder spread is a native shape key. Protect collars and inspect highlight flow after its edit."


def insert_episode():
    mats = prepare()
    panel = disk_surface("Curved panel", .27, .18, .022, mats["coat"])
    crown_source(panel, .27, .18)
    solid = panel.modifiers.new("Retained 2 mm shell", "SOLIDIFY")
    solid.thickness, solid.offset = .002, -1
    # Detailed insert sources are sampled in the same frame and driven by one source control.
    for name, width, depth, z, material in [("Following bezel", .097, .061, .025, mats["polymer"]),
                                           ("Following insert", .085, .049, .026, mats["metal"])]:
        verts = [(width*(col/20-.5), .012+depth*(row/12-.5), z) for row in range(13) for col in range(21)]
        faces = [(row*21+col, row*21+col+1, (row+1)*21+col+1, (row+1)*21+col) for row in range(12) for col in range(20)]
        child = mesh(name, verts, faces, material, "dependent")
        crown_source(child, .27, .18, driver_source=panel)
        wall = child.modifiers.new("Insert backing", "SOLIDIFY")
        wall.thickness = .0012
        child["follows"] = "Curved panel.crown_m"
    for i, (x, y) in enumerate([(-.107, -.063), (.107, -.063), (-.107, .063), (.107, .063)]):
        cylinder("Protected mounting datum "+str(i+1), .0035, .006, (x, y, .022), mats["metal"])["role"] = "protected"
    return "One native crown datum drives panel and surface-following insert. Seats/mounts have a different contract. This example is a fitted proud insert; it does not claim a Boolean recess."


def handle_episode():
    mats = prepare()
    curve = bpy.data.curves.new("Retained handle path", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 24
    curve.bevel_depth = .008
    curve.bevel_resolution = 4
    curve.use_fill_caps = True
    curve.twist_mode = "MINIMUM"
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(3)
    for point, coords in zip(spline.bezier_points, [(-.09, 0, .025), (-.067, -.016, .080), (.055, .010, .088), (.09, 0, .025)]):
        point.co = coords
        point.handle_left_type = point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new("Swept handle", curve)
    bpy.context.scene.collection.objects.link(obj)
    curve.materials.append(mats["polymer"])
    obj["contour_id"] = str(uuid.uuid4())
    for i, x in enumerate([-.09, .09]):
        cube("Protected handle mount "+str(i+1), (.035, .027, .016), (x, 0, .012), mats["metal"])["role"] = "protected"
        cylinder("Handle screw "+str(i+1), .003, .003, (x, -.007, .022), mats["accent"])
    return "Retain the curve and endpoint interfaces. Change middle Bezier points/handles, inspect sweep orientation and new clearance; endpoints remain fixed."


def bracket_episode():
    mats = prepare()
    width, depth = .23, .066
    verts = [(width*(column/40-.5), depth*(row/8-.5), .040) for row in range(9) for column in range(41)]
    faces = [(row*41+col, row*41+col+1, (row+1)*41+col+1, (row+1)*41+col) for row in range(8) for col in range(40)]
    bridge = mesh("Editable bridge", verts, faces, mats["coat"])
    bridge.shape_key_add(name="Basis")
    key = bridge.shape_key_add(name="Bridge arch")
    for point in key.data:
        t = point.co.x/(width*.5)
        point.co.z += .034*max(0, 1-t*t)**3
    key.value = .8
    attribute = bridge.data.attributes.new("fixed_mount_band", "FLOAT", "POINT")
    group = bridge.vertex_groups.new(name="Fixed mount band")
    for vertex in bridge.data.vertices:
        if abs(vertex.co.x) >= .105:
            group.add([vertex.index], 1, "REPLACE")
            key.data[vertex.index].co = vertex.co
        if abs(vertex.co.x) >= width*.5-1e-7:
            attribute.data[vertex.index].value = 1
    solid = bridge.modifiers.new("Retained bridge thickness", "SOLIDIFY")
    solid.thickness, solid.offset = .003, -1
    for i, x in enumerate([-.108, .108]):
        cube("Protected bridge foot "+str(i+1), (.034, .081, .037), (x, 0, .0175), mats["polymer"])["role"] = "protected"
        for j, y in enumerate([-.025, .025]):
            cylinder("Protected bridge bolt "+str(i*2+j+1), .0037, .004, (x, y, .042), mats["metal"])["role"] = "protected"
    return "Bridge arch retains its source; a real undeformed end band protects evaluated wall normals/seat. Check inner rim after Solidify, not only original vertices."


def repair_episode():
    mats = prepare()
    count = 30
    verts = [(column/count*.24-.12, row/count*.14-.07,
              .014*math.cos((column/count-.5)*math.pi)*math.cos((row/count-.5)*math.pi))
             for row in range(count+1) for column in range(count+1)]
    faces = [(row*(count+1)+col, row*(count+1)+col+1,
              (row+1)*(count+1)+col+1, (row+1)*(count+1)+col) for row in range(count) for col in range(count)]
    # Deliberate detached collinear construction error; no hidden procedural modifier source.
    offset = len(verts)
    verts += [(-.020, 0, .017), (0, 0, .017), (.020, 0, .017)]
    faces.append((offset, offset+1, offset+2))
    obj = mesh("Imported repair fixture", verts, faces, mats["coat"])
    group = obj.vertex_groups.new(name="Protected outer band")
    group.add([i for i, vertex in enumerate(obj.data.vertices) if abs(vertex.co.x) >= .11 or abs(vertex.co.y) >= .06], 1, "REPLACE")
    cube("Protected fixture datum", (.03, .14, .007), (-.139, 0, -.004), mats["metal"])["role"] = "protected"
    return "Baked external-style fixture with an intentional defect. Repair must reduce tiny triangles while preserving the stated material, datum and bounds. Separate native shape-key deformation tests protect the source outer band. This is a public regression fixture, not an independent holdout."


def material_episode():
    mats = prepare()
    plaque = cube("UV delivery plaque", (.16, .095, .012), (0, 0, .008), mats["coat"], .004)
    bpy.context.view_layer.objects.active = plaque
    bpy.ops.object.select_all(action="DESELECT")
    plaque.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=.04)
    bpy.ops.object.mode_set(mode="OBJECT")
    cylinder("Polymer material sample", .026, .021, (.020, 0, .026), mats["polymer"])
    cylinder("Metal material sample", .013, .029, (-.039, 0, .030), mats["metal"])
    cube("Accent strip", (.110, .004, .001), (0, -.034, .0147), mats["accent"], .0005)
    return "UV/material delivery sample with physical scale. Validate source shader versus target export, checker anisotropy, image colour space and an independent material edit. A generated pattern is a resource, not a complete PBR shader."


EPISODES = {"housing": None, "transition": loft_episode, "curved-insert": insert_episode,
            "sweep": handle_episode, "assembly": bracket_episode, "imported-repair": repair_episode,
            "materials": material_episode}


def build(name, output):
    output = Path(output).resolve()
    if output.exists() or output.suffix.lower() != ".blend":
        raise ValueError("Episode output must be a new .blend")
    if name not in EPISODES:
        raise ValueError("Unknown episode")
    if name == "housing":
        if bpy.data.filepath:
            raise ValueError("Housing requires a fresh scene")
        housing_module().build(.012)
        note = "Fixed-rim crown with live GN, Boolean vents, preserved seats and independent material/detail edits."
    else:
        note = EPISODES[name]()
    for obj in bpy.context.scene.objects:
        if "contour_id" not in obj:
            obj["contour_id"] = str(uuid.uuid4())
    bpy.context.scene["contour_episode"] = name
    text = bpy.data.texts.new("CONTOUR_AUTHORING_INTENT.md")
    text.write(note+"\nOriginal development episode; independent expert review and comparative uplift are not established.\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    return {"status": "PASS", "episode": name, "output": str(output), "intent": note,
            "independent_expert_review": "NOT_CHECKED"}
