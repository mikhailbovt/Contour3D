# Local edits and protected dependencies

Use for a meaningful change to an existing asset: crown, dimension, aperture, detail placement or repair. Establish the smallest editable region and the exact properties that must stay stable. Continue from the real scene, not a regenerated interpretation of a preview.

## Define a practical edit contract

Record the requested effect with units, current checkpoint, editable objects/regions and protected constraints. An object-name list is sufficient for a whole-object constraint; a partial deformation also needs a spatial/semantic region and boundary tolerance. Preserve the current project structure.

Different constraints need different comparisons:

- A completely protected object: compare its source, evaluated geometry, transform and relevant material/dependency data.
- A rim that must seat on another part: compare boundary location, normal/tangent behavior when required, and mating clearance.
- A mounting position: compare the actual fastening plane or world-space datum, not the object origin alone.
- A protected material: inspect shared node groups, textures and material users as well as the local slot.

`PASS` means the stated property was checked within its stated tolerance. `UNKNOWN` means the available method cannot decide. `NOT_CHECKED` means no check was performed. Keep coverage explicit, especially for evaluated meshes, drivers, animation or sampling.

## Choose what to edit

Prefer changing a preserved source when it naturally expresses the request: a section crown, cage control, curve path or available node input. For a fixed-rim crown change, use a smooth local deformation whose value and required boundary derivative vanish at the protected rim. Inspect the deformed thickness and new interior clearances as well.

Check the inside rim after thickness evaluation. An ideal zero boundary derivative does not freeze discrete mesh normals: Solidify can move the inner edge while the outer rim appears fixed. In the included enclosure example, a small undeformed seating band preserves both sides through a crown change. Label the actual source boundary when useful; an inferred broad spatial band may include interior vertices that are intentionally allowed to move.

For an imported mesh, a constrained lattice/cage or a localized mesh edit may be appropriate. Reacquire the region after a topology change. Face and vertex indices are correspondence only when the topology and order were actually preserved.

Keep dependent trim or vent groups anchored to the relevant source/frame. A shape change should not require guessing every accessory's new world coordinate. Conversely, a fully protected insert must not follow a deformed skin automatically when the contract says its seat is fixed.

## Working copy and acceptance

Save a working version or checkpoint before a risky change. Choose the most useful actual Blender operation; there is no mandatory command DSL. Inspect the effect before overwriting a last accepted result. Failed experiments can be discarded without rebuilding the original.

Check protected geometry and shared datablocks, repeat the diagnostic views that justify the edit, and inspect the affected interfaces. A preserved transform does not imply a preserved object when its shared mesh or shader changed. A numeric boundary pass does not establish a good highlight across the changed surface.

Reopen the new native file. Test a second meaningful edit to a different parameter to expose accidental baking or lost dependencies. The scene should remain editable in ordinary Blender without the plugin.

Good: a crown changes while a measured rim, mounting plane and independent material stay stable. Bad: remaking the entire object and accepting roughly matching silhouettes as proof that protected geometry survived.

Counterexamples: a shared material recolors a protected neighbor; a node group is shared between assemblies; a cage edit moves a protected seam through an unapplied modifier. Development coverage should include a procedural shell, an imported mesh and a linked assembly, with curvature and secondary-feature changes.

Use the [packaged authoring tools](authoring-tools.md) for snapshots, explicit region/property contracts, bounded native controls, local deformation, fit and rollback when appropriate. Select `dependencies` when input values must remain fixed, or the narrower `dependency_structure` for deliberately coupled changing GN values. Protect evaluated interfaces separately. Construction controls and their next-edit limits are indexed in [episodes.json](../assets/episodes.json).
