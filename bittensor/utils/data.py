def unflatten_dict(flat_dict):
    """Convert a flat dictionary with dot-separated keys to a nested dictionary."""
    nested_dict = {}

    for key, value in flat_dict.items():
        keys = key.split(".")
        d = nested_dict
        for part in keys[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[keys[-1]] = value

    return nested_dict


def flatten_dict(nested_dict, parent_key="", sep="."):
    """Convert a nested dictionary to a flat dictionary with dot-separated keys."""
    items = []
    for k, v in nested_dict.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
