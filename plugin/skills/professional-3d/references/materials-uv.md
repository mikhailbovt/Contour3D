# Materials, UVs and their delivery form

Use when material appearance, physical scale, shared shaders, texture quality or export conversion is part of the request. Evaluate form in a neutral view first. A successful material pass cannot repair an incorrect primary shape.

## Material decisions

Choose coherent base color, roughness and metalness for the intended substance. Coated metal is not necessarily a fully metallic surface; exposed metal and its coating may need different treatments. Use broad roughness structure to explain wear and handling rather than uniform random noise on every part.

Set microdetail in a meaningful physical scale. Inspect a known dimension in the scene and a close-up at the intended viewing distance. Oversized grain, repetitive wear and excessive normal strength can make a clean shell appear dented. Texture resolution is useful only with adequate UV scale and a realistic view.

Before changing a material, find its users and nested node-group users. Preserve protected users by making the intended resource single-user when appropriate; do not silently recolor other parts. Keep the shared version when a consistent assembly-wide change is requested.

## UV decisions

Choose seams according to surface curvature, hidden boundaries, fabrication and the required texture behavior. Inspect stretching on the highest-curvature areas, not just a flattened island outline. Use a checker or another available distortion view and compare physical texel density across important parts.

Mirrored/overlapping UVs can be appropriate for repeating materials and symmetric surfaces. They are inappropriate where unique text, asymmetric wear or a bake requires unique correspondence. Specify permitted overlap by usage instead of a universal prohibition.

Choose padding from target resolution, mip behavior and bake needs. Inspect labels and instruments at an actual target distance; a readable close-up does not prove legibility in the expected view. Check face material assignments on repaired/replaced topology.

## Native shader versus export

Keep the authoring shader in the `.blend`. For delivery, inspect whether the requested format supports its effects. Use an agreed bake or simplified delivery material for unsupported features; preserve the source and report the conversion. Never silently replace a procedural shader with an unrelated flat fallback.

Check image color spaces, normal orientation and expected roughness/metalness packing against the chosen exporter/runtime. Use the existing unwrap, bake and exporter. A successful GLB validator run checks format validity; it cannot establish material fidelity in Cyberpunk or another runtime.

## Evidence and changes

Inspect neutral, material and relevant UV/checker views. Reopen the native file with textures resolved or packed as required. If export is requested, reimport in a clean scene and compare dimensions, parts and material assignments, plus the appearance that matters to the brief.

Test a material change on one part and a scale change of a mapped surface. Protected neighbors and physical pattern scale should behave as intended. State any missing target-runtime verification.

Good: consistent material scale and a deliberate native-to-delivery conversion. Bad: dense procedural dirt hiding a rippled shape, or packed PNGs treated as proof that all exported shaders match.

Negative cases: intentional UV tiling outside 0–1, mirrored non-textured geometry, and glass whose appearance varies with environment. Development coverage should include painted metal, a polymer assembly and a label-bearing surface; avoid three palette variants of one prop.
