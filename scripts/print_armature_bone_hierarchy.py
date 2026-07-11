"""
Write the selected armature's bone hierarchy with exact name diagnostics.

Usage:
1. Open Blender.
2. Select a character armature, preferably making it the active object.
3. Paste this script into Blender's Text Editor and click Run Script.
4. Open /private/tmp/retargeteur_armature_bone_hierarchy.log.

The script does not modify the scene.
"""

import bpy


INDENT = "  "
LOG_PATH = "/private/tmp/retargeteur_armature_bone_hierarchy.log"


def get_selected_armature():
    """Return the active armature, or the only selected armature."""
    active_object = bpy.context.view_layer.objects.active
    if active_object and active_object.type == "ARMATURE":
        return active_object

    selected_armatures = [
        obj for obj in bpy.context.selected_objects
        if obj.type == "ARMATURE"
    ]

    if len(selected_armatures) == 1:
        return selected_armatures[0]

    return None


def format_parent_name(bone):
    if bone.parent:
        return repr(bone.parent.name)

    return "<root>"


def add_bone_tree_lines(lines, bone, depth=0):
    indent = INDENT * depth
    lines.append(
        f"{indent}{bone.name} | "
        f"repr={repr(bone.name)} | "
        f"len={len(bone.name)} | "
        f"parent={format_parent_name(bone)}"
    )

    for child in bone.children:
        add_bone_tree_lines(lines, child, depth + 1)


def build_armature_bone_hierarchy_report(armature):
    bones = armature.data.bones
    root_bones = [bone for bone in bones if bone.parent is None]

    lines = [
        "",
        "=" * 80,
        "Armature Bone Hierarchy Diagnostic",
        "=" * 80,
        f"Armature object: {armature.name}",
        f"Armature object repr: {repr(armature.name)}",
        f"Bone count: {len(bones)}",
        f"Root bone count: {len(root_bones)}",
        "-" * 80,
    ]

    if len(bones) == 0:
        lines.append("No bones found on this armature.")
    else:
        for root_bone in root_bones:
            add_bone_tree_lines(lines, root_bone)

    lines.extend([
        "=" * 80,
        "",
    ])

    return "\n".join(lines)


def write_log(contents):
    with open(LOG_PATH, "w", encoding="utf-8") as log_file:
        log_file.write(contents)
        if not contents.endswith("\n"):
            log_file.write("\n")


def main():
    armature = get_selected_armature()

    if armature is None:
        write_log(
            "\n"
            "ERROR: Select one armature, or make an armature the active object.\n"
            "No armature hierarchy was written.\n"
        )
        return

    write_log(build_armature_bone_hierarchy_report(armature))


if __name__ == "__main__":
    main()
