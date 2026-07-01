from . import action_compat
from . import retargeting
from .auto_detect_lists.bones import bone_list, ignore_rokoko_retargeting_bones

bone_detection_list = {}
bone_detection_list_unmodified = {}
bone_detection_list_custom = {}


def load_detection_lists():
    global bone_detection_list, bone_detection_list_unmodified, bone_detection_list_custom
    from . import custom_schemes_manager

    # Create the lists from the internal naming lists
    bone_detection_list_unmodified = setup_bone_list(bone_list)

    # Load the custom naming lists from the file
    bone_detection_list_custom = custom_schemes_manager.load_custom_bone_list_from_file()

    # Combine custom and internal lists
    bone_detection_list = combine_lists(bone_detection_list_unmodified, bone_detection_list_custom)

    # Print the whole bone list
    # print_bone_detection_list()


def setup_bone_list(raw_bone_list):
    new_bone_list = {}

    for bone_key, bone_values in raw_bone_list.items():
        # Add the bones to the list if no side indicator is found
        if 'left' not in bone_key:
            new_bone_list[bone_key] = [bone_value.lower() for bone_value in bone_values]
            if bone_key == 'spine':
                new_bone_list['chest'] = [bone_value.lower() for bone_value in bone_values]
            continue

        # Add bones to the list that are two sided
        bone_values_left = []
        bone_values_right = []

        for bone_name in bone_values:
            bone_name = bone_name.lower()

            if "\\l" in bone_name:
                for replacement in ['l', 'left', 'r', 'right']:
                    bone_name_new = bone_name.replace("\\l", replacement)

                    # Debug if duplicates are found
                    if bone_name_new in bone_values_left or bone_name_new in bone_values_right:
                        print('Duplicate autodetect bone entry:', bone_name, bone_name_new)
                        continue

                    if 'l' in replacement:
                        bone_values_left.append(bone_name_new)
                    else:
                        bone_values_right.append(bone_name_new)

        bone_key_left = bone_key
        bone_key_right = bone_key.replace('left', 'right')

        new_bone_list[bone_key_left] = bone_values_left
        new_bone_list[bone_key_right] = bone_values_right

    return new_bone_list


def combine_lists(internal_list, custom_list):
    """
        Creates a combined list with the second list put in first but with the structure of the first list
    """
    combined_list = {}

    # Set dictionary structure
    for key in internal_list.keys():
        combined_list[key] = []

    # Load in custom values into the dictionary
    for key, values in custom_list.items():
        combined_list[key] = []
        for value in values:
            combined_list[key].append(value.lower())

    # Load in internal values
    for key, values in internal_list.items():
        for value in values:
            combined_list[key].append(value)

    return combined_list


def print_bone_detection_list():
    print('BONES')
    for key, values in bone_detection_list.items():
        print(key, values)
        print()

    print('CUSTOM BONES')
    for key, values in bone_detection_list_custom.items():
        print(key, values)
        print('--> ', bone_detection_list[key])
        print()

    print()


