"""Small shared serialization utilities; importing this module does not edit Blender."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_new(path, value):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    return path


def read_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON: " + x)))


def finite_number(value, label="value", minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + " must be a finite number")
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError(label + " is outside the allowed interval")
    return float(value)


def vector(value, label="vector", size=3):
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(label + " must contain " + str(size) + " components")
    return [finite_number(item, label) for item in value]


def object_key(obj):
    """Never silently tag a user's scene during inspection."""
    stable = obj.get("contour_id")
    library = obj.library.filepath if obj.library else ""
    return str(stable) if stable else "name:" + library + ":" + obj.name_full


def units(scene):
    return finite_number(scene.unit_settings.scale_length, "metres per Blender unit", 1e-12)


def resolve_objects(names=None):
    import bpy
    scene = bpy.context.scene
    if names is None:
        return sorted(scene.objects, key=lambda item: item.name_full)
    missing = sorted(set(names) - set(scene.objects.keys()))
    if missing:
        raise ValueError("Scene objects missing: " + ", ".join(missing))
    return [scene.objects[name] for name in sorted(set(names))]


def source_identity():
    import bpy
    path = Path(bpy.data.filepath) if bpy.data.filepath else None
    return {"source_file": path.name if path else None,
            "source_sha256": file_hash(path) if path and path.is_file() else None,
            "blender_version": bpy.app.version_string,
            "frame": bpy.context.scene.frame_current,
            "metres_per_blender_unit": units(bpy.context.scene)}
