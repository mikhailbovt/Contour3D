# Evidence that answers the actual quality question

Use for final acceptance, targeted diagnostic observations or comparison of variants. Define the question first: silhouette, smooth transition, fit, topology, material appearance, budget or editability. Produce the relevant observation through the existing Blender workflow.

## Views and measurements

| Question | Useful evidence | Does not prove |
|---|---|---|
| Proportion and silhouette | Aligned orthographic views, known dimension, matched reference framing | Hidden construction or correct reflection flow |
| Broad surface flow | Neutral clay, grazing view, reflection strips, key sections | Exhaustive mathematical surface regularity |
| Aperture/joint fit | Local section, measured gap and wall, corner crop | Every possible intersection/assembly position |
| Topology cause | Wireframe plus native/evaluated mesh inspection | Aesthetic quality from quad ratio |
| Material/UV | Material/checker views, texel scale, clean reimport | Fidelity in an untested runtime |
| Further edits | A new substantive edit with measured invariants, save/reopen | Universal editability from file opening alone |

Use matching camera, pose, material and lighting for a before/after question. If one changed, disclose it and do not attribute the visual difference entirely to geometry. A material override must actually affect the chosen render engine; inspect the output rather than assuming the override was applied.

## Defect record

For an unresolved issue, record its location, visible symptom, likely cause, evidence and next discriminating check. Prioritize silhouette and major transitions, then interfaces and prominent secondary forms, before inconsequential microdetail. Rank by the asset's use and views, not just a count of diagnostic warnings.

Task-specific criteria can yield `PASS`/`FAIL`. Missing measurements remain `NOT_CHECKED`; ambiguous or insufficient evidence remains `UNKNOWN`. Degenerate triangles are a technical signal to inspect. An open sheet, triangle, high polygon count or UV overlap is not inherently a failure.

The optional [scene_probe.py](../scripts/scene_probe.py) can produce an explicitly scoped mesh audit through an existing Blender process. It writes a new JSON file and does not edit/save the scene. Its viewport evaluation omits instances, curves and render-only modifier differences; use native observations for those cases. It cannot assign professional quality or certify a protected edit.

## Native source and delivery copy

Preserve useful cages, profiles, curves, modifiers, material sources and important part relationships in the authoring file. Apply modifiers/triangulate only where a delivery copy requires it. Keep native units, scene scale and the requested transforms documented.

Save and reopen the ordinary `.blend` without executing unknown embedded code. Check needed images and data dependencies. For a requested export, use the existing exporter, format validator when available, and clean reimport. Reimport checks format/content; test the target game/application separately when required.

## Claims and fair comparison

Report technical validation, visual inspection, independent artistic review and target-runtime tests separately. A frozen old asset can reveal development problems; it does not by itself prove that the plugin beats the current Codex.

For a causal comparison, use the same task inputs, model/client, Blender/tools, hardware, permission scope and total budget. Evaluate the raw asset before manual cleanup. Count failed and assisted runs. Preserve the evidence for disagreements and ties. A hand-authored example demonstrates a representation and checks; it is not a blinded plugin-versus-baseline experiment.
