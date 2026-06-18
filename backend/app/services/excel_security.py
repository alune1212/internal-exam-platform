FORMULA_PREFIXES = ("=", "+", "-", "@")


def escape_excel_cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value
