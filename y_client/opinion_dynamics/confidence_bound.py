
def bounded_confidence(x: float, y: float, epsilon: float = 0.25, mu: float = 0.5, theta: float = 0.0,
                       cold_start: str = "neutral") -> float | str:
    """
    Calculate the confidence bound for a given score x and total count y.

    Parameters:
    - x (float): opinion score of the user
    - y (float): opinion score of the second user
    - epsilon (float): The confidence level parameter.
    - mu (float): The prior mean for Bayesian adjustment.
    - theta (float): The prior strength for Bayesian adjustment.
    - cold_start (str): The label to return when y is 0.
    - discrete (bool): Whether to return discrete class labels.
    - group_classes (dict): A mapping of score ranges to class labels.

    Returns:
    - float | str: The confidence bound score or class label.
    """

    if x is None:
        if cold_start == "neutral":
            x = 0.5
        if cold_start == "inherited":
            x = y

    else:
        if abs(y-x) > epsilon:
            if theta != 0:
                if x > y:
                    x = min(x+theta, 1)
                else:
                    x = max(x-theta, 0)

        else:
            x += mu * abs(x-y)

    return x

