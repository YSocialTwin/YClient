def get_opinion_group(opinion: float, group_classes: dict) -> str:
    """
    Map a continuous opinion score to a discrete class label based on defined ranges.

    Parameters:
    - opinion (float): The opinion score to classify.
    - group_classes (dict): A mapping of score ranges to class labels.

    Returns:
    - str: The class label corresponding to the opinion score.
    """
    if not isinstance(group_classes, dict):
        return "unknown"
    for class_label, bounds in group_classes.items():
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            continue
        lower_bound, upper_bound = bounds
        if lower_bound <= opinion < upper_bound:
            return class_label
    return "unknown"
