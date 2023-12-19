def green(content: str) -> str:
    """
    Green color message
    """
    return "\033[92m" + content + "\033[0m"


def red(content: str) -> str:
    """
    Red color message
    """
    return "\033[91m" + content + "\033[0m"


def cyan(content: str) -> str:
    """
    Cyan color message
    """
    return "\033[96m" + content + "\033[0m"


def yellow(content: str) -> str:
    """
    Yellow color message
    """
    return "\033[93m" + content + "\033[0m"
