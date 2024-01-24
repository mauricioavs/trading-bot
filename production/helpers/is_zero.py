def is_zero(number: float) -> bool:
    if abs(number) < 1e-10:
        return True
    return False
