"""Validate the distributable tree and build a deterministic local plugin ZIP."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin"
MAX_BYTES = 25 * 1024 * 1024


def validate(root=PLUGIN):
    root = root.resolve()
    portable = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    overlay = json.loads((root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if portable["name"] != overlay["name"] or portable["version"] != overlay["version"]:
        raise ValueError("Portable and compatibility identity/version differ")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", portable["name"]):
        raise ValueError("Invalid plugin name")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-z0-9.-]+)?", portable["version"]):
        raise ValueError("Invalid plugin version")
    if portable.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
        raise ValueError("Unexpected portable schema")
    interface = portable.get("extensions", {}).get("com.openai", {}).get("interface")
    if interface != overlay["interface"]:
        raise ValueError("Portable and compatibility presentation differ")
    if len(interface["shortDescription"]) > 30:
        raise ValueError("Listing subtitle exceeds 30 characters")
    if any(key in portable for key in ["skills", "interface", "mcpServers", "apps"]):
        raise ValueError("Unexpected portable top-level extension")
    if portable.get("extensions", {}).get("com.openai", {}).get("apps") or overlay.get("apps") or (root/".app.json").exists():
        raise ValueError("Unverified app binding is not distributable")
    for value in [overlay["skills"], overlay["interface"]["composerIcon"], overlay["interface"]["logo"]]:
        if not value.startswith("./") or ".." in Path(value).parts or "\\" in value:
            raise ValueError("Invalid manifest resource path: " + value)
        path = (root / value).resolve()
        if not path.is_relative_to(root) or not path.exists():
            raise ValueError("Missing or escaped manifest resource: " + value)
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if not skills:
        raise ValueError("No skill entrypoint")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Symlinks are not distributable: " + str(path))
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.suffix in {".blend", ".glb"}:
            raise ValueError("Build cache or benchmark geometry in package: " + relative)
        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", content):
                if "://" in target or target.startswith("#"):
                    continue
                linked = (path.parent / target.split("#", 1)[0]).resolve()
                if not linked.is_relative_to(root) or not linked.is_file():
                    raise ValueError(f"Unresolved package reference in {relative}: {target}")
        files.append((relative, path.read_bytes()))
    if sum(len(content) for _, content in files) > MAX_BYTES:
        raise ValueError("Uncompressed plugin exceeds 25 MiB")
    provenance_path = root/"assets/workbench/vendor/provenance.json"
    if provenance_path.is_file():
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        if provenance.get("license") != "MIT" or provenance.get("name") != "three":
            raise ValueError("Unexpected viewer dependency provenance")
        for name, checksum in provenance["files"].items():
            path = (provenance_path.parent/name).resolve()
            if not path.is_relative_to(provenance_path.parent) or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                raise ValueError("Viewer dependency checksum mismatch: " + name)
    return portable, files


def archive_bytes(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files):
            info = zipfile.ZipInfo(name, (2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def build(destination):
    manifest, files = validate()
    if not any(name == "LICENSE" for name, _ in files):
        files.append(("LICENSE", (ROOT / "LICENSE").read_bytes()))
    data = archive_bytes(files)
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{manifest['name']}-{manifest['version']}.zip"
    receipt = {
        "name": manifest["name"], "version": manifest["version"],
        "zip_sha256": hashlib.sha256(data).hexdigest(),
        "zip_bytes": len(data), "uncompressed_bytes": sum(len(value) for _, value in files),
        "files": [{"path": name, "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
                  for name, value in sorted(files)],
        "validation": "Local identity, resource paths, links and ZIP payload verified. Official catalog review and host discovery are separate checks.",
    }
    receipt_path = path.with_suffix(".manifest.json")
    receipt_bytes = (json.dumps(receipt, indent=2) + "\n").encode()
    for output, content in [(path, data), (receipt_path, receipt_bytes)]:
        if output.exists():
            if output.read_bytes() != content:
                raise ValueError("Existing artifact differs; choose a new destination or package version")
        else:
            with output.open("xb") as handle:
                handle.write(content)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupt archive")
        if archive.namelist() != sorted(name for name, _ in files):
            raise ValueError("Unexpected archive contents")
        for name, content in files:
            if archive.read(name) != content:
                raise ValueError("ZIP content mismatch: " + name)
    return {key: receipt[key] for key in ["name", "version", "zip_sha256", "zip_bytes", "uncompressed_bytes"]} | {"path": str(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        manifest, files = validate()
        print(json.dumps({"name": manifest["name"], "files": len(files), "status": "PASS"}))
    else:
        print(json.dumps(build(args.output_dir), indent=2))


if __name__ == "__main__":
    main()
