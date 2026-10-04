# Contour3D

**Reference-guided 3D modeling for Codex and Blender.**

Contour3D helps Codex avoid modeling mistakes and improve results through useful references, native measurements and checks after each meaningful edit. It keeps Blender assets editable and makes protected regions explicit.

It does not guarantee a dramatic quality increase. Results also depend on the GPT model, the brief, the references and the representation chosen for the asset.

[Download 1.0.0](https://github.com/mikhailbovt/Contour3D/releases/tag/v1.0.0) · [Getting started](docs/getting-started.md) · [Privacy](PRIVACY.md) · [Support](SUPPORT.md)

## What it adds

| Capability | Purpose |
| --- | --- |
| Editable construction sources | Seven examples for curved housings, transitions, inserts, sweeps, assemblies, mesh repair and materials. |
| Native and evaluated inspection | Inspect the source and the result after modifiers, including instances, sections, UV distortion and scoped thickness samples. |
| Protected edits | Change controls or local shape while checking the declared geometry, bounds, materials and dependencies. Failed constraints roll back supported mutations. |
| Local 3D workbench | Select parts and surface regions, examine real Blender renders and save revision-bound edit requests. No MCP server or CDN is needed. |
| Built-in Codex imagegen | Generate references or material resources for a specific uncertainty, record the actual inputs and transfer accepted features into the native asset. |
| Delivery checks | Reopen the editable source or export a static GLB and check its scale, triangle budget and bounds after reimport. |

## Install

Use Codex desktop with an existing Blender installation. The plugin does not install Blender, model weights or a separate image-generation service.

For a repository-based installation:

```powershell
codex plugin marketplace add https://github.com/mikhailbovt/Contour3D.git
codex plugin add contour3d@contour3d-dev
```

Start a new chat and select **Contour3D / Professional 3D**. For example:

> Build an editable curved enclosure with a seated perimeter frame, vents and fasteners. Use references to settle the proportions, preserve the native controls and verify a later curvature edit.

> Change this panel's curvature while preserving the evaluated inner rim and mounting points. Show real diagnostic renders and report which properties were checked.

> Use built-in Codex imagegen to resolve the design of this small detail from the current renders. Implement the selected features in Blender and compare using the same cameras.

The plugin interface and documentation are in English. See [getting started](docs/getting-started.md) for direct helper commands and [the workbench guide](docs/workbench.md) for interactive review.

## Requirements and verification

Verified locally on Windows with Blender **5.1.2**, Python **3.14.5** and Codex CLI **0.148.0**. Geometry helpers use Blender's bundled Python and NumPy; host helpers use ordinary Python. No additional pip packages are required. Other Blender/client combinations require their own check.

The automated suite covers protected edits, rollback, shader dependencies, source/evaluated differences, native reopening, local request boundaries and static GLB roundtrips. These are technical checks, not an independent artistic-quality benchmark. Read [verification and limits](docs/verification.md).

The workbench is a bundled local browser application. Registration as a first-class native Codex extension is not claimed. Engine-specific rigs, animation, collision, calibrated PBR and fabrication-grade surface continuity require separate validation.

## Develop

[Development guide](docs/development.md) · [Architecture](docs/architecture.md) · [Changelog](CHANGELOG.md)

The source tree contains the distributable plugin, focused tests, the package builder and user documentation. Generated assets, private projects, research drafts and build outputs are excluded.

## License

Copyright 2026 **Mikhail Bovt**. Original code is licensed under [Apache-2.0](LICENSE). Bundled Three.js retains its [MIT license and provenance](plugin/assets/workbench/THIRD_PARTY.md). Blender and user assets are not distributed with the plugin.
