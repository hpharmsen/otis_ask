import sys

import rich

from pdf_reader import read_file
from gpteasy import GPT, set_prompt_file, get_prompt

RED = '#ff0000'
GREEN = '#00ff00'

CHECKS = {
    '1': 'Naam werkgever',
    '2': 'Adres werkgever',
    '3': 'Naam werknemer',
    '4': 'Adres van de werknemer',
    '5': 'Werkgever heeft voorgesteld arbeidsovereenkomst te beëindigen',
    '6': 'Reden beëindiging',
    '7': 'Geen dringende reden voor ontslag',
    '8': 'Beëindiging met wederzijds goedvinden',
    '9': 'De datum einde arbeidsovereenkomst',
    '10': 'Datum eindafrekening',
    '11': 'Plaats van ondertekening',
    '12': 'Datum van ondertekening',
    '13': '2 weken bedenktijd'
}

def color_print(text, color, end='\n'):
    rich.get_console().print(text, style=color, end=end)


def get_params():
    if len(sys.argv) != 2:
        color_print("Usage: python main.py <pdf_file>", "RED")
        sys.exit(1)
    return sys.argv[1]


if __name__ == "__main__":
    set_prompt_file("prompts.toml")
    input_file = get_params()
    text = read_file(input_file)

    gpt = GPT()
    gpt.model = "gpt-4-1106-preview"

    prompt = get_prompt('DATA', text=text)
    response = gpt.chat(prompt)
    process_response(response)