# Diagnose geometry, normals and shading separately

Use when a surface has pinching, facets, seams, dents, nonplanar caps or imported topology problems. Locate the issue in an actual Blender image and identify the affected object/region. Keep a checkpoint and inspect both native and evaluated geometry before a repair.

## Separate causes

1. **Silhouette or section moves incorrectly:** likely geometry, representation or a modifier dependency. Normals cannot repair the silhouette.
2. **Clay shape is right but highlights break:** inspect face smooth flags, sharp edges, custom normals, tangent/normal mapping, bevel and weighted normals. Compare with a temporary simple shader. Check whether an exported material uses the same normal convention.
3. **Only material view looks wrong:** inspect scale, UVs, normal map strength/color space and shader conversion. Do not remesh the asset to repair a material assignment.
4. **Only the export looks wrong:** inspect triangulation, transforms, split vertices, tangents and material conversion. Keep the editable native source separate from a triangulated delivery copy.

## Find structural defects

Check zero/near-zero area triangles at a task-appropriate physical threshold, duplicate faces, loose geometry, inconsistent winding and edges with more than two incident faces. Boundary edges may be intentional sheet construction. Distinguish an intended sheet from a torn boundary through a solid part.

Inspect long skinny triangles near curved apertures and nonplanar ngons. A filled curved loop with a large cap can produce unstable triangulation and a shading fan. If that cap is supposed to be flat, rebuild it in its plane; if it is a formed surface, give it an appropriate interior surface representation.

For subdivision, inspect high valence points, tightly bunched support loops and abrupt spacing changes. Smooth shading and weighted normals do not remove geometric pinching on a broad curved reflection. Reduce or relocate the underlying cause before adding resolution.

## Repair locally

Choose the smallest repair that resolves the cause and preserves the intended surface. Merge only vertices whose distance and semantic boundary make the merge valid; a global merge can erase a purposeful seam. Preserve UVs, material assignments, rigid weights and sharp/smooth decisions when replacing topology.

Triangulate a delivery copy if export requires it. For a local nonplanar-cap issue, select the affected cap, control its triangulation or rebuild the surface, then compare shading. Avoid triangulating every clean quad source to fix one bad polygon.

Apply a normal fix only to a diagnosed normal problem. Test a changed bevel/normal order in the evaluated result. If normals depend on a source that was changed, update them deliberately; do not assume a stale custom normal layer is still valid.

A destructive remesh may be useful for some shapes. First account for loss of boundaries, thin walls, weights, UVs, source controls and detail. It is a poor default for a fitted assembly or a panel with dimension-critical mounts.

## Verify the effect

Repeat the exact diagnostic view that showed the defect, plus a relevant neighboring view. Recompute the offending signal and check protected data. Inspect the result after save/reopen and export when the defect concerns delivery.

Good: an isolated shading seam repaired without changing geometry or material users. Bad: a global smooth/remesh pass whose only evidence is a flattering new render.

Negative cases: deliberate open panels, mirrored UVs, a high-poly but correctly formed close-up surface, and an imported mesh without parametric sources. These cases prevent false defect classifications. Develop on a curved corner, a swept feature and a nonplanar imported cap; then test a later curvature and feature-size change.

The [inspector/repair helpers](authoring-tools.md) distinguish source from evaluated defects. A current-frame Armature result can collapse nearly coincident construction edges even when a double-precision source measurement has no triangles below the chosen threshold. Inspect that difference before editing topology or the rig. Repair acceptance must improve the actual evaluated result and preserve the stated interfaces, materials and other parts; current-frame success does not certify animation/weights.
