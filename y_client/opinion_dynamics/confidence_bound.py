def bounded_confidence(
    x,
    y,
    epsilon=0.25,
    mu=0.5,
    theta=0.0,
    cold_start="neutral",
    text=None,
    group_classes=None,
    topic=None,
    base_url=None,
    llm_config=None,
    **kwargs,
):
    if x is None:
        if cold_start == "neutral":
            x = 0.5
        elif cold_start in ("author", "inherited"):
            x = y

    if x is None:
        return y

    x = float(x)
    y = float(y)
    epsilon = float(epsilon)
    mu = float(mu)
    theta = float(theta)

    if abs(y - x) > epsilon:
        if theta != 0.0:
            if x > y:
                x = min(x + theta, 1.0)
            else:
                x = max(x - theta, 0.0)
        return x

    return x + mu * (y - x)
