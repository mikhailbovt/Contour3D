# Architecture

Contour3D is a portable plugin package with a short skill entrypoint, conditional authoring guides, executable Blender helpers and a bundled local review application. It uses the GPT model and execution/image tools supplied by the host.

```text
Codex + references
        |
        v
Professional 3D skill -> native Blender construction/edit
        |                         |
        |                  inspect / contracts
        |                         |
        +---- imagegen <---- real render packet
                     |            |
               native transfer   local 3D review
                     |            |
                     +-- verify --+ -> editable .blend / checked static GLB
```

## Components

- `plugin/plugin.json`: portable identity and OpenAI listing metadata.
- `plugin/.codex-plugin/plugin.json`: matching compatibility metadata.
- `plugin/skills/professional-3d`: entrypoint, conditional references, source episodes and helper scripts.
- `scripts/author.py`: inspection, snapshots/contracts, edits, render packets, episodes, delivery and image-resource evidence.
- `scripts/contour`: Blender measurement, intent, transaction, construction, rendering, delivery and provenance modules.
- `scripts/workbench.py` and `plugin/assets/workbench`: a bounded loopback server and bundled Three.js UI.
- `.agents/plugins/marketplace.json`: repository-based installation source, separate from official directory publication.

## Evidence and intent

Geometry checks use world metres, the declared frame and the relevant dependency graph. Source and evaluated results are distinct. Snapshot fingerprints include native geometry, transforms, shader groups and resource bytes, and relevant dependencies.

An edit declares its protected properties and passes only that contract. Supported mutations roll back when required checks fail; accepted outputs use new native files. An imagegen result is an additional design/resource hypothesis, never proof that the native model has those features.

The application stores revision-bound requests and serves only its selected packet and bundle. It exposes no arbitrary Blender execution endpoint. Its boundaries do not sandbox normal Blender Python that the user authorizes through Codex.

There is no bundled LLM, Blender binary, model download, mandatory MCP server or publisher-operated storage service. First-class host-extension registration, independent artistic-quality uplift and engine-specific runtime certification are separate from this implementation.