# def get_bone_list():
#     return bone_detection_list
#
#
# def get_custom_bone_list():
#     return bone_detection_list_custom
#
#
def standardize_bone_name(name):
    # List of chars to replace if they are at the start of a bone name
    starts_with = [
        ('_', ''),
        ('ValveBiped_', ''),
        ('Valvebiped_', ''),
        ('Bip1_', 'Bip_'),
        ('Bip01_', 'Bip_'),
        ('Bip001_', 'Bip_'),
        ('Character1_', ''),
        ('HLP_', ''),
        ('JD_', ''),
        ('JU_', ''),
        ('Armature|', ''),
        ('Bone_', ''),
        ('C_', ''),
        ('Cf_S_', ''),
        ('Cf_J_', ''),
        ('G_', ''),
        ('Joint_', ''),
        ('DEF_', ''),
        ('CC_Base_', ''),
    ]

    # Standardize names
    # Make all the underscores!
    name = (
        name.replace(' ', '_')
        .replace('-', '_')
        .replace('.', '_')
        .replace('____', '_')
        .replace('___', '_')
        .replace('__', '_')
    )

    # Replace if name starts with specified chars
    for replacement in starts_with:
        if name.startswith(replacement[0]):
            name = replacement[1] + name[len(replacement[0]):]

    # Remove digits from the start
    name_split = name.split('_')
    if len(name_split) > 1 and name_split[0].isdigit():
        name = name_split[1]

    # Specific condition
    name_split = name.split('"')
    if len(name_split) > 3:
        name = name_split[1]

    # Another specific condition
    if ':' in name:
        for i, split in enumerate(name.split(':')):
            if i == 0:
                name = ''
            else:
                name += split

    # Remove S0 from the end
    if name[-2:] == 'S0':
        name = name[:-2]

    if name[-4:] == '_Jnt':
        name = name[:-4]

    return name.lower()


def bone_parent_names_match(source_bone, target_bone, allow_standardized=False):
    while source_bone.parent or target_bone.parent:
        source_parent = source_bone.parent
        target_parent = target_bone.parent

        if not source_parent or not target_parent:
            return False

        if allow_standardized:
            if standardize_bone_name(source_parent.name) != standardize_bone_name(target_parent.name):
                return False
        elif source_parent.name != target_parent.name:
            return False

        source_bone = source_parent
        target_bone = target_parent

    return True


def detect_source_bone_name(obj, bone_name_source, source_obj=None, allow_standardized=False):
    source_bone = source_obj.pose.bones.get(bone_name_source) if source_obj else None
    bone = obj.pose.bones.get(bone_name_source)
    if bone and (not source_bone or bone_parent_names_match(source_bone, bone)):
        return bone.name

    source_name_lower = bone_name_source.lower()
    found_bone_name = ''
    for bone in obj.pose.bones:
        if bone.name.lower() != source_name_lower:
            continue
        if source_bone and not bone_parent_names_match(source_bone, bone):
            continue
        if found_bone_name:
            return ''
        found_bone_name = bone.name

    if found_bone_name or not allow_standardized:
        return found_bone_name

    source_name_standardized = standardize_bone_name(bone_name_source)
    for bone in obj.pose.bones:
        if standardize_bone_name(bone.name) != source_name_standardized:
            continue
        if source_bone and not bone_parent_names_match(source_bone, bone, allow_standardized=True):
            continue
        if found_bone_name:
            return ''
        found_bone_name = bone.name

    return found_bone_name


def detect_bone(obj, bone_name_key, bone_name_source=None, source_obj=None):
    # Go through the target armature and search for bones that fit the main source bone
    found_bone_name = ''

    if not bone_name_source:
        bone_name_source = bone_name_key

    if bone_detection_list_custom.get(bone_name_key):
        for bone in obj.pose.bones:
            for bone_name_detected in bone_detection_list_custom[bone_name_key]:
                if bone_name_detected == bone.name.lower():
                    return bone.name

    found_bone_name = detect_source_bone_name(obj, bone_name_source, source_obj=source_obj)
    if found_bone_name:
        return found_bone_name

    for bone in obj.pose.bones:
        for bone_name_detected in bone_detection_list[bone_name_key]:
            if bone_name_detected == standardize_bone_name(bone.name):
                return bone.name

    return found_bone_name


