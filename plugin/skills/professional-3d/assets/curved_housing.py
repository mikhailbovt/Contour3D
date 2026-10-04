"""Original development example: an asymmetric housing with a live crown control.

Use Blender's normal background/Python route. Build in a fresh scene; edit a
saved example into a new file. No plugin, add-on or transport is needed to reopen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Vector

RIM_Z = 0.079
HALF_WIDTH, HALF_DEPTH, CORNER = 0.15, 0.095, 0.021
CENTER_X = 0.010
CROWN_SEAT = 0.12
MUTABLE = {"Crown lid", "Display bezel", "Display glass", "Display bars"}


def rounded_loop(width, depth, radius, steps=8):
    points = []
    for index, (x, y) in enumerate([(width/2-radius, depth/2-radius),
                                   (-width/2+radius, depth/2-radius),
                                   (-width/2+radius, -depth/2+radius),
                                   (width/2-radius, -depth/2+radius)]):
        for step in range(steps + 1):
            angle = (index + step/steps) * math.pi/2
            points.append((x + radius*math.cos(angle), y + radius*math.sin(angle)))
    return points


def shell_loop(width, depth, steps=64):
    """A smooth fourth-order superellipse, shared by the body, frame and lid."""
    points=[]
    for index in range(steps):
        angle=2*math.pi*index/steps
        c,s=math.cos(angle),math.sin(angle)
        radius=(c**4+s**4)**(-.25)
        points.append((width*.5*radius*c,depth*.5*radius*s))
    return points


def material(name, color, metallic=0.0, roughness=0.4, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1)
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    node.inputs["Emission Color"].default_value = (*color, 1)
    node.inputs["Emission Strength"].default_value = emission
    return mat


def mesh_object(name, vertices, faces, mat, role="body"):
    mesh = bpy.data.meshes.new(name + " source")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(mat)
    obj["role"] = role
    for face in mesh.polygons:
        face.use_smooth = True
    return obj


def bevel(obj, width, segments=3):
    modifier = obj.modifiers.new("Edge radius", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.harden_normals = True
    normals = obj.modifiers.new("Manufactured normals", "WEIGHTED_NORMAL")
    normals.keep_sharp = True


def rings_mesh(name, loops, mat, cap_bottom=False, cap_top=False, role="body"):
    count = len(loops[0])
    vertices = [vertex for loop in loops for vertex in loop]
    faces = [(ring*count+j, ring*count+(j+1)%count,
              (ring+1)*count+(j+1)%count, (ring+1)*count+j)
             for ring in range(len(loops)-1) for j in range(count)]
    if cap_bottom:
        faces.append(tuple(reversed(range(count))))
    if cap_top:
        faces.append(tuple((len(loops)-1)*count+j for j in range(count)))
    return mesh_object(name, vertices, faces, mat, role)


def crown_group():
    group = bpy.data.node_groups.new("Contour crown — metres", "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    control = group.interface.new_socket(name="Crown (m)", in_out="INPUT", socket_type="NodeSocketFloat")
    control.default_value = .012
    control.min_value, control.max_value = 0.0, 0.030
    control.description = "Smooth crown with fixed superellipse rim position and first boundary derivative"
    inputs = group.nodes.new("NodeGroupInput")
    outputs = group.nodes.new("NodeGroupOutput")
    # Evaluate a smooth implicit field on subdivided positions. A radial distance
    # to a rounded rectangle has diagonal derivative discontinuities; avoid it.
    coordinates=group.nodes.new("GeometryNodeInputPosition")
    separate=group.nodes.new("ShaderNodeSeparateXYZ")
    group.links.new(coordinates.outputs["Position"],separate.inputs["Vector"])
    def math_node(operation,a=None,b=None):
        node=group.nodes.new("ShaderNodeMath");node.operation=operation
        for index,value in enumerate([a,b]):
            if value is None:continue
            if isinstance(value,(float,int)):node.inputs[index].default_value=value
            else:group.links.new(value,node.inputs[index])
        return node.outputs[0]
    x=math_node("DIVIDE",math_node("SUBTRACT",separate.outputs["X"],CENTER_X),HALF_WIDTH)
    y=math_node("DIVIDE",separate.outputs["Y"],HALF_DEPTH)
    inside=math_node("SUBTRACT",1.0,math_node("ADD",math_node("POWER",x,4.0),math_node("POWER",y,4.0)))
    # Preserve a real seating band. A zero derivative on the ideal boundary
    # alone does not freeze Solidify's discrete boundary normals and inner rim.
    seated=math_node("DIVIDE",math_node("SUBTRACT",inside,CROWN_SEAT),1-CROWN_SEAT)
    weights=math_node("POWER",math_node("MAXIMUM",seated,0.0),2.0)
    multiply = group.nodes.new("ShaderNodeMath")
    multiply.operation = "MULTIPLY"
    vector = group.nodes.new("ShaderNodeCombineXYZ")
    position = group.nodes.new("GeometryNodeSetPosition")
    group.links.new(inputs.outputs["Geometry"], position.inputs["Geometry"])
    group.links.new(weights, multiply.inputs[0])
    group.links.new(inputs.outputs["Crown (m)"], multiply.inputs[1])
    group.links.new(multiply.outputs[0], vector.inputs["Z"])
    group.links.new(vector.outputs["Vector"], position.inputs["Offset"])
    group.links.new(position.outputs["Geometry"], outputs.inputs["Geometry"])
    for node, location in [(inputs,(-600,150)),(coordinates,(-1100,-180)),(separate,(-900,-180)),(multiply,(-350,-80)),
                           (vector,(-150,-80)),(position,(80,150)),(outputs,(300,150))]:
        node.location = location
    return group, control.identifier


def add_crown(obj, group, identifier, crown):
    subdivide=obj.modifiers.new("Retained surface sampling","SUBSURF")
    subdivide.subdivision_type="SIMPLE";subdivide.levels=2;subdivide.render_levels=2
    modifier = obj.modifiers.new("Editable crown", "NODES")
    modifier.node_group = group
    modifier[identifier] = crown
    obj["crown_socket"] = identifier


def weight_at(x, y):
    """Smooth analytic superellipse field; independent sample evaluation."""
    inside=1-((x-CENTER_X)/HALF_WIDTH)**4-(y/HALF_DEPTH)**4
    return max(0.0,(inside-CROWN_SEAT)/(1-CROWN_SEAT))**2


def build(crown):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    scene["contour_example"] = "curved-housing-v1"
    scene["crown_metres"] = crown
    scene["protected_intent"] = "Body, perimeter frame, feet, ports and all four mounting fasteners. Crown lid and display surface parts may change."
    blue = material("Ceramic blue coating", (.025,.085,.11), .10, .38)
    dark = material("Graphite polymer", (.017,.022,.024), 0, .42)
    steel = material("Satin fastening steel", (.32,.36,.37), .85, .27)
    glass = material("Dark display glass", (.012,.037,.035), .18, .19)
    lit = material("Display phosphor", (.1,.68,.38), 0, .3, .8)
    loops = []
    for width, depth, z, shift in [(.276,.173,.010,-.003),(.280,.177,.014,-.002),
                                 (.295,.186,.060,.008),(.300,.190,.075,CENTER_X)]:
        loops.append([(x+shift,y,z) for x,y in shell_loop(width,depth)])
    body = rings_mesh("Tapered housing", loops, blue, cap_bottom=True)
    solid = body.modifiers.new("Retained 3 mm wall", "SOLIDIFY")
    solid.thickness = .003
    solid.offset = -1
    # One native Boolean source cuts real ventilation openings through the wall.
    cutter_vertices, cutter_faces = [], []
    profile = rounded_loop(.008, .026, .0025, steps=5)
    for index in range(9):
        offset = len(cutter_vertices)
        center = -.060 + index*.015
        count = len(profile)
        cutter_vertices.extend((center+x,y,.039+z) for y in [-.110,-.074] for x,z in profile)
        cutter_faces.extend([(offset+j,offset+(j+1)%count,offset+count+(j+1)%count,offset+count+j) for j in range(count)])
        cutter_faces.extend([tuple(offset+j for j in reversed(range(count))),
                             tuple(offset+count+j for j in range(count))])
    cutter = mesh_object("Vent aperture source", cutter_vertices, cutter_faces, dark, "construction")
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    boolean = body.modifiers.new("Retained vent openings", "BOOLEAN")
    boolean.operation, boolean.solver, boolean.object = "DIFFERENCE", "EXACT", cutter
    bevel(body, .0012)
    # Sparse crown source: 12 radial bands, native quads with a central fan.
    outline = shell_loop(.300, .190)
    vertices, weights = [(CENTER_X,0,RIM_Z)], [1.0]
    count, bands = len(outline), 12
    for ring in range(1,bands+1):
        t = ring/bands
        weight = (1-t**4)**2
        for x,y in outline:
            vertices.append((CENTER_X+t*x,t*y,RIM_Z+.0015*weight*t*x/HALF_WIDTH))
            weights.append(weight)
    faces = [(0,1+j,1+(j+1)%count) for j in range(count)]
    for ring in range(bands-1):
        a, b = 1+ring*count, 1+(ring+1)*count
        faces.extend((a+j,b+j,b+(j+1)%count,a+(j+1)%count) for j in range(count))
    lid = mesh_object("Crown lid", vertices, faces, blue, "editable")
    group, identifier = crown_group()
    # Persist the actual boundary selection instead of inferring it from a broad
    # spatial band that also includes intentionally deforming interior vertices.
    rim_attribute=lid.data.attributes.new("contour_protected_rim","FLOAT","POINT")
    for datum in list(rim_attribute.data)[1+(bands-1)*count:]:datum.value=1.0
    add_crown(lid, group, identifier, crown)
    solid = lid.modifiers.new("Retained lid thickness", "SOLIDIFY")
    solid.thickness, solid.offset = .0024, -1
    # A real closed frame cross-section seats on the fixed lid boundary.
    frame_loops = []
    for width, depth, z in [(.297,.187,.076),(.311,.201,.076),(.311,.201,.082),(.297,.187,.082),(.297,.187,.076)]:
        frame_loops.append([(CENTER_X+x,y,z) for x,y in shell_loop(width,depth)])
    # Join the last section back to the first without duplicate vertices.
    frame = rings_mesh("Protected perimeter frame", frame_loops[:-1]+[frame_loops[0]], dark, role="protected")
    # Weld coincident closure vertices for a proper closed section.
    bm = bmesh.new(); bm.from_mesh(frame.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bm.to_mesh(frame.data); bm.free()
    bevel(frame,.0008,2)
    for index,(x,y) in enumerate([(-.125,-.077),(.125,-.077),(-.125,.077),(.125,.077)],1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0037,depth=.002,location=(CENTER_X+x,y,.083))
        obj=bpy.context.object; obj.name=f"Protected fastener {index}"; obj["role"]="protected"
        obj.data.materials.append(steel); bevel(obj,.0003,2)
    # Display module follows the same preserved surface field; it is allowed to move.
    for name,width,depth,z,mat in [("Display bezel",.116,.059,.0835,dark),
                                  ("Display glass",.105,.048,.085,glass)]:
        verts, ws = [], []
        nx,ny=18,10
        for row in range(ny+1):
            for column in range(nx+1):
                x=CENTER_X-width/2+width*column/nx
                y=.012-depth/2+depth*row/ny
                w=weight_at(x,y)
                verts.append((x,y,z+.0015*w*(x-CENTER_X)/HALF_WIDTH)); ws.append(w)
        fs=[(row*(nx+1)+col,row*(nx+1)+col+1,(row+1)*(nx+1)+col+1,(row+1)*(nx+1)+col)
            for row in range(ny) for col in range(nx)]
        obj=mesh_object(name,verts,fs,mat,"editable")
        add_crown(obj,group,identifier,crown)
        solid=obj.modifiers.new("Display source thickness","SOLIDIFY"); solid.thickness=.0012; solid.offset=-1
    bars,bar_faces,bar_weights=[],[],[]
    for index in range(6):
        x=CENTER_X-.037+index*.012
        y=.005; height=.006+.003*(index%3)
        offset=len(bars)
        for a,b in [(x,y),(x+.005,y),(x+.005,y+height),(x,y+height)]:
            w=weight_at(a,b); bars.append((a,b,.0855+.0015*w*(a-CENTER_X)/HALF_WIDTH));bar_weights.append(w)
        bar_faces.append(tuple(offset+j for j in range(4)))
    obj=mesh_object("Display bars",bars,bar_faces,lit,"editable")
    add_crown(obj,group,identifier,crown)
    for index,(x,y) in enumerate([(-.095,-.056),(.095,-.056),(-.095,.056),(.095,.056)],1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.013,depth=.010,location=(x,y,.006))
        obj=bpy.context.object;obj.name=f"Protected foot {index}";obj["role"]="protected";obj.data.materials.append(dark);bevel(obj,.001,3)
    for name,radius,depth,x,mat in [("Protected connector collar",.009,.010,.159,steel),
                                   ("Protected connector socket",.0065,.011,.162,dark)]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=radius,depth=depth,location=(x,.03,.041),rotation=(0,math.pi/2,0))
        obj=bpy.context.object;obj.name=name;obj["role"]="protected";obj.data.materials.append(mat);bevel(obj,.0005,2)
    setup_views()
    text=bpy.data.texts.new("AUTHORING_INTENT.md")
    text.write("Original Contour3D example. Units: metres. Change Crown (m) in the retained Geometry Nodes modifiers on lid and display parts together. Perimeter frame, body, fasteners, feet, ports and vent source are protected. Plugin resources are not required to reopen/edit. Render and sampled checks do not certify CAD or global clearance.\n")
    bpy.context.view_layer.update()


def setup_views():
    scene=bpy.context.scene
    bpy.ops.object.camera_add(location=(.38,-.43,.33))
    camera=bpy.context.object;camera.name="Inspection camera"
    camera.rotation_euler=(Vector((CENTER_X,0,.05))-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.type="ORTHO";camera.data.ortho_scale=.46;scene.camera=camera
    for name,location,energy,size in [("Key",(.0,-.35,.55),10,.42),("Fill",(-.35,.1,.3),5,.35),("Rim",(.3,.35,.4),6,.3)]:
        bpy.ops.object.light_add(type="AREA",location=location)
        light=bpy.context.object;light.name=name;light.data.energy=energy;light.data.shape="DISK";light.data.size=size
        light.rotation_euler=(Vector((0,0,.04))-light.location).to_track_quat("-Z","Y").to_euler()
    scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.035,.045,.055,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.4
    scene.render.engine="CYCLES";scene.cycles.samples=24
    scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG";scene.view_settings.view_transform="AgX"


def fingerprint(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    try:
        values={"matrix":[list(row) for row in obj.matrix_world],
                "vertices":[list(vertex.co) for vertex in mesh.vertices],
                "faces":[list(face.vertices) for face in mesh.polygons],
                "source_vertices":[list(vertex.co) for vertex in obj.data.vertices],
                "materials":[mat.name if mat else None for mat in obj.data.materials]}
        return hashlib.sha256(json.dumps(values,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    finally:
        evaluated.to_mesh_clear()


def protected_snapshot():
    return {obj.name:fingerprint(obj) for obj in bpy.context.scene.objects
            if obj.type=="MESH" and obj.name not in MUTABLE}


def rim_samples():
    obj=bpy.data.objects["Crown lid"].evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=obj.to_mesh()
    try:
        selection=mesh.attributes.get("contour_protected_rim")
        if selection is None:raise RuntimeError("Source has no protected-rim correspondence")
        return {vertex.index:tuple(vertex.co) for vertex in mesh.vertices
                if selection.data[vertex.index].value>=1-1e-6}
    finally:
        obj.to_mesh_clear()


def center_height():
    obj=bpy.data.objects["Crown lid"].evaluated_get(bpy.context.evaluated_depsgraph_get())
    found,position,normal,index=obj.ray_cast(Vector((CENTER_X,0,1)),Vector((0,0,-1)))
    if not found:
        raise RuntimeError("Center height ray missed the lid")
    return position.z


def edit(crown):
    scene=bpy.context.scene
    if scene.get("contour_example")!="curved-housing-v1":
        raise RuntimeError("This is not the authored development enclosure")
    before=protected_snapshot();old_height=center_height();old_crown=float(scene["crown_metres"])
    old_rim=rim_samples()
    for name in MUTABLE:
        obj=bpy.data.objects[name]
        modifier=obj.modifiers["Editable crown"]
        modifier[obj["crown_socket"]]=crown
        obj.update_tag()
    scene["crown_metres"]=crown;bpy.context.view_layer.update()
    after=protected_snapshot();new_height=center_height()
    new_rim=rim_samples()
    if old_rim.keys()!=new_rim.keys():raise RuntimeError("Rim correspondence changed")
    rim_shift=max((Vector(old_rim[index])-Vector(new_rim[index])).length for index in old_rim)
    changed=[name for name in set(before)|set(after) if before.get(name)!=after.get(name)]
    error=abs((new_height-old_height)-(crown-old_crown))
    if changed or error>1e-6 or rim_shift>5e-6:
        raise RuntimeError(f"Protected change or incorrect crown/rim: {changed}, error={error}, rim={rim_shift}")
    return {"protected_objects":len(before),"changed_protected_objects":changed,
            "protected_geometry_status":"PASS","center_height_before_m":old_height,
            "center_height_after_m":new_height,"requested_crown_delta_m":crown-old_crown,
            "measured_height_delta_m":new_height-old_height,"height_error_m":error,
            "rim_sample_count":len(old_rim),"maximum_sampled_rim_shift_m":rim_shift,
            "sampled_rim_status":"PASS","rim_tolerance_m":5e-6,
            "center_height_status":"PASS",
            "coverage":"Exact source vertex/evaluated position and topology hashes, object transforms and material slot identity for all noneditable mesh objects; one center ray and source-labelled evaluated rim vertices with unchanged correspondence. Does not cover material node contents, global collisions, artistic quality or every boundary derivative."}


def render(path, mode):
    scene=bpy.context.scene
    if mode=="clay":
        clay=material("Diagnostic neutral clay",(.32,.35,.38),0,.5)
        # Explicit slot overrides work in the chosen engine, including Cycles.
        for obj in scene.objects:
            if obj.type=="MESH" and not obj.hide_render:
                obj.data.materials.clear();obj.data.materials.append(clay)
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["build","edit"])
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--crown-mm",type=float,default=12)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--preview",type=Path)
    parser.add_argument("--view",choices=["material","clay"],default="material")
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    args=parser.parse_args(argv)
    paths=[args.output,args.report]+([args.preview] if args.preview else [])
    if len({path.resolve() for path in paths})!=len(paths):
        parser.error("Each output needs a distinct path")
    if args.output.suffix.lower()!=".blend" or args.report.suffix.lower()!=".json":
        parser.error("Output must be .blend; report must be .json")
    if args.preview and args.preview.suffix.lower()!=".png":
        parser.error("Preview must be .png")
    if not math.isfinite(args.crown_mm) or not 0<=args.crown_mm<=30:
        parser.error("Crown must be finite and between 0 and 30 mm")
    for path in paths:
        if path.exists():parser.error(f"Output exists: {path}")
        if bpy.data.filepath and path.resolve()==Path(bpy.data.filepath).resolve():parser.error("Cannot overwrite the source")
        path.parent.mkdir(parents=True,exist_ok=True)
    if args.mode=="build":
        if bpy.data.filepath:parser.error("Build requires a fresh Blender scene")
        build(args.crown_mm/1000)
        report={"status":"CREATED","center_height_m":center_height(),"quality_status":"NOT_CHECKED"}
    else:
        report=edit(args.crown_mm/1000)
    report.update({"schema_version":1,"blender_version":bpy.app.version_string,
                   "example":"curved-housing-v1","crown_mm":args.crown_mm,
                   "independent_expert_review":"NOT_CHECKED","comparison_against_C1":"NOT_CHECKED"})
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    with args.report.open("x",encoding="utf-8") as handle:json.dump(report,handle,indent=2);handle.write("\n")
    print("CONTOUR_EXAMPLE "+json.dumps(report),flush=True)
    if args.preview:render(args.preview.resolve(),args.view)


if __name__=="__main__":
    main()
