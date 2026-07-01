from bpy.types import Object, Scene
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, PointerProperty

from .core import retargeting
from .panels import retargeting as retargeting_ui


scene_properties = (
    "rsl_retargeting_armature_source",
    "rsl_retargeting_armature_target",
    "rsl_retargeting_auto_scaling",
    "rsl_retargeting_use_pose",
    "rsl_retargeting_bone_list",
    "rsl_retargeting_bone_list_index",
)


def register():
    Scene.rsl_retargeting_armature_source = PointerProperty(
        name='Source',
        description='Select the armature with the animation that you want to retarget',
        type=Object,
        poll=retargeting.poll_source_armatures,
        update=retargeting.clear_bone_list
    )
    Scene.rsl_retargeting_armature_target = PointerProperty(
        name='Target',
        description='Select the armature that should receive the animation',
        type=Object,
        poll=retargeting.poll_target_armatures,
        update=retargeting.clear_bone_list
    )
    Scene.rsl_retargeting_auto_scaling = BoolProperty(
        name='Auto Scale',
        description='This will scale the source armature to fit the height of the target armature.'
                    '\nBoth armatures have to be in T-pose for this to work correctly',
        default=True
    )
    Scene.rsl_retargeting_use_pose = EnumProperty(
        name="Use Pose",
        description='Select which pose of the source and target armature to use to retarget the animation.'
                    '\nBoth armatures should be in the same pose before retargeting',
        items=[
            ("REST", "Rest", "Select this to use the rest pose during retargeting."),
            ("CURRENT", "Current", "Select this to use the current pose during retargeting.")
        ]
    )
    Scene.rsl_retargeting_bone_list = CollectionProperty(
        type=retargeting_ui.BoneListItem
    )
    Scene.rsl_retargeting_bone_list_index = IntProperty(
        name="Index for the retargeting bone list",
        default=0
    )

def unregister():
    for attr in reversed(scene_properties):
        if hasattr(Scene, attr):
            delattr(Scene, attr)
