"""Imagegen provenance. No provider client, model selection or key handling."""
from __future__ import annotations

from pathlib import Path
import shutil
from .common import file_hash, read_json, write_new


def record_output(packet_path, image_path, prompt, purpose, features=None, input_renders=None):
    packet_path = Path(packet_path).resolve()
    packet = read_json(packet_path)
    if packet.get("kind") != "CONTOUR_VISUAL_PACKET" or packet.get("schema_version") != 2:
        raise ValueError("Expected a real Contour visual packet")
    image_path = Path(image_path).resolve()
    extension = image_path.suffix.lower()
    if extension not in {".png", ".jpg", ".jpeg", ".webp"} or not image_path.is_file():
        raise ValueError("Imagegen output must be a saved PNG, JPEG or WebP")
    with image_path.open("rb") as handle:
        header = handle.read(16)
    if not (header.startswith(b'\x89PNG\r\n\x1a\n') or header.startswith(b'\xff\xd8\xff') or
            header.startswith(b'RIFF') and header[8:12] == b'WEBP'):
        raise ValueError("Selected output does not have a supported raster header")
    digest = file_hash(image_path)
    stem = "generated-"+digest[:16]
    target = packet_path.parent/(stem+extension)
    record_path = packet_path.parent/(stem+".json")
    if target.exists() or record_path.exists():
        raise ValueError("This output already has a resource record")
    available = {render["path"]:render for render in packet["renders"]}
    if not input_renders or not isinstance(input_renders,list) or set(input_renders)-set(available):
        raise ValueError("Name the exact packet renders actually supplied to the built-in tool")
    inputs = [{"path": render["path"], "sha256": render["sha256"], "kind": render["kind"],
               "view": render["view"], "mode": render["mode"]} for render in packet["renders"]]
    inputs = [item for item in inputs if item["path"] in input_renders]
    for item in inputs:
        if file_hash(packet_path.parent/item["path"]) != item["sha256"]:
            raise ValueError("Input render changed after packet creation")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Store the actual generation prompt")
    with image_path.open("rb") as source, target.open("xb") as destination:
        shutil.copyfileobj(source, destination)
    record = {"schema_version": 2, "kind": "GENERATED_IMAGE_RESOURCE", "status": "GENERATED_DRAFT",
              "tool": "Built-in Codex imagegen", "purpose": purpose, "prompt": prompt,
              "source_revision": packet["revision"], "source_sha256": packet["source_sha256"],
              "frame": packet["frame"], "metres_per_blender_unit":packet["inspection"]["metres_per_blender_unit"],
              "inputs": inputs, "output": target.name, "output_sha256": digest,
              "proposed_features": features or [], "camera_consistency": "NOT_CHECKED",
              "native_transfer": "NOT_CHECKED", "artistic_quality": "NOT_CHECKED",
              "warning": "Generated design/texture resource, never evidence that native geometry was completed."}
    write_new(record_path, record)
    return {"status": "PASS", "resource": str(target), "record": str(record_path)}


def record_transfer(resource_path, native_result, edit_report_path, output_path, observations):
    resource_path = Path(resource_path).resolve()
    record = read_json(resource_path)
    native_result = Path(native_result).resolve()
    evidence = read_json(edit_report_path)
    if record.get("kind") != "GENERATED_IMAGE_RESOURCE" or not native_result.is_file() or native_result.suffix.lower() != ".blend":
        raise ValueError("Expected a recorded generated resource and saved native result")
    if file_hash(resource_path.parent/record["output"]) != record["output_sha256"]:
        raise ValueError("Generated resource has changed")
    if evidence.get("status") != "PASS" or evidence.get("acceptance", {}).get("status") != "PASS":
        raise ValueError("Native transfer needs a passing scoped edit report")
    if evidence.get("source", {}).get("source_sha256") != record["source_sha256"]:
        raise ValueError("Native transfer started from another source revision")
    if any(evidence.get("source",{}).get(key) != record.get(key) for key in ["frame","metres_per_blender_unit"]):
        raise ValueError("Native transfer started from another frame or physical unit scale")
    if not isinstance(observations,str) or not observations.strip():
        raise ValueError("Describe the actual native feature transfer and checks")
    if Path(evidence.get("output", "")).resolve() != native_result:
        raise ValueError("Edit evidence belongs to another native output")
    successor = {**record, "status": "TRANSFERRED_TO_NATIVE", "native_result": str(native_result),
                 "native_sha256": file_hash(native_result), "native_transfer": "PASS",
                 "edit_report": str(Path(edit_report_path).resolve()), "edit_report_sha256": file_hash(edit_report_path),
                 "observations": observations, "artistic_quality": "NOT_CHECKED"}
    write_new(output_path, successor)
    return {"status": "PASS", "record": str(Path(output_path).resolve()), "scope": "Recorded native transfer and scoped edit evidence, not an artistic-quality certificate."}
