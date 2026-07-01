import json
import os

import bpy

from . import detection_manager

custom_bone_list_filename = "custom_bone_list.json"


def get_custom_bones_dir():
    package_name = (__package__ or "rokoko_retargeting").split(".")[0]

    if hasattr(bpy.utils, "extension_path_user"):
        try:
            path = bpy.utils.extension_path_user(package_name, path="custom_bones", create=True)
            if path:
                return path
        except Exception:
            pass

    try:
        return bpy.utils.user_resource(
            'SCRIPTS',
            path=os.path.join("rokoko_retargeting", "custom_bones"),
            create=True,
        )
    except TypeError:
        base_path = bpy.utils.user_resource('SCRIPTS')
        return os.path.join(base_path, "rokoko_retargeting", "custom_bones")


def get_custom_bone_list_file():
    return os.path.join(get_custom_bones_dir(), custom_bone_list_filename)


def save_retargeting_to_list():
    retargeting_dict = detection_manager.detect_retarget_bones()

    for bone_item in bpy.context.scene.rsl_retargeting_bone_list:
        if not bone_item.bone_name_source or not bone_item.bone_name_target:
            continue

        bone_name_key = bone_item.bone_name_key
        bone_name_source = bone_item.bone_name_source.lower()
        bone_name_target = bone_item.bone_name_target.lower()
        bone_name_target_detected, bone_name_key_detected = retargeting_dict.get(
            bone_item.bone_name_source,
            ("", bone_name_key),
        )

        if bone_name_target_detected == bone_item.bone_name_target:
            continue

        if bone_name_key_detected and bone_name_key_detected != 'spine':
            if not detection_manager.bone_detection_list_custom.get(bone_name_key_detected):
                detection_manager.bone_detection_list_custom[bone_name_key_detected] = []

            if bone_name_target_detected.lower() in detection_manager.bone_detection_list_custom[bone_name_key_detected]:
                if bone_name_key_detected.startswith('custom_bone_') and len(detection_manager.bone_detection_list_custom[bone_name_key_detected]) == 2:
                    detection_manager.bone_detection_list_custom.pop(bone_name_key_detected)
                else:
                    detection_manager.bone_detection_list_custom[bone_name_key_detected].remove(bone_name_target_detected.lower())

                detection_manager.bone_detection_list = detection_manager.combine_lists(
                    detection_manager.bone_detection_list_unmodified,
                    detection_manager.bone_detection_list_custom,
                )

                retargeting_dict = detection_manager.detect_retarget_bones()
                bone_name_detected_new, _ = retargeting_dict.get(bone_item.bone_name_source, ("", ""))
                if bone_name_detected_new.lower() == bone_name_target:
                    continue

            if bone_name_target not in detection_manager.bone_detection_list_custom[bone_name_key_detected]:
                detection_manager.bone_detection_list_custom[bone_name_key_detected] = [bone_name_target] + detection_manager.bone_detection_list_custom[bone_name_key_detected]
            continue

        detection_manager.bone_detection_list_custom['custom_bone_' + bone_name_source] = [bone_name_source, bone_name_target]

    save_to_file_and_update()


def save_to_file_and_update():
    save_custom_to_file()
    detection_manager.load_detection_lists()


def save_custom_to_file(file_path=None):
    if not file_path:
        file_path = get_custom_bone_list_file()

    new_custom_list = clean_custom_list()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w', encoding="utf8") as outfile:
        json.dump(new_custom_list, outfile, ensure_ascii=False, indent=4)


def load_custom_bone_list_from_file(file_path=None):
    if not file_path:
        file_path = get_custom_bone_list_file()

    try:
        with open(file_path, encoding="utf8") as file:
            custom_bone_list = json.load(file)
    except FileNotFoundError:
        return {}
    except json.decoder.JSONDecodeError:
        print("Custom bone list is not a valid json file!")
        return {}

    if custom_bone_list.get('rokoko_custom_names') is None or custom_bone_list.get('version') is None or custom_bone_list.get('bones') is None:
        print("Custom name list file is not a valid name list file")
        return {}

    return custom_bone_list.get('bones') or {}


def clean_custom_list():
    new_custom_list = {
        'rokoko_custom_names': True,
        'version': 1,
        'bones': {},
        'shapes': {},
    }

    for key, values in detection_manager.bone_detection_list_custom.items():
        if not values:
            continue
        new_custom_list['bones'][key] = [value.lower() for value in values]

    return new_custom_list


def import_custom_list(directory, file_name):
    file_path = os.path.join(directory, file_name)
    new_custom_bone_list = load_custom_bone_list_from_file(file_path=file_path)

    for key, bones in detection_manager.bone_detection_list_custom.items():
        if not new_custom_bone_list.get(key):
            new_custom_bone_list[key] = []

        for bone in new_custom_bone_list[key]:
            if bone in bones:
                bones.remove(bone)

        new_custom_bone_list[key] += bones

    detection_manager.bone_detection_list_custom = new_custom_bone_list


def export_custom_list(file_path):
    if not detection_manager.bone_detection_list_custom:
        return None

    save_custom_to_file(file_path=file_path)
    return os.path.basename(file_path)


def delete_custom_bone_list():
    detection_manager.bone_detection_list_custom = {}
    save_to_file_and_update()
