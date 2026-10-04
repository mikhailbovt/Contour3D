# Authoring tools and executable episodes

These are optional packaged helpers for an existing Blender. They do not limit ordinary Python/BMesh, external DCCs or a user's chosen workflow. Resolve `scripts/author.py` relative to the loaded skill, including after installation. Host commands use ordinary Python; Blender geometry commands use Blender's bundled Python/numpy. No pip installs are needed.

## Existing native source

Run from the user's workspace, with absolute paths and explicit new outputs:

```text
blender --background SOURCE.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- inspect --output NEW-inspection.json --objects "Panel" "Frame" --thickness --sections planes.json
blender --background SOURCE.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- snapshot --output NEW-snapshot.json --objects "Panel" "Frame"
blender --background SOURCE.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- packet --output-dir NEW-packet --objects "Panel" "Frame" --views iso front side --modes clay reflection silhouette --resolution 768
```

`planes.json` is an array such as `[{"normal":[1,0,0],"offset_m":0.03}]`. Dimensions, section coordinates, falloffs and tolerances are world metres, including scene unit scale and object transforms. Measurements use the current viewport graph/frame. Instances are additional evaluated geometry; render-only differences and excluded types are labelled. Discrete dihedral and directional thickness are diagnostic signals, not principal curvature, collision or minimum-wall certificates.

## Explicit edit plan

Start from [edit-plan.json](../assets/edit-plan.json), replace example object names and bind its source SHA-256, frame and metre scale from the current inspection. Saved-source edits require those fields. Every edit needs at least one meaningful constraint. Add all properties/parts needed to fulfill the request; a helper PASS certifies only the supplied contract.

```text
blender --background SOURCE.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- capture --plan plan.json --output NEW-baseline.json
blender --background SOURCE.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- edit --plan plan.json --output NEW-result.blend --report NEW-edit.json
blender --background NEW-result.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- check --baseline NEW-baseline.json --output NEW-recheck.json
```

`edit` captures the baseline internally as well. It rejects stale bindings, applies typed operations, checks the contract and saves a new `.blend`; failure restores supported mutations and writes a failure report with no accepted native output. It never executes a JSON expression or script. Existing files are not overwritten.

Operations:

| Kind | Fields and purpose |
|---|---|
| `set_control` | `control`, `value`. Native shape key, numeric object property or scalar modifier/GN input with explicit `minimum/maximum`. |
| `deform` | `object`, unique `name`, `center_m`, `radii_m`, `delta_m`, `maximum_displacement_m`, optional `protected_regions`. Compact C2 polynomial source influence retained as a relative native shape key. Rejects rigs/simulation and absolute-key sequences. |
| `repair_degenerate` | `object`, `distance_m` (default `1e-7`, max `0.001`). BMesh dissolve must reduce the larger source/evaluated tiny-triangle count. Diagnose source versus evaluated cause first. Rig/simulation requires explicit `allow_rigged_topology:true` and separate animation/weight checks. |
| `fit_controls` | `controls` (1–8), `targets`, `maximum_candidates` (1–60). Bounded coordinate search measures actual evaluated geometry and checks protected constraints on each candidate. Fails/rolls back if all tolerances are not reached. |
| `assign_base_color` | `object`, absolute `image`, `image_sha256`, `uv_layer`, optional `slot`, `shader_node`, `material_name`. Packs inspected sRGB pixels into a local copy of an existing Principled material. Preserves independent roughness/metallic. Requires an existing UV map. |

Control shapes: `{"kind":"shape_key","object":"Bridge","name":"Arch","minimum":0,"maximum":1}`; `{"kind":"object_property","object":"Panel","property":"crown_m","minimum":0,"maximum":0.04}`; or `{"kind":"modifier","object":"Panel","modifier":"Crown","property":"Socket_2","minimum":0,"maximum":0.04}`. Read actual names/socket identifiers; never invent them.

Fit targets are `bounds_extent` (`axis`, `target_m`, `tolerance_m`), `region_coordinate` (same plus `selector`) or `surface_ray_coordinate` (same plus `origin_m`, nonzero `direction`). Bounds/mean coordinates answer only those measurements; use a ray for a precise surface point. Declare a tight task-specific budget; reevaluate the representation after failed attempts.

Constraints:

- `object_unchanged`: exact object name and `properties` from `geometry`, `transform`, `materials`, `dependencies`, `dependency_structure`. Default protects the first four. Geometry includes source/evaluated topology, coordinates, source UVs, smoothing, assignments and shape keys. `evaluated_uv_tolerance` defaults to `1e-6` UV units because native bevel interpolation can differ by a float ULP; raw values are checked in addition to the quantized fingerprint.
- `dependencies` includes GN input values. `dependency_structure` permits changes of GN custom input values while protecting modifiers, driver definitions, parent/constraint relationships and node groups. Use that narrower scope only for intentionally coupled native controls; explicitly check the expected changed output.
- `region_position`: exact object, `selector`, `evaluated` (default true), `tolerance_m`, optional `normal_tolerance_degrees`. Protect attributes propagated to evaluated points when available. A source-only invariant does not protect a Solidify inner rim.
- `bounds_unchanged`: exact object and `tolerance_m`. It covers only world bounds, not full silhouette or interior geometry.

Selectors: scalar point `attribute` with `name/threshold`; source-only `vertex_group`; world `sphere` with `center_m/radius_m`; or exact `indices` with a matching `topology_signature`. Empty regions fail. A topology/correspondence change returns UNKNOWN and blocks acceptance. Scene frame/scale changes also fail. Shader fingerprints traverse shared groups, socket defaults, links, ramps, driver definitions and packed/file/generated image bytes. Animation, simulation caches, complex nested RNA, UDIM/sequence evaluation remain outside certification.

Texture dependencies use resolved external paths and actual bytes, or packed bytes without their unused original filepath. Blender's legitimate relative-path remapping during Save As does not constitute a shader change. Contract fingerprints are versioned; recapture an older algorithm's baseline on its original source before comparison.

## Original construction episodes

```text
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- episode --name transition --output NEW-transition.blend
```

Seven fresh-scene episodes: `housing`, `transition`, `curved-insert`, `sweep`, `assembly`, `imported-repair`, `materials`. Sources, controls, materials and intent are ordinary Blender data. They reopen without importing the plugin. Study the episode whose representation fits the brief; they are development examples, not expert-approved assets or independent benchmark holdouts.

Each episode's next edit matters: crown with a protected inner rim; shoulder shape key with fixed collars; coupled panel/bezel/insert crown with seat datum; middle Bezier controls with preserved ends; bridge arch with evaluated mount band; repair/deform a baked fixture; local shader/UV/resource transfer. Inspect new highlights and clearances, not just a successful script return.
