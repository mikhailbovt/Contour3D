from pathlib import Path
import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
import io

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("package_plugin",ROOT/"tools/package_plugin.py")
pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)


class PackagingTests(unittest.TestCase):
    def test_distributable_has_only_resolvable_resources(self):
        manifest,files=pack.validate()
        self.assertEqual(manifest["name"],"contour3d")
        self.assertGreater(len(files),2)
        self.assertEqual(dict(files)["LICENSE"], (ROOT/"LICENSE").read_bytes())

    def test_archive_is_reproducible_and_payload_survives(self):
        items=[("skills/x.txt",b"some bytes\n"),("plugin.json",b"{}")]
        first=pack.archive_bytes(items)
        self.assertEqual(first,pack.archive_bytes(list(reversed(items))))
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual({name:archive.read(name) for name in archive.namelist()},dict(items))

    def copied_tree(self,directory):
        target=Path(directory)/"plugin"
        shutil.copytree(pack.PLUGIN,target)
        return target

    def test_manifest_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=self.copied_tree(temporary)
            path=root/".codex-plugin/plugin.json"
            data=json.loads(path.read_text(encoding="utf-8"));data["skills"]="./../outside"
            path.write_text(json.dumps(data),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"resource path"):
                pack.validate(root)

    def test_large_baseline_geometry_cannot_leak_into_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=self.copied_tree(temporary)
            (root/"private-baseline.blend").write_bytes(b"BLENDER")
            with self.assertRaisesRegex(ValueError,"benchmark geometry"):
                pack.validate(root)

    def test_missing_card_and_identity_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=self.copied_tree(temporary)
            (root/"skills/professional-3d/references/form-surfaces.md").unlink()
            with self.assertRaisesRegex(ValueError,"Unresolved package reference"):
                pack.validate(root)

    def test_listing_and_vendor_bytes_are_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=self.copied_tree(temporary)
            for filename in ['plugin.json','.codex-plugin/plugin.json']:
                path=root/filename;data=json.loads(path.read_text(encoding='utf-8'))
                interface=data['extensions']['com.openai']['interface'] if filename=='plugin.json' else data['interface']
                interface['shortDescription']='x'*31
                path.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'30 characters'):pack.validate(root)
        with tempfile.TemporaryDirectory() as temporary:
            root=self.copied_tree(temporary)
            (root/'assets/workbench/vendor/OrbitControls.js').write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):pack.validate(root)
        with tempfile.TemporaryDirectory() as temporary:
            root=self.copied_tree(temporary)
            path=root/"plugin.json";data=json.loads(path.read_text(encoding="utf-8"));data["version"]="0.2.0"
            path.write_text(json.dumps(data),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"identity/version differ"):
                pack.validate(root)


if __name__=="__main__":
    unittest.main()
