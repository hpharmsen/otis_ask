import rich

from otis_ask.checks import Checks

RED = '#ff0000'
GREEN = '#00ff00'
BLUE = '#99bbff'
GRAY = '#aaaaaa'


def color_print(text, color, end='\n'):
    rich.get_console().print(text, style=color, end=end)


def print_response(checks: Checks):
    if not checks:
        return
    for check in checks:
        value = check.value
        if not value:
            value = '-'

        if not check.required:
            print("➡️", end=" ")
        elif check.passed:
            print("✅", end=" ")
        else:
            print("❌", end=" ")
        color_print(f"{check.description}", GRAY, end="")
        if value:
            color_print(": ", GRAY, end="")
            color_print(value, BLUE)
        else:
            print()
