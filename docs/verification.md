# Verification and limits

Contour3D uses technical checks to reduce avoidable modeling mistakes. A check answers a specific question about a particular asset, frame, dependency graph and tolerance. It does not assign an artistic-quality score.

## Covered by the test suite

- Known section lengths, UV anisotropy, source/evaluated differences, curve conversion and instances.
- Shared shader graphs, socket values, image-resource identity, frame and unit context.
- World-space local deformation, evaluated protected regions/normals, rollback and a subsequent edit after native reopening.
- Bounded fitting with protected constraints, exhaustion handling and stale-source rejection.
- Degenerate-mesh repair, source preservation and read-only real-render packets.
- Evaluated interfaces in a coupled assembly.
- Local packed texture isolation, relative image-path remapping and static GLB export/reimport at a non-unit scene scale.
- Local workbench Host/Origin/path/input/revision boundaries and request persistence.
- Reproducible packaging, metadata/resource consistency and pinned third-party bytes.

On October 4, 2026, the 1.0.0 source passed 14 host tests and seven Blender-native regressions. The earlier development run also passed the independent probe integration fixtures. Blender 5.1.2, Python 3.14.5 and Codex CLI 0.148.0 were used for local Windows verification. The repository's CI provides separate host checks; it does not run Blender.

## Observed workflows

Editable examples were built and meaningful curvature, insertion, sweep and assembly changes were saved and inspected. The built-in Codex imagegen workflow was exercised with actual Blender views, a saved output and a packed material transfer, followed by matched-camera native renders. The workbench was exercised interactively, including point selection, protected regions, bounded controls, request saving and a 480 px panel.

Examples and synthetic fixtures are authored for development. They are not independent holdouts or expert-approved reference assets.

## Limits

No dramatic or universal quality increase is promised. Results also depend on the GPT model, the brief, reference quality and the chosen representation. Independent expert review and controlled comparisons across new tasks have not established a numerical artistic-quality uplift.

Scoped wall samples, discrete dihedral and UV signals do not certify collision freedom, global minimum wall thickness, CAD-grade curvature continuity or calibrated PBR. Animation, full rig/weight behavior, simulation caches, complex nested RNA, UDIM/sequence evaluation and engine-specific runtime behavior need separate checks.

The live workbench preview simplifies materials and may sample triangles. Acceptance uses native measurements and actual Blender renders. Saving an application request does not perform or certify a native edit. Official directory approval is separate from local tests and package validation.
