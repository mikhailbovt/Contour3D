# Built-in Codex imagegen as an additional authoring tool

Use the host's existing imagegen capability. Do not introduce another provider, API key, account, paid image-to-3D service or MCP just for this flow. Discover the current tool arguments; follow the active imagegen skill. A tool/model version, reference limit or exact call syntax must come from the host rather than this card.

## Select a visual question

Generate when an explicit uncertainty blocks meaningful modeling: alternative silhouette/assembly layouts; reverse/hidden-side hypotheses; an enlarged detail crop; construction versus decoration; trim/seam/fastener language; repeated motif/decals; flat albedo concepts; controlled wear distributions; material scale; an exploded design study; or communication of a requested edit. Use observed references and native measurements directly when they already answer the question.

Create a visual packet with one purpose/question, real useful views and explicit protected properties. For a form edit, include neutral silhouettes and a reflection strip; for a detail, include a crop plus its placement in the complete asset; for a surface resource, include the actual UV/layout and material context. The packet never calls an external generation service by itself.

```text
blender --background SOURCE.blend --disable-autoexec --python-exit-code 1 --python AUTHOR.py -- packet --output-dir NEW-packet --views iso front top --modes clay reflection --purpose detail --question "Resolve this bezel's corner construction without moving its seat"
```

Inspect supplied images before generation. Choose the smallest relevant reference set. Preserve the accepted design's identity, camera, dimensions and protected interfaces in edit prompts. One initial call and one targeted refinement is the default per visual question; follow the user's budget. Stop if the result does not resolve the uncertainty and return to native modeling or new evidence.

## Use the image for its actual role

| Resource | What it can guide | What still needs native verification |
|---|---|---|
| Alternative/form study | Art direction, proportion hypotheses, broad feature hierarchy | Silhouettes, physical dimensions, source representation, all changed interfaces |
| New angle/hidden view | A plausible construction hypothesis | Cross-view identity and geometry; generated orthographic views are not a calibrated blueprint |
| Close detail/annotated crop | Shape language, placement, trim/seam continuity | Actual size, attachment, topology, local clearance and placement in full asset |
| Exploded/assembly image | Communication of candidate part relationships | Feasible assembly/fasteners and real mating surfaces |
| Flat albedo/decal/pattern | Colour motifs, markings, wear proposals | UV layout, seam/padding, resolution/texel scale, packed image and target colour space |
| Material/wear study | Artistic distribution and scale | Independent roughness/metallic/normal/displacement, lighting and target renderer |

Generate a new angle from the same accepted reference set, then explicitly compare unchanged landmarks. Cross-view disagreement remains uncertain; do not average incompatible views into authoritative dimensions. Keep original source/reference evidence distinct from generated hypotheses. Never compare a native before-render with a generated after-image as model-quality proof.

For albedo, ask for uniform flat colour appearance without baked illumination, perspective, shadows or object features. A physically complete PBR material is several independently evaluated channels; a generated colour image does not supply calibrated metallic/roughness or tangent-space normals. Geometry/detail synthesis is optional; inspect topology and editable provenance if a separate supported tool is used.

## Provenance and transfer

Persist the selected built-in output into the project, with the actual prompt and input render identities:

```text
python AUTHOR.py image-record --packet NEW-packet/packet.json --image ABSOLUTE_GENERATED_OUTPUT.png --prompt-file actual-prompt.txt --purpose albedo_design --features "coating motif" "calibration ticks" --input-renders iso-material.png top-material.png
```

The record binds input/source hashes, frame, exact source revision, prompt, selected output hash and accepted feature descriptions. It is `GENERATED_DRAFT`, even if visually polished. Only transfer accepted features into the actual curve/cage/mesh, native detail sources or shaders. Use `assign_base_color` when a packed UV resource on one local material is appropriate; otherwise use normal Blender scripting and the same protection/verification procedure.

Render the edited native result with the previous packet's framing (`packet --framing OLD/packet.json`), inspect it and reopen the file. Record transfer only from a successful edit report on the original source:

```text
python AUTHOR.py image-transfer --resource-record RECORD.json --native RESULT.blend --edit-report EDIT.json --output NEW-transfer.json --observations "State the accepted features and actual checks/limits"
```

`TRANSFERRED_TO_NATIVE` records that native output and scoped edit evidence exist; it is not an artistic approval. Keep unresolved seams, inconsistencies or runtime limitations visible in the handoff. Deliver the native asset and its needed packed/external resources, not only the generated picture.
