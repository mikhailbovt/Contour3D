"""Serve the bundled local 3D workbench and one explicitly selected packet.

No MCP, external network, arbitrary execution or native-file overwrite endpoint.
Region/edit requests are new revision-bound JSON artifacts for Codex to inspect.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import sys
import threading
from urllib.parse import unquote, urlsplit
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contour.common import finite_number, read_json, vector, write_new

ASSETS = Path(__file__).resolve().parents[3]/"assets"/"workbench"


def within(root, relative):
    if not relative or "\\" in relative or "\x00" in relative:
        raise ValueError("Invalid asset path")
    candidate = root/relative
    if candidate.is_symlink():
        raise ValueError("Symlinks cannot be served")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()) or any(part == ".." for part in Path(relative).parts):
        raise ValueError("Path escapes the selected packet")
    # Check parents, too: a contained symlink must not expose unrelated data.
    for parent in [candidate, *candidate.parents]:
        if parent == root.parent:
            break
        if parent.is_symlink():
            raise ValueError("Symlink parent is not allowed")
    return resolved


def validate_request(value, packet):
    if not isinstance(value, dict) or value.get("source_revision") != packet["revision"]:
        raise ValueError("Request is stale or does not belong to this packet")
    intent = value.get("intent", "")
    if not isinstance(intent, str) or not 1 <= len(intent.strip()) <= 8192:
        raise ValueError("Describe the requested edit in 1..8192 characters")
    objects = {item["id"]: item for item in packet["preview"]["objects"]}
    selection = value.get("selection")
    if not isinstance(selection, dict) or selection.get("id") not in objects:
        raise ValueError("Select a part from this exact preview")
    original = objects[selection["id"]]
    point = vector(selection["point_m"], "selection point") if selection.get("point_m") is not None else None
    protected = value.get("protected_regions", [])
    if not isinstance(protected, list) or len(protected) > 64:
        raise ValueError("Too many protected regions")
    regions = []
    for region in protected:
        if not isinstance(region, dict) or region.get("id") not in objects:
            raise ValueError("Protected region belongs to another scene")
        item = objects[region["id"]]
        regions.append({"id": item["id"], "source_id": item["source_id"], "name": item["name"],
                        "selector": {"kind": "sphere", "center_m": vector(region["center_m"]),
                                     "radius_m": finite_number(region["radius_m"], "region radius", 1e-9, 10000)},
                        "tolerance_m": finite_number(region.get("tolerance_m", 5e-6), "region tolerance", 0, 1)})
    changes = value.get("control_changes", [])
    if not isinstance(changes, list) or len(changes) > 32:
        raise ValueError("Invalid control changes")
    declared = {(obj["id"], index): control for obj in objects.values() for index, control in enumerate(obj["controls"])}
    controls = []
    for change in changes:
        key = (change.get("id"), change.get("index"))
        if key not in declared:
            raise ValueError("Control belongs to another source")
        control = declared[key]
        controls.append({"control": control, "requested_value": finite_number(change["value"], "control", control["minimum"], control["maximum"])})
    return {"schema_version": 2, "kind": "CONTOUR_WORKBENCH_REQUEST", "source_revision": packet["revision"],
            "source_sha256": packet["source_sha256"], "intent": intent.strip(),
            "frame": packet["frame"], "metres_per_blender_unit": packet["inspection"]["metres_per_blender_unit"],
            "selection": {"id": original["id"], "source_id": original["source_id"], "name": original["name"],
                          "instance": original["instance"], "point_m": point},
            "protected_regions": regions, "control_changes": controls,
            "status": "REQUESTED", "native_edit": "NOT_RUN",
            "scope": "UI request only. Codex must resolve native regions, check the source revision, construct an explicit edit contract and verify the resulting .blend. Sampled preview vertices are not trusted source correspondence."}


def make_server(packet_path, port=0):
    packet_path = Path(packet_path).resolve()
    if packet_path.is_symlink() or not packet_path.is_file():
        raise ValueError("Choose a saved packet.json")
    packet = read_json(packet_path)
    if packet.get("kind") != "CONTOUR_VISUAL_PACKET" or packet.get("schema_version") != 2:
        raise ValueError("Unsupported visual packet")
    folder = packet_path.parent
    data_allowed = {"packet.json", "inspection.json", "imagegen-prompt.txt"}
    data_allowed.update(render["path"] for render in packet["renders"])
    static_allowed = {path.relative_to(ASSETS).as_posix() for path in ASSETS.rglob("*") if path.is_file() and not path.is_symlink()}
    def resources():
        values = {}
        for path in sorted(folder.glob("generated-*.json")):
            try:
                if path.is_symlink():
                    continue
                record = read_json(path)
                if record.get("kind") == "GENERATED_IMAGE_RESOURCE" and record.get("source_revision") == packet["revision"]:
                    image_path = within(folder, record["output"])
                    if image_path.is_file() and image_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                        old=values.get(record["output"])
                        if old is None or record.get("status") == "TRANSFERRED_TO_NATIVE":
                            values[record["output"]]={**record, "record_path": path.name}
            except (ValueError, KeyError, OSError):
                continue
        return list(values.values())
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *values):
            print(fmt % values, file=sys.stderr, flush=True)

        def send(self, status, content, content_type="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(content)

        def valid_host(self):
            return self.headers.get("Host", "") in {"127.0.0.1:"+str(self.server.server_port), "localhost:"+str(self.server.server_port)}

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self.valid_host():
                self.send(403, b'{"error":"Host denied"}')
                return
            path = unquote(urlsplit(self.path).path)
            if path == "/api/resources":
                self.send(200, json.dumps(resources(), ensure_ascii=False).encode())
                return
            if path == "/api/status":
                self.send(200, json.dumps({"source_revision": packet["revision"], "source_file": packet["source_file"], "native_edit": "NOT_RUN"}).encode())
                return
            try:
                if path.startswith("/data/"):
                    relative = path[len("/data/"):]
                    allowed = data_allowed | {record["output"] for record in resources()}
                    if relative not in allowed:
                        raise ValueError("File was not explicitly selected")
                    target = within(folder, relative)
                else:
                    relative = "index.html" if path == "/" else path.lstrip("/")
                    if relative not in static_allowed:
                        raise ValueError("Unknown application asset")
                    target = within(ASSETS, relative)
                if not target.is_file():
                    raise ValueError("File missing")
                mime = "text/javascript" if target.suffix == ".js" else mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                self.send(200, target.read_bytes(), mime)
            except (ValueError, OSError):
                self.send(404, b'{"error":"Resource unavailable"}')

        def do_POST(self):
            if not self.valid_host() or urlsplit(self.path).path != "/api/requests":
                self.send(403, b'{"error":"Action denied"}')
                return
            expected_origin = "http://127.0.0.1:"+str(self.server.server_port)
            if self.headers.get("Origin") not in {expected_origin, "http://localhost:"+str(self.server.server_port)}:
                self.send(403, b'{"error":"Origin denied"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("Invalid request size")
                value = json.loads(self.rfile.read(length), parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
                result = validate_request(value, packet)
                destination = within(folder, "requests/"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]+".json")
                write_new(destination, result)
                self.send(201, json.dumps({"status": "SAVED", "request_path": str(destination), "native_edit": "NOT_RUN"}).encode())
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.send(400, json.dumps({"error": str(error)}).encode())
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--lifetime-minutes", type=int, default=120)
    args = parser.parse_args()
    if not 1 <= args.lifetime_minutes <= 1440 or not 0 <= args.port <= 65535:
        parser.error("Invalid lifetime or port")
    server = make_server(args.packet, args.port)
    timer = threading.Timer(args.lifetime_minutes*60, server.shutdown)
    timer.daemon = True
    timer.start()
    print(json.dumps({"url": "http://127.0.0.1:"+str(server.server_port), "packet": str(args.packet.resolve()),
                      "MCP": False, "native_edit_endpoint": False, "lifetime_minutes": args.lifetime_minutes}), flush=True)
    try:
        server.serve_forever(poll_interval=.25)
    finally:
        timer.cancel()
        server.server_close()


if __name__ == "__main__":
    main()
