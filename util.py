
def fliprange(a: int, b: int) -> range:
    """Wrapper for range-builtin that does not care about signs"""
    return range(min(a, b), max(a, b) + 1)
