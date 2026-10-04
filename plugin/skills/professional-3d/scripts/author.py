"""Contour3D authoring CLI. Blender commands run through your existing Blender."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Blender --python execution does not consistently add the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from contour.common import read_json, write_new


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Read-only instance-aware geometry, sections, UV and sampled thickness")
    inspect.add_argument("--output", type=Path, required=True)
    inspect.add_argument("--objects", nargs="+")
    inspect.add_argument("--thickness", action="store_true")
    inspect.add_argument("--sections", type=Path, help="JSON array of normal/offset_m section planes")
    inspect.add_argument("--no-instances", action="store_true")
    snap = sub.add_parser("snapshot", help="Read-only geometry/material/dependency fingerprints")
    snap.add_argument("--output", type=Path, required=True)
    snap.add_argument("--objects", nargs="+")
    contract = sub.add_parser("capture", help="Capture exact declared protected properties/regions")
    contract.add_argument("--plan", type=Path, required=True)
    contract.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("check", help="Verify a captured contract against the loaded scene")
    check.add_argument("--baseline", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    edit = sub.add_parser("edit", help="Apply a bounded data-only plan, validate invariants and save a new native file")
    edit.add_argument("--plan", type=Path, required=True)
    edit.add_argument("--output", type=Path, required=True)
    edit.add_argument("--report", type=Path, required=True)
    packet = sub.add_parser("packet", help="Real diagnostic renders and a 3D workbench preview")
    packet.add_argument("--output-dir", type=Path, required=True)
    packet.add_argument("--objects", nargs="+")
    packet.add_argument("--views", nargs="+", default=["iso", "front", "side"])
    packet.add_argument("--modes", nargs="+", default=["clay", "reflection"])
    packet.add_argument("--resolution", type=int, default=768)
    packet.add_argument("--purpose", default="form")
    packet.add_argument("--question", default="")
    packet.add_argument("--no-render", action="store_true")
    packet.add_argument("--framing", type=Path, help="Earlier packet.json for exactly matched before/after cameras")
    packet.add_argument("--preview-triangles", type=int, default=100000)
    episode = sub.add_parser("episode", help="Original editable construction episodes in a fresh scene")
    episode.add_argument("--name", choices=["housing", "transition", "curved-insert", "sweep", "assembly", "imported-repair", "materials"], required=True)
    episode.add_argument("--output", type=Path, required=True)
    deliver = sub.add_parser("deliver", help="Static GLB with triangle budget and independent Blender reimport")
    deliver.add_argument("--objects", nargs="+")
    deliver.add_argument("--output", type=Path, required=True)
    deliver.add_argument("--report", type=Path, required=True)
    deliver.add_argument("--triangle-budget", type=int)
    deliver.add_argument("--tolerance-m", type=float, default=1e-5)
    image = sub.add_parser("image-record", help="Record an actual built-in imagegen output; runs with normal Python")
    image.add_argument("--packet", type=Path, required=True)
    image.add_argument("--image", type=Path, required=True)
    image.add_argument("--prompt-file", type=Path, required=True)
    image.add_argument("--purpose", required=True)
    image.add_argument("--features", nargs="*", default=[])
    image.add_argument("--input-renders", nargs="+", required=True, help="Exact packet image filenames supplied to the tool")
    transfer = sub.add_parser("image-transfer", help="Record scoped successful native transfer from the same source")
    transfer.add_argument("--resource-record", type=Path, required=True)
    transfer.add_argument("--native", type=Path, required=True)
    transfer.add_argument("--edit-report", type=Path, required=True)
    transfer.add_argument("--output", type=Path, required=True)
    transfer.add_argument("--observations", required=True)
    return root


def main():
    argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:]
    args = parser().parse_args(argv)
    if args.command == "image-record":
        from contour.visual import record_output
        result = record_output(args.packet, args.image, args.prompt_file.read_text(encoding="utf-8"), args.purpose, args.features, args.input_renders)
    elif args.command == "image-transfer":
        from contour.visual import record_transfer
        result = record_transfer(args.resource_record, args.native, args.edit_report, args.output, args.observations)
    else:
        try:
            import bpy
        except ImportError as error:
            raise RuntimeError("Run this command inside the existing Blender: blender --background scene.blend --disable-autoexec --python author.py -- <command>") from error
        if args.command == "inspect":
            from contour.geometry import inspect_scene
            result = inspect_scene(args.objects, not args.no_instances, args.thickness,
                                   read_json(args.sections) if args.sections else None)
            write_new(args.output, result)
            result = {"status": "PASS", "output": str(args.output.resolve()), "objects": len(result["objects"]),
                      "instances": len(result["instances"]), "evaluated_triangles": result["evaluated_object_triangles"]}
        elif args.command == "snapshot":
            from contour.intent import snapshot
            result = snapshot(args.objects)
            write_new(args.output, result)
            result = {"status": "PASS", "output": str(args.output.resolve()), "revision": result["revision"]}
        elif args.command == "capture":
            from contour.intent import capture_contract
            result = capture_contract(read_json(args.plan)["constraints"])
            write_new(args.output, result)
            result = {"status": "PASS", "output": str(args.output.resolve()), "rules": len(result["records"])}
        elif args.command == "check":
            from contour.intent import check_contract
            result = check_contract(read_json(args.baseline))
            write_new(args.output, result)
            result = {"status":result["status"],"output":str(args.output.resolve()),"checks":len(result["checks"]),
                      "failed":sum(item["status"]!="PASS" for item in result["checks"]),"reason":result.get("reason")}
        elif args.command == "edit":
            from contour.edits import apply_plan
            result = apply_plan(read_json(args.plan), args.output, args.report)
            result = {"status": result["status"], "output": result["output"], "report": str(args.report.resolve()),
                      "reason": result.get("reason")}
        elif args.command == "packet":
            from contour.packet import make_packet
            framing = read_json(args.framing)["framing"] if args.framing else None
            result = make_packet(args.output_dir, args.objects, args.views, args.modes, args.resolution,
                                 args.purpose, args.question, not args.no_render, framing, args.preview_triangles)
        elif args.command == "episode":
            from contour.episodes import build
            result = build(args.name, args.output)
        elif args.command == "deliver":
            from contour.delivery import delivery
            result = delivery(args.output, args.report, args.objects, args.triangle_budget, args.tolerance_m)
            result = {"status":result["status"],"output":result["output"],"report":str(args.report.resolve()),
                      "reason":result.get("reason")}
    print("CONTOUR_RESULT "+json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
    if result.get("status") == "FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
