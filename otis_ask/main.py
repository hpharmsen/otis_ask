import sys

import rich

try:
    from pdf_reader import read_file
except ImportError:
    from .pdf_reader import read_file


from gpteasy import GPT, set_prompt_file, get_prompt
from justdays import Day

RED = '#ff0000'
GREEN = '#00ff00'
BLUE = '#99bbff'
GRAY = '#aaaaaa'

CHECKS = {
    '1': 'Naam werkgever',
    '2': 'Adres werkgever',
    '3': 'Naam werknemer',
    '4': 'Adres van de werknemer',
    '5': 'Werkgever heeft voorgesteld arbeidsovereenkomst te beëindigen',
    '6': 'Reden beëindiging',
    '7': 'Geen dringende reden voor ontslag',
    '8': 'Beëindiging met wederzijds goedvinden',
    '9': 'Datum einde arbeidsovereenkomst',
    '10': 'Datum eindafrekening',
    '11': 'Plaats van ondertekening',
    '12': 'Datum van ondertekening',
    '13': 'Twee weken bedenktijd',
    '14': 'Opzegtermijn'
}


def color_print(text, color, end='\n'):
    rich.get_console().print(text, style=color, end=end)


def get_params():
    if len(sys.argv) != 2:
        color_print("Usage: python main.py <pdf_file>", "RED")
        sys.exit(1)
    return sys.argv[1]


def process_response(response):
    lines = response.split('\n')
    res = [{}] * (len(CHECKS))
    for line in lines:
        try:
            number, value = line.split(' ', 1)
        except ValueError:
            number, value = line, ''
        if number in CHECKS:
            if value and value.lower() != 'nee':
                passed = True
            else:
                passed = False
            res[int(number) - 1] = {'passed': passed, 'value': value}
    opzegdatum = res[12 - 1]['value']
    einddatum = res[9 - 1]['value']
    if opzegdatum and einddatum:
        termijn = Day(einddatum) - Day(opzegdatum)
        if termijn > 30:  # !! Deze moet afhankdelijk worden van het arbeidscontract
            res[14 - 1] = {'passed': True, 'value': f'{termijn} dagen'}
        else:
            res[14 - 1] = {'passed': False, 'value': f'{termijn} dagen'}
    else:
        res[14 - 1] = {'passed': False, 'value': ''}
    return res


def print_response(data):
    for i, rec in enumerate(data):
        passed = rec['passed']
        value = rec['value']
        if not value:
            value = '-'
        if passed:
            print("✅", end=" ")
        else:
            print("❌", end=" ")
        color_print(f"{CHECKS[str(i + 1)]}", GRAY, end="")
        if value and value.lower() not in ('ja', 'nee'):
            color_print(": ", GRAY, end="")
            color_print(value, BLUE)
        else:
            print()


def analyze_vso(vso_text: str):
    gpt = GPT()
    gpt.model = "gpt-4-1106-preview"
    gpt.temperature = 0

    set_prompt_file("otis_ask/prompts.toml")
    prompt = get_prompt('DATA', text=text)
    response = gpt.chat(prompt)
    data = process_response(response)
    return data


if __name__ == "__main__":
    input_file = get_params()
    text = read_file(input_file)
    data = analyze_vso(text)
    print_response(data)
