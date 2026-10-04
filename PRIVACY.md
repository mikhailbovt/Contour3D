# Privacy Policy

**Contour3D · Publisher: Mikhail Bovt · Effective date: October 4, 2026**

This policy describes the Contour3D plugin distributed from [mikhailbovt/Contour3D](https://github.com/mikhailbovt/Contour3D). It applies to the plugin's own code and support channels. Codex, OpenAI, Blender and GitHub have their own terms and data practices.

## Data used by the plugin

Contour3D works with the files and references selected for a modeling task. These can contain geometry, UVs, materials, images, scene and object names, local file paths, edit instructions and user-authored metadata. File paths or metadata may contain personal information.

The helpers create local inspection reports, hashes, render packets, edit plans, request records, generated-resource records and native/export files. This information is used to model the selected asset, identify the current revision, check protected properties and document the resulting changes.

Contour3D does not create a publisher account, request credentials, run analytics or send telemetry to Mikhail Bovt. Its local workbench has no external backend and bundles its viewer without a CDN. The server binds to `127.0.0.1` and serves only the selected packet and application resources. Reference images selected in the workbench are previewed in the browser and are not uploaded by that picker.

## Codex and image generation

When you use Contour3D through a hosted Codex session, the conversation, selected images and tool outputs that the host processes may be sent to OpenAI under the rules and settings of your account. A reference or render supplied to built-in Codex image generation is processed by that host service. The plugin does not provide a separate image-generation account or API client.

Local execution therefore does not make the entire Codex workflow offline. Review your host's privacy and data controls before using confidential models or references. [OpenAI privacy information](https://openai.com/policies/privacy-policy/) applies to OpenAI's processing.

## Recipients and support

The publisher does not operate a Contour3D cloud storage service or receive modeling files automatically. OpenAI receives information processed through its hosted features. GitHub processes repository visits, downloads and information you submit through GitHub under its own policies.

If you open a GitHub issue or discussion, your GitHub username, message and attachments may be public and accessible to the publisher and other visitors. These are used to respond to support requests and diagnose reported problems. Do not post confidential scenes, personal information, credentials or proprietary references in a public issue.

## Storage and retention

Generated files remain in the locations you choose until you delete them. Contour3D has no scheduled cleanup or publisher-side retention of your modeling data. Removing the plugin does not remove your `.blend` files, textures, reports or edit requests.

The workbench's selected-image previews and in-memory state last for the browser session. Its server lifetime is configurable and defaults to 120 minutes. Local access logs may appear in the launching terminal and are retained only as that terminal or your own logging setup retains them. The application does not maintain a publisher-operated access-log service.

Public GitHub support records remain available until removed through GitHub; repository history and third-party copies may persist. OpenAI and GitHub retention is governed by those services, not by this plugin.

## Your controls

You choose the scene, reference images, tool inputs and output locations. You can stop the workbench, close its tab, disable or uninstall the plugin, delete local generated files and use your host's data controls. You can edit or delete support content where GitHub permits; contact the publisher through the [support page](https://github.com/mikhailbovt/Contour3D/blob/main/SUPPORT.md) about a privacy concern. Avoid adding further sensitive data when contacting support.

## Updates

Material changes to the plugin's data practices will be documented by updating this policy and its effective date in the public repository and release package.