def detect_retarget_bones() -> {str: (str, str)}:
    """
    Detects all matching bones in the target and source armatures
    :return: A dictionary with the source bone name as key and a tuple of the target bone name and their shared key name as value
    """
    bone_list_animated = []
    retargeting_dict = {}
    armature_source = retargeting.get_source_armature()
    armature_target = retargeting.get_target_armature()

    action = action_compat.get_action(armature_source)

    # Get all source bones from the animation and add them to bone_list_animated
    for fc in action_compat.iter_fcurves(armature_source, action):
        bone_name = fc.data_path.split('"')
        if len(bone_name) == 3 and bone_name[1] not in bone_list_animated:
            bone_list_animated.append(bone_name[1])

    # Check if this animation is from Rokoko Studio. Ignore certain bones in that case
    is_rokoko_animation = False
    if 'newton' in bone_list_animated and 'RightFinger1Tip' in bone_list_animated and 'HeadVertex' in bone_list_animated and 'LeftFinger2Metacarpal' in bone_list_animated:
        is_rokoko_animation = True

    spines_source = []
    spines_target = []
    found_main_bones = []

    # Then add all the bones to the retargeting dictionary
    for bone_name in bone_list_animated:
        if is_rokoko_animation and bone_name in ignore_rokoko_retargeting_bones:
            continue

        bone_item_source = bone_name
        bone_item_target = ''
        main_bone_name = ''
        standardized_bone_name_source = standardize_bone_name(bone_name)

        # Find the main bone name (bone name key) of the source bone
        for bone_main, bone_values in bone_detection_list.items():
            if bone_main == 'chest':  # Ignore chest bones, these are only used for live data
                continue
            if bone_main in found_main_bones:  # Only find main bones once, except for spines
                continue
            # If the source bone name is found in the bone detection list, add its main bone name to the list of found main bones
            if bone_name.lower() in bone_values or standardized_bone_name_source in bone_values or standardized_bone_name_source == bone_main.lower():
                main_bone_name = bone_main
                if main_bone_name != 'spine':  # Ignore the spine bones for now, so that it can add the custom spine bones first
                    found_main_bones.append(main_bone_name)
                    break

        # Add the source bone and the main bone name to the retargeting dict with an empty targeting bone name
        retargeting_dict[bone_item_source] = ("", main_bone_name)

        # If no main bone name was found, continue
        if not main_bone_name:
            bone_item_target = detect_source_bone_name(
                armature_target,
                bone_item_source,
                source_obj=armature_source,
                allow_standardized=True,
            )
            if bone_item_target:
                retargeting_dict[bone_item_source] = (
                    bone_item_target,
                    'custom_bone_' + bone_item_source.lower(),
                )
            continue

        # If it's a spine bone, add it to the list for later fixing
        if main_bone_name == 'spine':
            spines_source.append(bone_name)
            continue

        # If it's a custom spine/chest bone, add it to the spine list nonetheless
        custom_main_bone = main_bone_name.startswith('custom_bone_')
        if custom_main_bone and standardize_bone_name(main_bone_name.replace('custom_bone_', '')) in bone_detection_list['spine']:
            spines_source.append(bone_name)

        # Go through the target armature and search for bones that fit the main source bone
        bone_item_target = detect_bone(
            armature_target,
            main_bone_name,
            bone_name_source=bone_item_source,
            source_obj=armature_source,
        )

        # Add the bone to the retargeting list again
        retargeting_dict[bone_item_source] = (bone_item_target, main_bone_name)

    # Add target spines to list for later fixing
    for bone in armature_target.pose.bones:
        bone_name_standardized = standardize_bone_name(bone.name)
        if bone_name_standardized in bone_detection_list['spine']:
            spines_target.append(bone.name)

    # Fix spine auto detection
    if spines_target and spines_source:
        # print(spines_source)
        spine_dict = {}

        i = 0
        for spine in reversed(spines_source):
            i += 1
            if i == len(spines_target):
                break
            spine_dict[spine] = spines_target[-i]

        spine_dict[spines_source[0]] = spines_target[0]

        # Fill in fixed spines into unfilled matches
        for spine_source, spine_target in spine_dict.items():
            for bone_source, bone_values in retargeting_dict.items():
                bone_target, bone_key = bone_values
                if bone_source == spine_source and not bone_target:
                    retargeting_dict[bone_source] = (spine_target, bone_key)
                    break

    return retargeting_dict
