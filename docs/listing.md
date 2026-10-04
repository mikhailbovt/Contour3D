# Contour3D listing

| Field | Value |
| --- | --- |
| Developer | Mikhail Bovt |
| Version | 1.0.0 |
| Category | Developer Tools |
| Availability | All countries available through the directory |
| Plugin price | No purchase or subscription offered by Contour3D |

## English

**Subtitle:** Reference-guided 3D modeling

Contour3D helps Codex avoid modeling mistakes and improve results through references, measurements and checks. Build and refine editable Blender assets with curved forms, fitted details, assemblies, materials and UVs. Inspect source and evaluated geometry, preserve declared regions and dependencies, and roll back edits that fail their constraints.

Review real Blender renders and select parts or regions in a bundled local 3D workbench without MCP. Use built-in Codex imagegen for specific visual questions or material resources, then transfer accepted features into the native asset and check it again.

An existing Blender installation and local Codex execution are required. The plugin interface and documentation are in English. No dramatic improvement is guaranteed: quality also depends on the GPT model, the references and the chosen representation. Checks cover only the declared properties; artistic judgment and target-runtime validation remain necessary.

## Starter prompts

- Build an editable curved enclosure and verify a later curvature change.
- Refine this model using its references and preserve the selected mounting points.
- Use current renders to design a detail with imagegen, then implement and verify it in Blender.

## Links and requirements

- [Source and installation](https://github.com/mikhailbovt/Contour3D)
- [Release 1.0.0](https://github.com/mikhailbovt/Contour3D/releases/tag/v1.0.0)
- [Support](https://github.com/mikhailbovt/Contour3D/blob/main/SUPPORT.md)
- [Privacy Policy](https://github.com/mikhailbovt/Contour3D/blob/main/PRIVACY.md)
- [Terms](https://github.com/mikhailbovt/Contour3D/blob/main/TERMS.md)
- [Technical verification and limits](verification.md)

Verified locally on Windows with Blender 5.1.2 and Codex CLI 0.148.0. Other versions and platforms need their own validation. Contour3D does not host a cloud service or require its own API key; Codex and image-generation access follow the host product's terms and availability. Local Blender remains necessary for the native helpers.

The installable listing values are stored in [the portable manifest](../plugin/plugin.json), including the English description, release notes and unrestricted country targeting. Directory approval and visibility are separate from the GitHub release.
