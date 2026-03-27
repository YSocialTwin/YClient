def get_opinion_group(opinion, group_classes):
    if not isinstance(group_classes, dict):
        return "unknown"
    for class_label, bounds in group_classes.items():
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            continue
        lower_bound, upper_bound = bounds
        if lower_bound <= opinion < upper_bound:
            return class_label
    return "unknown"
