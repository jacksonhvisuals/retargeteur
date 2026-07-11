import bpy
from . import core, operators, panels, properties


classes = (
    panels.retargeting.BoneListItem,
    panels.retargeting.RSL_UL_BoneList,
    operators.detector.SaveCustomBonesRetargeting,
    operators.detector.ImportCustomBones,
    operators.detector.ExportCustomBones,
    operators.detector.ClearCustomBones,
    operators.retargeting.BuildBoneList,
    operators.retargeting.AddBoneListItem,
    operators.retargeting.ClearBoneList,
    operators.retargeting.RetargetAnimation,
    panels.retargeting.RetargetingPanel,
)


def register():
    print("\n### Loading Retargeteur...")
    for cls in classes:
        bpy.utils.register_class(cls)
    properties.register()
    core.detection_manager.load_detection_lists()
    print("### Loaded Retargeteur successfully!\n")


def unregister():
    print("### Unloading Retargeteur...")
    properties.unregister()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    print("### Unloaded Retargeteur successfully!\n")


if __name__ == '__main__':
    register()
