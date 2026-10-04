"""Scoped static GLB delivery with independent native reimport measurements."""
from pathlib import Path
import tempfile
import bpy
import numpy as np
from mathutils import Matrix

from .common import file_hash, finite_number, resolve_objects, source_identity, units, write_new
from .geometry import arrays, bounds, evaluated_mesh, GEOMETRY_TYPES, inspect_scene


def delivery(output, report_path, names=None, triangle_budget=None, tolerance_m=1e-5):
    output, report_path = Path(output).resolve(), Path(report_path).resolve()
    if output.suffix.lower() != '.glb' or output.exists() or report_path.exists() or output == report_path:
        raise ValueError('Delivery needs new .glb and JSON report paths')
    tolerance_m = finite_number(tolerance_m, 'roundtrip bounds tolerance', 0)
    if triangle_budget is not None and (isinstance(triangle_budget, bool) or not isinstance(triangle_budget,int) or triangle_budget < 1):
        raise ValueError('Triangle budget must be a positive integer')
    source = source_identity()
    objects = resolve_objects(names)
    objects = [obj for obj in objects if obj.type in GEOMETRY_TYPES]
    if not objects or bpy.context.mode != 'OBJECT':
        raise ValueError('Static delivery requires selected geometry in Object mode')
    if any(obj.library or any(mod.type in {'ARMATURE','CLOTH','SOFT_BODY','FLUID'} for mod in obj.modifiers) for obj in objects):
        raise ValueError('This static profile does not certify rigged, simulated or linked assets; use a target-specific exporter')
    inspection = inspect_scene([obj.name for obj in objects], include_instances=True)
    if inspection['instances']:
        raise ValueError('Realize/check instance export through an explicit target-specific method')
    expected = inspection['evaluated_object_triangles']
    if triangle_budget is not None and expected > triangle_budget:
        raise ValueError('Evaluated triangle count exceeds the declared delivery budget')
    positions=[]
    for obj in objects:
        with evaluated_mesh(obj) as (mesh,matrix): positions.append(arrays(mesh,matrix,units(bpy.context.scene))[0])
    before_bounds=bounds(np.concatenate(positions))
    if before_bounds is None: raise ValueError('No evaluated vertices to deliver')
    scene=bpy.context.scene
    selection=list(bpy.context.selected_objects); active=bpy.context.view_layer.objects.active
    old_ids={kind:{item.as_pointer() for item in getattr(bpy.data,kind)} for kind in ['objects','meshes','materials','images','node_groups','collections']}
    imported_scene=None;export_scene=None
    report={'schema_version':2,'source':source,'profile':'static-glb','objects':[obj.name for obj in objects],
            'evaluated_triangles':expected,'triangle_budget':triangle_budget,'bounds_tolerance_m':tolerance_m,
            'artistic_quality':'NOT_CHECKED','target_engine_runtime':'NOT_CHECKED','shader_fidelity':'NOT_CHECKED',
            'scope':'Current-frame static GLB, metre scale, applied modifiers, no animations. Reimport validates triangle count and world bounds; does not certify shader equivalence, UV padding, collision, LOD or target engine readiness.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='contour-delivery-') as folder:
            temporary=Path(folder)/'asset.glb'
            # Export a metre-scaled evaluated scene; Blender's glTF exporter treats
            # NONE unit systems differently, so never rely on that implicit policy.
            from .packet import evaluated_copies
            copies=evaluated_copies([obj.name for obj in objects])
            export_scene=bpy.data.scenes.new('Contour temporary export')
            export_scene.unit_settings.system='METRIC';export_scene.unit_settings.scale_length=1
            bpy.context.window.scene=export_scene
            exported=[]
            for item in copies:
                obj=bpy.data.objects.new('Static '+item['source'].name,item['mesh'])
                export_scene.collection.objects.link(obj)
                transform=Matrix.Scale(units(scene),4) @ item['source'].matrix_world
                if abs(transform.determinant())<1e-15: raise ValueError('Static export needs invertible transforms')
                item['mesh'].transform(transform.inverted())
                obj.matrix_world=transform;obj.select_set(True);exported.append(obj)
            if not exported:raise ValueError('No visible evaluated geometry for export')
            bpy.context.view_layer.objects.active=exported[0]
            bpy.context.view_layer.update()
            report['exported_names']={item['source'].name:obj.name for item,obj in zip(copies,exported)}
            status=bpy.ops.export_scene.gltf(filepath=str(temporary),export_format='GLB',use_selection=True,
                export_apply=True,export_yup=True,export_animations=False,export_extras=False,
                export_materials='EXPORT',export_texcoords=True,export_normals=True)
            if 'FINISHED' not in status or not temporary.is_file(): raise ValueError('GLB export did not finish')
            imported_scene=bpy.data.scenes.new('Contour temporary roundtrip')
            imported_scene.unit_settings.system='METRIC';imported_scene.unit_settings.scale_length=1
            bpy.context.window.scene=imported_scene
            result=bpy.ops.import_scene.gltf(filepath=str(temporary))
            if 'FINISHED' not in result: raise ValueError('GLB reimport did not finish')
            bpy.context.view_layer.update()
            imported=[]; triangles=0
            for obj in imported_scene.objects:
                if obj.type in GEOMETRY_TYPES:
                    with evaluated_mesh(obj) as (mesh,matrix):
                        points,faces=arrays(mesh,matrix,units(imported_scene)); imported.append(points);triangles+=len(faces)
            if not imported: raise ValueError('Reimport produced no geometry')
            after_bounds=bounds(np.concatenate(imported))
            shift=max(abs(before_bounds[key][axis]-after_bounds[key][axis]) for key in ['minimum_m','maximum_m'] for axis in range(3))
            passed=triangles==expected and shift<=tolerance_m
            report['roundtrip']={'status':'PASS' if passed else 'FAIL','triangles':triangles,
                                 'maximum_bound_shift_m':shift,'before_bounds':before_bounds,'after_bounds':after_bounds}
            if not passed: raise ValueError('Static export roundtrip changed triangle count or bounds beyond tolerance')
            with output.open('xb') as handle: handle.write(temporary.read_bytes())
            report.update(status='PASS',output=str(output),sha256=file_hash(output))
    except Exception as error:
        report.update(status='FAIL',reason=str(error),output=None)
    finally:
        bpy.context.window.scene=scene
        if imported_scene: bpy.data.scenes.remove(imported_scene)
        if export_scene: bpy.data.scenes.remove(export_scene)
        for kind in old_ids:
            collection=getattr(bpy.data,kind)
            for item in list(collection):
                if item.as_pointer() not in old_ids[kind]: collection.remove(item,do_unlink=True)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection: obj.select_set(True)
        bpy.context.view_layer.objects.active=active
        bpy.context.view_layer.update()
    write_new(report_path,report)
    return report
