def _id_type(id_data):
    return getattr(id_data, "id_type", id_data.__class__.__name__.upper())


def _legacy_fcurves(action):
    """Return the pre-Blender-5 F-Curve collection, if available.

    Blender 4.5 stores F-Curves directly on the Action. Blender 5.0 moved
    them into slot-specific channel bags, so all callers go through this
    module instead of branching on Blender's version number.
    """
    return getattr(action, "fcurves", None)


def _slot_for_action(id_data, action, create=False):
    anim_data = id_data.animation_data_create() if create else id_data.animation_data
    if not anim_data:
        return None

    if anim_data.action == action:
        slot = getattr(anim_data, "action_slot", None)
        if slot:
            return slot
        suitable_slots = getattr(anim_data, "action_suitable_slots", None)
        if suitable_slots and len(suitable_slots):
            return suitable_slots[0]

    slots = getattr(action, "slots", None)
    if slots is None:
        return None

    target_id_type = _id_type(id_data)
    for slot in slots:
        if getattr(slot, "target_id_type", None) == target_id_type:
            return slot

    if create:
        return slots.new(target_id_type, id_data.name)

    return slots[0] if len(slots) else None


def _keyframe_strip(action, create=False):
    layers = getattr(action, "layers", None)
    if layers is None:
        return None

    if len(layers):
        layer = layers[0]
    elif create:
        layer = layers.new(name="Layer")
    else:
        return None

    strips = layer.strips
    if len(strips):
        return strips[0]
    if create:
        return strips.new(type='KEYFRAME')
    return None


def assign_action(id_data, action):
    anim_data = id_data.animation_data_create()
    anim_data.action = action

    if hasattr(anim_data, "action_slot"):
        slot = _slot_for_action(id_data, action, create=True)
        if slot:
            anim_data.action_slot = slot

    return action


def get_action(id_data):
    anim_data = id_data.animation_data
    return anim_data.action if anim_data else None


def get_channelbag(id_data, action=None, create=False):
    action = action or get_action(id_data)
    if not action:
        return None

    slot = _slot_for_action(id_data, action, create=create)
    if not slot:
        return None

    strip = _keyframe_strip(action, create=create)
    if not strip or not hasattr(strip, "channelbag"):
        return None

    return strip.channelbag(slot, ensure=create)


def iter_fcurves(id_data, action=None):
    legacy_fcurves = _legacy_fcurves(action or get_action(id_data))
    if legacy_fcurves is not None:
        return iter(legacy_fcurves)

    channelbag = get_channelbag(id_data, action)
    if not channelbag:
        return iter(())
    return iter(channelbag.fcurves)


def new_fcurve(id_data, action, data_path, index=0, group_name=None):
    legacy_fcurves = _legacy_fcurves(action)
    if legacy_fcurves is not None:
        kwargs = {"index": index}
        if group_name:
            kwargs["action_group"] = group_name
        return legacy_fcurves.new(data_path, **kwargs)

    channelbag = get_channelbag(id_data, action, create=True)
    kwargs = {}
    if group_name:
        kwargs["group_name"] = group_name
    return channelbag.fcurves.new(data_path, index=index, **kwargs)


def find_fcurve(id_data, action, data_path, index=0):
    legacy_fcurves = _legacy_fcurves(action)
    if legacy_fcurves is not None:
        return legacy_fcurves.find(data_path, index=index)

    channelbag = get_channelbag(id_data, action)
    if not channelbag:
        return None
    return channelbag.fcurves.find(data_path, index=index)


def remove_fcurve(id_data, action, fcurve):
    legacy_fcurves = _legacy_fcurves(action)
    if legacy_fcurves is not None:
        legacy_fcurves.remove(fcurve)
        return

    channelbag = get_channelbag(id_data, action)
    if channelbag:
        channelbag.fcurves.remove(fcurve)
