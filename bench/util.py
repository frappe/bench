def sequencify(arg):
    if not isinstance(arg, (list, tuple)):
        arg = [arg]
    return arg

def assign_if_empty(a, b):
    if not a:
        a = b
    return a