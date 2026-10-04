# Development

The runtime uses an existing Blender installation and its bundled Python/NumPy. Host helpers and the unit suite use the Python standard library. The viewer's pinned dependency and license are already included in the repository.

## Host checks

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python tools/package_plugin.py --validate-only
```

## Blender checks

Use a new output directory for each native regression run:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/blender_upgrade.py -- outputs/verification-NEW
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/blender_integration.py
```

`tests/housing_verification.py` exercises the original retained Geometry Nodes source and a subsequent native edit. Run it against the fresh packaged housing example with new output/report paths; it never loads the plugin to reopen the result.

## Package

```powershell
python tools/package_plugin.py --output-dir dist
```

The builder validates manifest consistency, references, payload limits and bundled dependency hashes. It produces a deterministic ZIP and a file-by-file SHA-256 receipt. Existing differing outputs are not overwritten.

Keep both manifests, the public listing, source license and packaged policy documents consistent. Preserve the upstream Three.js notices. Generated scenes, private references, local reports and distributions belong outside the committed source tree.

CI runs the host suite and package validation on Windows and Linux. It does not substitute for Blender-native checks or artistic review. For contributions, describe the behavior being changed and include focused validation appropriate to that change.
