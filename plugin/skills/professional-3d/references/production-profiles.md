# Delivery profiles and task-specific acceptance

Select the profile from intended use. Professional delivery is judged by the asset and the next edit, not by a universal mesh score. Keep the native source and its intent/dependencies regardless of the requested export.

| Profile | Required checks |
|---|---|
| Editable concept/prop | Reference silhouettes, sections/highlights, native controls/dependencies, requested dimensions/interfaces, packed or supplied textures, reopening and a meaningful next edit |
| Static game prop | Above plus target triangle/material/texture budgets, UV/padding/texel scale, bake tangents/channel conventions, pivot/scale, explicit collision/LODs, actual engine import/view/runtime |
| Rigged character/vehicle | Pose/rig/weights/animation and deformation over representative frames, skeleton/datum conventions, LOD/collision/engine-specific export; static checks do not certify it |
| Fabrication/print | Intended closed volume versus deliberate sheets, physical minimum walls/clearances, manifold intersections/orientation, actual dimensions, slicing or target CAD/fabrication validation |
| Product/render | Reference/art direction, lighting-independent shape, grazing highlights, material scale/colour space, UV/resource consistency and final camera/light/render budget |

## Packaged static GLB roundtrip

Use only for static local geometry with no rigs/simulation, linked assets or unresolved instances. It exports current-frame geometry with modifiers, metre scale, UVs/normals and supported materials. It reimports the actual bytes in an isolated Blender scene and compares triangle count and world bounds. Source selection is restored, temporary importer data removed; new output paths are mandatory.

```text
blender --background SOURCE.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- deliver --objects "Part" "Frame" --output NEW-asset.glb --report NEW-delivery.json --triangle-budget 40000 --tolerance-m 0.00001
```

A PASS covers the stated static scope and reimport measurements. Source/export render comparison, exact shader fidelity, UV overlaps/padding, collision, LOD and target engine runtime are separate gates. The triangle budget is supplied by the actual brief. A large vehicle does not inherit a prop budget or become game-ready just because GLB roundtrip passes. A Cyberpunk target needs its specific supported mesh/material/rig pipeline and actual game verification.

If fabrication requirements are important, do not treat the inspector's directional thickness samples as a true global minimum or its dihedral metric as G2 continuity. Use appropriate volumetric/CAD/collision methods, preserve clear tolerances and state unmeasured conditions.
