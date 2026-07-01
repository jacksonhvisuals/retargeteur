# Rokoko Retargeting

Rokoko Retargeting is a Blender 5.0+ Extension for retargeting an existing
armature action onto another armature.

This extraction intentionally does not include Rokoko Studio live streaming,
recording, browser sign-in, telemetry, update checks, or the Studio Command API.

## Features

- Select a source armature with an existing action.
- Select a target armature to receive the retargeted action.
- Build an editable source-to-target bone mapping list.
- Auto-detect common bone names, including Rokoko action exports.
- Add manual mapping rows for custom rigs.
- Retarget with rest-pose or current-pose alignment.
- Optionally auto-scale the source armature during retargeting.
- Save, import, export, and clear custom bone naming schemes.

## Installation

Install this directory as a Blender Extension. The extension metadata is defined
in `blender_manifest.toml`.

## Usage

1. Open Blender 5.0 or newer.
2. Enable the Rokoko Retargeting extension.
3. Open the 3D View sidebar and select the Rokoko tab.
4. Choose a source armature that has an action.
5. Choose a different target armature.
6. Click Build Bone List.
7. Review and edit the bone mapping list.
8. Choose Auto Scale and Rest/Current pose options as needed.
9. Click Retarget Animation.

The extension creates a new action on the target armature and removes temporary
helper objects and constraints after baking.

## Custom Bone Naming Schemes

Custom bone naming schemes are stored in Blender's extension/user data location,
not in the installed extension directory. Use the panel's Save, Import, Export,
and Clear controls to manage them.

The JSON format keeps the legacy `rokoko_custom_names`, `version`, `bones`, and
`shapes` keys for compatibility. This extension only reads and writes `bones`;
`shapes` is exported as an empty object.

## Development Checks

Run Python compilation and a stale-reference search before packaging the
extension.
