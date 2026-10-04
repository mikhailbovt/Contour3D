# The local 3D workbench

The workbench is a bundled browser application for reviewing one Blender visual packet. It runs on loopback without MCP, a CDN or a publisher-operated backend. It is not advertised as a first-class native Codex extension.

```powershell
python plugin/skills/professional-3d/scripts/workbench.py --packet outputs/housing-packet/packet.json --lifetime-minutes 120
```

Open the exact printed `http://127.0.0.1:PORT/` URL in Codex. Keep the server running during review. The default lifetime is 120 minutes; the URL expires when that process stops.

1. Select a part or click a surface point. Orbit, change cameras, isolate a part or show its wireframe.
2. Choose a physical region radius and mark the area to preserve.
3. Examine **Surface** for real Blender renders. The live preview uses simplified materials and may sample large meshes.
4. In **Edit**, describe the change and optionally request a native control value. Save the request for Codex.
5. Ask Codex to resolve that request against the native source, apply an explicit edit contract and verify the result. A saved UI request is labeled `NOT_RUN` until native execution occurs.

The request records the selected source revision, frame, scale, requested controls and protected region. Preview indices are not trusted native correspondence. The **References** image picker previews files in the browser; built-in imagegen is invoked separately through Codex with the actual selected inputs.

The interface is in English. See the [packaged guide](../plugin/skills/professional-3d/references/workbench.md) for the full workflow and technical boundaries, and [privacy](../PRIVACY.md) for data handling.
