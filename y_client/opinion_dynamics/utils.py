def get_opinion_group(opinion: float, group_classes: dict) -> str:
    """
    Map a continuous opinion score to a discrete class label based on defined ranges.

    Parameters:
    - opinion (float): The opinion score to classify.
    - group_classes (dict): A mapping of score ranges to class labels.

    Returns:
    - str: The class label corresponding to the opinion score.
    """
    for class_label, (lower_bound, upper_bound) in group_classes.items():
        if lower_bound <= opinion < upper_bound:
            return class_label
    return "unknown"
