import copy
import time

import bpy

from ..core import action_compat, custom_schemes_manager, detection_manager as detector, utils
from ..core.retargeting import get_source_armature, get_target_armature

RETARGET_ID = '_RSL_RETARGET'


class BuildBoneList(bpy.types.Operator):
    bl_idname = "rsl.build_bone_list"
    bl_label = "Build Bone List"
    bl_description = "Build the bone list from the source action and automatically match target bones"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        armature_source = get_source_armature()
        armature_target = get_target_armature()

        if not armature_source or not armature_source.animation_data or not armature_source.animation_data.action:
            self.report({'ERROR'}, 'No animation on the source armature found!'
                                   '\nSelect an armature with an animation as source.')
            return {'CANCELLED'}

        if not armature_target:
            self.report({'ERROR'}, 'No target armature selected.')
            return {'CANCELLED'}

        if armature_source.name == armature_target.name:
            self.report({'ERROR'}, 'Source and target armature are the same!'
                                   '\nPlease select different armatures.')
            return {'CANCELLED'}

        retargeting_dict = detector.detect_retarget_bones()
        context.scene.rsl_retargeting_bone_list.clear()

        for bone_source, bone_values in retargeting_dict.items():
            bone_target, bone_key = bone_values
            bone_item = context.scene.rsl_retargeting_bone_list.add()
            bone_item.bone_name_key = bone_key
            bone_item.bone_name_source = bone_source
            bone_item.bone_name_target = bone_target

        return {'FINISHED'}


class AddBoneListItem(bpy.types.Operator):
    bl_idname = "rsl.add_bone_list_item"
    bl_label = "Add Bone List Item"
    bl_description = "Add a custom source-to-target bone mapping"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        bone_item = context.scene.rsl_retargeting_bone_list.add()
        bone_item.is_custom = True
        context.scene.rsl_retargeting_bone_list_index = len(context.scene.rsl_retargeting_bone_list) - 1
        return {'FINISHED'}


class ClearBoneList(bpy.types.Operator):
    bl_idname = "rsl.clear_bone_list"
    bl_label = "Clear Bone List"
    bl_description = "Clear the target side of the bone list"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        for bone_item in context.scene.rsl_retargeting_bone_list:
            bone_item.bone_name_target = ''
        return {'FINISHED'}


