# Local 3D workbench without MCP

The bundled application is a working local browser UI over one selected visual packet. Three.js is bundled/pinned with its MIT licence; it has no CDN or external backend. This route does not claim registration as a first-class native Codex application extension. Verify any newer host-specific registration API before adding it; do not infer its absence from older Skill Creator documents.

```text
python WORKBENCH.py --packet ABSOLUTE-packet/packet.json --lifetime-minutes 120
```

Resolve `WORKBENCH.py` to `scripts/workbench.py` in this skill. The command prints the loopback URL on an OS-assigned port. Open that exact URL in the Codex browser/panel using the supported host API. Keep the process running for the requested review, mark a deliverable tab when useful, and report its lifetime. It binds only `127.0.0.1`. No Blender/add-on launch, login or MCP connection is required.

## Review and request

1. Inspect the part tree, orbit/frame the evaluated 3D preview, switch cameras or wireframe and select the actual desired surface point.
2. Set a physical region radius and mark protected areas; inspect their labels and tolerances in Edit. A sampled large-model preview is explicitly labelled. Preview material/normals are simplified; actual Blender renders in Surface are the acceptance evidence.
3. Describe the result and optionally request values for discovered native controls. Saving writes a new request JSON inside this packet. It does not silently modify Blender or declare the edit finished.
4. Read the returned artifact, verify its source revision/hash/frame/scale against the actual native source, and resolve preview IDs/instances to source objects. Convert its intended protected areas to stable native/evaluated regions. A clicked sphere may select no native vertices; refine its selector instead of dropping the invariant.
5. Create an explicit contract, perform the edit and verify the intended changed feature as well as the protections. Produce a new native file, report and new visual packet. Refresh review against that new revision.

The application's reference picker previews user images in the browser only. It does not upload them or persist an imagegen invocation. For generation, use the host's actual imagegen tool and provenance workflow. Generated resources recorded for the same packet appear as drafts, separately labelled from real renders.

The server allows only selected packet JSON/renders/resource images and its application bundle. It rejects path escapes, unselected native files, wrong Host/Origin, stale requests, nonfinite numbers and out-of-range declared controls. JSON is data; there is no arbitrary Python execution endpoint. These boundaries protect this local app route; they do not sandbox independently authorized Blender scripting.
