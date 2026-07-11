# Retargeteur

Retargeteur is a Blender extension for retargeting an existing armature action
onto another armature. It requires Blender 4.5.0 or newer.

This is a modified extraction of the retargeting functionality from the
[Rokoko Studio Live Blender plugin](https://github.com/Rokoko/rokoko-studio-live-blender).
Live streaming, recording, sign-in, telemetry, update checks, and the Studio
Command API are not included.

## Installation

Install the extension in Blender from this directory. The package metadata is
defined in `blender_manifest.toml`.

## Usage

1. Open the 3D View sidebar and select the Retargeteur tab.
2. Choose a source armature with an action and a different target armature.
3. Click **Build Bone List**, then review or edit the bone mappings.
4. Choose the pose and auto-scaling options if needed.
5. Click **Retarget Animation**.

The retargeted action is assigned to the target armature. Temporary helper
objects and constraints are removed after baking.

Custom bone naming schemes can be saved, imported, exported, and cleared from
the panel. They are stored in Blender's extension/user data location rather
than in the installed extension directory.

## License

Licensed under the GNU Lesser General Public License, version 3 or later. See
[LICENSE.md](LICENSE.md). The Rokoko name and trademarks remain the property of
their respective owner; this project is not an official Rokoko product.
