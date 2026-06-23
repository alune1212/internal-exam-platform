FORMULA_PREFIXES = ("=", "+", "-", "@")
LEADING_FORMULA_PADDING = "".join(chr(value) for value in range(0x21))


def escape_excel_cell(value: object) -> object:
    if isinstance(value, str) and value.lstrip(LEADING_FORMULA_PADDING).startswith(
        FORMULA_PREFIXES
    ):
        return f"'{value}"
    return value
