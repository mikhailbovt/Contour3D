# Getting started

## Use through Codex

Install the plugin from the official directory when it is available, or use this repository marketplace:

```powershell
codex plugin marketplace add https://github.com/mikhailbovt/Contour3D.git
codex plugin add contour3d@contour3d-dev
```

Start a new Codex chat, select Contour3D / Professional 3D and describe the asset, intended use, scale and available references. An existing Blender installation is required for the native geometry helpers. Contour3D does not install or launch a paid service.

A useful brief is specific about both the change and what must remain intact:

> Increase this enclosure's crown by 4 mm. Preserve the evaluated seating rim, fasteners and neighboring shaders. Keep the original file, show diagnostic renders and verify that the new source reopens.

For a small transform or material change, the workflow can stay small. Complex modeling uses relevant construction and inspection procedures while retaining normal Blender Python, BMesh, curves, modifiers and Geometry Nodes.

## Direct helper commands

Run from a checkout. These PowerShell examples use the standard Windows Blender path; substitute your actual installation if different. Outputs must be new files.

```powershell
$contourBlender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$contourAuthor = (Resolve-Path 'plugin/skills/professional-3d/scripts/author.py').Path

& $contourBlender --background --factory-startup --disable-autoexec --python-exit-code 1 --python $contourAuthor -- episode --name housing --output outputs/housing.blend
& $contourBlender --background outputs/housing.blend --disable-autoexec --python-exit-code 1 --python $contourAuthor -- inspect --output outputs/housing-inspection.json
& $contourBlender --background outputs/housing.blend --disable-autoexec --python-exit-code 1 --python $contourAuthor -- packet --output-dir outputs/housing-packet --views iso front side --modes clay reflection --resolution 768
```

The episodes are `housing`, `transition`, `curved-insert`, `sweep`, `assembly`, `imported-repair` and `materials`. They create ordinary editable `.blend` files, not a required Blender add-on or custom file format.

For an installed plugin, resolve `author.py` relative to the skill that Codex actually loaded; do not assume the checkout's path exists on another computer.

## Protected edits and delivery

An edit plan binds the current source hash, frame and physical scale to explicit operations and constraints. Keep meaningful protections: an object, a seating region, a dependency or a material that matters to the requested change. A passed contract covers only the declared properties.

See [authoring tools](../plugin/skills/professional-3d/references/authoring-tools.md) for plan fields and command examples, [imagegen](../plugin/skills/professional-3d/references/imagegen-flow.md) for purposeful generated resources and [production profiles](../plugin/skills/professional-3d/references/production-profiles.md) for delivery.

The interactive application saves a request, not an automatic completed Blender edit. Continue that request through Codex, check the resulting native asset and refresh the packet. See [the workbench guide](workbench.md).