class RetargetAnimation(bpy.types.Operator):
    bl_idname = "rsl.retarget_animation"
    bl_label = "Retarget Animation"
    bl_description = "Retarget the source armature action to the target armature"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        armature_source = get_source_armature()
        armature_target = get_target_armature()

        if not armature_source or not armature_source.animation_data or not armature_source.animation_data.action:
            self.report({'ERROR'}, 'No animation on the source armature found!'
                                   '\nSelect an armature with an animation as source.')
            return {'CANCELLED'}

        if not armature_target:
            self.report({'ERROR'}, 'No target armature selected.')
            return {'CANCELLED'}

        if armature_source.name == armature_target.name:
            self.report({'ERROR'}, 'Source and target armature are the same!'
                                   '\nPlease select different armatures.')
            return {'CANCELLED'}

        self.retarget_bone_list = []
        for item in context.scene.rsl_retargeting_bone_list:
            if not item.bone_name_source or not item.bone_name_target \
                    or not armature_source.pose.bones.get(item.bone_name_source) \
                    or not armature_target.pose.bones.get(item.bone_name_target):
                continue
            self.retarget_bone_list.append(item)

        root_bones = self.find_root_bones(armature_target)
        if not root_bones:
            self.report({'ERROR'}, 'No root bone found!'
                                   '\nCheck if the bones are mapped correctly or try rebuilding the bone list.')
            return {'CANCELLED'}

        duplicates = self.find_duplicate_targets()
        if duplicates:
            self.report({'ERROR'}, 'Duplicate target bone entries found! Please use each target bone only once:'
                                   f'\n{", ".join(duplicates)}')
            return {'CANCELLED'}

        custom_schemes_manager.save_retargeting_to_list()

        utils.set_active(armature_target)
        bpy.ops.object.mode_set(mode='OBJECT')
        utils.set_active(armature_source)
        bpy.ops.object.mode_set(mode='OBJECT')

        armature_source.data.pose_position = 'POSE'
        armature_target.data.pose_position = 'POSE'

        if bpy.context.scene.rsl_retargeting_use_pose == 'REST':
            self.get_and_reset_pose_rotations(armature_source)
            self.get_and_reset_pose_rotations(armature_target)

        source_scale = None
        if context.scene.rsl_retargeting_auto_scaling:
            self.clean_animation(armature_source)
            source_scale = copy.deepcopy(armature_source.scale)
            self.scale_armature(armature_source, armature_target, root_bones)

        armature_source_original = armature_source
        source_action_original = action_compat.get_action(armature_source_original)
        armature_source = self.copy_rest_pose(context, armature_source)

        rotation_mode = armature_target.rotation_mode
        armature_target.rotation_mode = 'QUATERNION'
        rotation = copy.deepcopy(armature_target.rotation_quaternion)
        location = copy.deepcopy(armature_target.location)

        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_target)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        bpy.ops.object.mode_set(mode='EDIT')
        bone_transforms = {}
        for bone in context.object.data.edit_bones:
            bone.select = False
            bone_transforms[bone.name] = (
                armature_source.matrix_world.inverted() @ bone.head.copy(),
                armature_source.matrix_world.inverted() @ bone.tail.copy(),
                utils.mat3_to_vec_roll(armature_source.matrix_world.inverted().to_3x3() @ bone.matrix.to_3x3()),
            )

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_source)
        bpy.ops.object.mode_set(mode='EDIT')

        for item in self.retarget_bone_list:
            bone_source = armature_source.data.edit_bones.get(item.bone_name_source)
            bone_new = armature_source.data.edit_bones.new(item.bone_name_target + RETARGET_ID)
            bone_new.head, bone_new.tail, bone_new.roll = bone_transforms[item.bone_name_target]
            bone_new.parent = bone_source

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        for item in self.retarget_bone_list:
            bone_target = armature_target.pose.bones.get(item.bone_name_target)

            constraint = bone_target.constraints.new('COPY_ROTATION')
            constraint.name += RETARGET_ID
            constraint.target = armature_source
            constraint.subtarget = item.bone_name_target + RETARGET_ID

            if bone_target.name in root_bones:
                constraint = bone_target.constraints.new('COPY_LOCATION')
                constraint.name += RETARGET_ID
                constraint.target = armature_source
                constraint.subtarget = item.bone_name_source

        self.select_target_pose_bones(armature_target)
        if not self.bake_animation(armature_source, armature_target, root_bones):
            self.report({'ERROR'}, 'Retargeting failed: no keyframes were baked.')
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_source)
        helper_action = action_compat.get_action(armature_source)
        if helper_action and helper_action != source_action_original and helper_action.users <= 1:
            bpy.data.actions.remove(helper_action)
        bpy.ops.object.delete()

        armature_source = armature_source_original
        if source_action_original:
            armature_target.animation_data.action.name = source_action_original.name + ' Retarget'

        for bone in armature_target.pose.bones:
            for constraint in list(bone.constraints):
                if RETARGET_ID in constraint.name:
                    bone.constraints.remove(constraint)

        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_target)

        armature_target.rotation_quaternion = rotation
        armature_target.location = location

        armature_target.rotation_quaternion.w = -armature_target.rotation_quaternion.w
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        armature_target.rotation_quaternion = rotation
        armature_target.rotation_mode = rotation_mode

        if source_scale:
            armature_source.scale = source_scale

        bpy.ops.object.select_all(action='DESELECT')
        self.report({'INFO'}, 'Retargeted animation.')
        return {'FINISHED'}

    def find_duplicate_targets(self):
        seen = {}
        for item in self.retarget_bone_list:
            seen[item.bone_name_target] = seen.get(item.bone_name_target, 0) + 1
        return [key for key, value in seen.items() if value > 1]

    def find_root_bones(self, armature_target):
        root_bones = [bone for bone in armature_target.pose.bones if not bone.parent]
        root_bones_animated = []
        target_bones = [item.bone_name_target for item in self.retarget_bone_list]

        while root_bones:
            for bone in copy.copy(root_bones):
                root_bones.remove(bone)
                if bone.name in target_bones:
                    root_bones_animated.append(bone.name)
                else:
                    root_bones.extend(bone.children)
        return root_bones_animated

    def select_target_pose_bones(self, armature_target):
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_target)
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')

        for item in self.retarget_bone_list:
            bone = armature_target.pose.bones.get(item.bone_name_target)
            if bone:
                if hasattr(bone, "select"):
                    bone.select = True
                else:
                    bone.bone.select = True

        bpy.ops.object.mode_set(mode='OBJECT')

    def clean_animation(self, armature_source):
        deletable_fcurves = {'location', 'rotation_euler', 'rotation_quaternion', 'scale'}
        action = action_compat.get_action(armature_source)

        for fcurve in list(action_compat.iter_fcurves(armature_source, action)):
            if fcurve.data_path in deletable_fcurves:
                action_compat.remove_fcurve(armature_source, action, fcurve)

    def get_and_reset_pose_rotations(self, armature):
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature)
        bpy.ops.object.mode_set(mode='POSE')

        pose_rotations = {}
        for bone in armature.pose.bones:
            if bone.rotation_mode == 'QUATERNION':
                pose_rotations[bone.name] = copy.deepcopy(bone.rotation_quaternion)
                bone.rotation_quaternion = (1, 0, 0, 0)
            else:
                pose_rotations[bone.name] = copy.deepcopy(bone.rotation_euler)
                bone.rotation_euler = (0, 0, 0)

        bpy.ops.object.mode_set(mode='OBJECT')
        return pose_rotations

    def scale_armature(self, armature_source, armature_target, root_bones):
        source_min = None
        source_min_root = None
        target_min = None
        target_min_root = None

        for item in self.retarget_bone_list:
            bone_source = armature_source.pose.bones.get(item.bone_name_source)
            bone_target = armature_target.pose.bones.get(item.bone_name_target)

            bone_source_z = (armature_source.matrix_world @ bone_source.head)[2]
            bone_target_z = (armature_target.matrix_world @ bone_target.head)[2]

            if item.bone_name_target in root_bones:
                if source_min_root is None or source_min_root > bone_source_z:
                    source_min_root = bone_source_z
                if target_min_root is None or target_min_root > bone_target_z:
                    target_min_root = bone_target_z

            if source_min is None or source_min > bone_source_z:
                source_min = bone_source_z
            if target_min is None or target_min > bone_target_z:
                target_min = bone_target_z

        source_height = source_min_root - source_min
        target_height = target_min_root - target_min

        if not source_height or not target_height:
            print('No scaling needed')
            return

        scale_factor = target_height / source_height
        armature_source.scale *= scale_factor

    def read_anim_start_end(self, armature):
        frame_start = None
        frame_end = None
        action = action_compat.get_action(armature)

        for fcurve in action_compat.iter_fcurves(armature, action):
            for key in fcurve.keyframe_points:
                keyframe = key.co.x
                if frame_start is None or keyframe < frame_start:
                    frame_start = keyframe
                if frame_end is None or keyframe > frame_end:
                    frame_end = keyframe

        return frame_start, frame_end

    def copy_rest_pose(self, context, armature_source):
        context.scene.tool_settings.use_keyframe_insert_auto = False

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_source)
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.duplicate_move(
            OBJECT_OT_duplicate={"linked": False, "mode": 'TRANSLATION'},
            TRANSFORM_OT_translate={
                "value": (0, 0, 0),
                "constraint_axis": (False, True, False),
                "mirror": False,
                "snap": False,
                "remove_on_cancel": False,
                "release_confirm": False,
            },
        )

        source_armature_copy = context.object
        source_armature_copy.name = armature_source.name + "_copy"

        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(source_armature_copy)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='POSE')

        anim_data = source_armature_copy.animation_data
        action_tmp = anim_data.action if anim_data else None
        action_slot_tmp = getattr(anim_data, "action_slot", None) if anim_data else None
        if anim_data:
            anim_data.action = None
        bpy.ops.pose.armature_apply()
        if anim_data and action_tmp:
            anim_data.action = action_tmp
            if action_slot_tmp and hasattr(anim_data, "action_slot"):
                anim_data.action_slot = action_slot_tmp

        for bone in source_armature_copy.pose.bones:
            constraint = bone.constraints.new('COPY_TRANSFORMS')
            constraint.name = bone.name
            constraint.target = armature_source
            constraint.subtarget = bone.name

        bpy.ops.object.mode_set(mode='OBJECT')
        return source_armature_copy

    def bake_animation(self, armature_source, armature_target, root_bones):
        frame_split = 25
        frame_start, frame_end = self.read_anim_start_end(armature_source)
        if frame_start is None or frame_end is None:
            return False

        frame_start, frame_end = int(frame_start), int(frame_end)
        utils.set_active(armature_target)

        actions_all = []
        current_step = 0
        steps = int((frame_end - frame_start) / frame_split) + 1
        wm = bpy.context.window_manager
        wm.progress_begin(current_step, steps)
        start_time = time.time()

        bpy.ops.object.mode_set(mode='POSE')
        for frame in range(frame_start, frame_end + 2, frame_split):
            start = frame
            end = min(frame + frame_split - 1, frame_end)
            if start > end:
                continue

            bpy.ops.nla.bake(
                frame_start=start,
                frame_end=end,
                visual_keying=True,
                only_selected=True,
                use_current_action=False,
                bake_types={'POSE'},
            )

            action = armature_target.animation_data.action
            action.name = 'RSL_RETARGETING_' + str(frame)
            action_compat.assign_action(armature_target, action)
            actions_all.append(action)

            current_step += 1
            if steps != current_step:
                wm.progress_update(current_step)
        bpy.ops.object.mode_set(mode='OBJECT')

        if not actions_all:
            wm.progress_end()
            return False

        key_counts = {}
        for action in actions_all:
            for fcurve in action_compat.iter_fcurves(armature_target, action):
                key = fcurve.data_path + str(fcurve.array_index)
                key_counts[key] = key_counts.get(key, 0) + len(fcurve.keyframe_points)

        action_final = bpy.data.actions.new(name='RSL_RETARGETING_FINAL')
        action_final.use_fake_user = True
        action_compat.assign_action(armature_target, action_final)

        first_action_fcurves = list(action_compat.iter_fcurves(armature_target, actions_all[0]))
        for fcurve in first_action_fcurves:
            if fcurve.data_path.endswith('scale'):
                continue
            if fcurve.data_path.endswith('location'):
                bone_name = fcurve.data_path.split('"')
                if len(bone_name) != 3 or bone_name[1] not in root_bones:
                    continue

            group_name = fcurve.group.name if fcurve.group else None
            curve_final = action_compat.new_fcurve(
                armature_target,
                action_final,
                fcurve.data_path,
                index=fcurve.array_index,
                group_name=group_name,
            )
            keyframe_points = curve_final.keyframe_points
            key = fcurve.data_path + str(fcurve.array_index)
            keyframe_points.add(key_counts[key])

            index = 0
            for action in actions_all:
                fcurve_to_add = action_compat.find_fcurve(
                    armature_target,
                    action,
                    fcurve.data_path,
                    index=fcurve.array_index,
                )
                if not fcurve_to_add:
                    continue

                for kp in fcurve_to_add.keyframe_points:
                    keyframe_points[index].co.x = kp.co.x
                    keyframe_points[index].co.y = kp.co.y
                    keyframe_points[index].interpolation = 'LINEAR'
                    index += 1

        for fcurve in action_compat.iter_fcurves(armature_target, action_final):
            if len(fcurve.keyframe_points) <= 2:
                continue

            kp_pre_pre = fcurve.keyframe_points[0]
            kp_pre = fcurve.keyframe_points[1]
            kp_to_delete = []

            for kp in fcurve.keyframe_points[2:]:
                if round(kp_pre_pre.co.y, 5) == round(kp_pre.co.y, 5) == round(kp.co.y, 5):
                    kp_to_delete.append(kp_pre)
                kp_pre_pre = kp_pre
                kp_pre = kp

            for kp in reversed(kp_to_delete):
                fcurve.keyframe_points.remove(kp)

        for action in actions_all:
            bpy.data.actions.remove(action)

        action_compat.assign_action(armature_target, action_final)
        print('Retargeting Time:', round(time.time() - start_time, 2), 'seconds')
        wm.progress_end()
        return True
