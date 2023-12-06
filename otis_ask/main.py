import sys
from pathlib import Path

import rich

try:
    from pdfreader import read_file
except ImportError:
    try:
        from .pdfreader import read_file
    except ImportError:
        from otis_ask.pdfreader import read_file


from gpteasy import GPT, set_prompt_file, get_prompt
from justdays import Day

RED = '#ff0000'
GREEN = '#00ff00'
BLUE = '#99bbff'
GRAY = '#aaaaaa'

CHECKS = [
    'Naam werkgever',
    'Adres werkgever',
    'Naam werknemer',
    'Adres van de werknemer',
    'Werkgever heeft voorgesteld arbeidsovereenkomst te beëindigen',
    'Reden beëindiging',
    'Werknemer kan geen verwijt worden gemaakt',
    'Geen dringende reden voor ontslag',
    'Geen opzegverbod',
    'Beëindiging met wederzijds goedvinden',
    'Datum einde arbeidsovereenkomst',
    'Datum eindafrekening',
    'Twee weken bedenktijd',
    'Plaats van ondertekening',
    'Datum van ondertekening',
    'Opzegtermijn'
]
NAAM_WERKGEVER = 0
ADRES_WERKGEVER = 1
NAAM_WERKNEMER = 2
ADRES_WERKNEMER = 3
VOORGESTELD = 4
REDEN = 5
GEEN_VERWIJT = 6
GEEN_DRINGENDE_REDEN = 7
GEEN_OPZEGVERBOD = 8
WEDERZIJDS = 9
EINDDATUM = 10
EINDAFREKENING = 11
TWEE_WEKEN = 12
PLAATS = 13
OPZEGDATUM = 14
OPZEGTERMIJN = 15

def color_print(text, color, end='\n'):
    rich.get_console().print(text, style=color, end=end)


def get_params():
    if len(sys.argv) != 2:
        color_print("Usage: python main.py <pdf_file>", "RED")
        sys.exit(1)
    return sys.argv[1]



def process_response(response):
    print('########\n', response.strip(), '\n########')
    lines = response.strip().split('\n')
    res = [{}] * (len(CHECKS))
    for line in lines:
        if not line.strip():
            continue
        try:
            number, value = line.split(' ', 1)
        except ValueError:
            number, value = line, ''
        if value and value.lower() != 'nee':
            passed = True
        else:
            passed = False

        try:
            i = int(number)
        except ValueError:
            print('Error: ', line)
            continue

        res[int(number)] = {'number':number, 'check':CHECKS[int(number)], 'passed': passed, 'value': value}

    opzegdatum = parse_date(res, OPZEGDATUM)
    einddatum = parse_date(res, EINDDATUM)
    parse_date(res, EINDAFREKENING)

    if opzegdatum:
        opzegtermijn = opzegdatum.last_day_of_month() + 1
        opzeg_str = '-> ' + str(opzegtermijn)
    else:
        opzeg_str = ''

    termijn = ''
    passed = False
    if opzegdatum and einddatum:
        try:
            termijn = f'{einddatum - opzegdatum} dagen'
            passed = True
        except ValueError:
            pass  # Geen correct datum
    res[OPZEGTERMIJN] = {'number': str(OPZEGTERMIJN), 'check': CHECKS[OPZEGTERMIJN], 'passed': passed, 'value': termijn + opzeg_str}
    return res


def parse_date(res, index):
    """ Checks the indexed number in res and converts it to a date if possible. If not sets the passed flag to False """
    try:
        datum = Day(res[index]['value'])
    except ValueError:
        datum = ''
        res[index]['passed'] = False
    res[index]['value'] = str(datum)
    return datum


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
        color_print(f"{CHECKS[i]}", GRAY, end="")
        if value and value.lower() not in ('ja', 'nee'):
            color_print(": ", GRAY, end="")
            color_print(value, BLUE)
        else:
            print()

def generate_advice(data):
    # Check for missing data
    res = ''
    missing_data_sentence = ''
    for index in (NAAM_WERKGEVER, ADRES_WERKGEVER, NAAM_WERKNEMER, ADRES_WERKNEMER, PLAATS, OPZEGDATUM, EINDDATUM, EINDAFREKENING):
        if not data[index]['passed']:
            missing_data_sentence += '<li>' + CHECKS[index] + '</li>'
    if missing_data_sentence:
        res += f'<p>Vul de volgende gegevens aan:<ul>{missing_data_sentence}</ul></p>'

    missing_clauses_sentence = ''
    for index in (VOORGESTELD, REDEN, GEEN_VERWIJT, GEEN_DRINGENDE_REDEN, GEEN_OPZEGVERBOD, WEDERZIJDS, TWEE_WEKEN):
        if not data[index]['passed']:
            missing_clauses_sentence += '<li>' + CHECKS[index] + '</li>'
    if missing_clauses_sentence:
        res += f'<p>Let erop dat de volgende zaken in de Vaststellingsovereenkomst zijn opgenomen:<ul>{missing_clauses_sentence}</ul></p>'

    if not data[OPZEGTERMIJN]['passed']:
        if not data[OPZEGDATUM]['passed'] or not data[EINDDATUM]['passed']:
            res += f'<p>Om de opzegtermijn te kunnen checken moeten zowel opzegdatum als einddatum zijn ingevuld.</p>'
        res += f'''<p>De opzegtermijn voldoet niet aan de wettelijke eisen.<br/>De door de werkgever in acht te nemen termijn van opzegging bedraagt bij een arbeidsovereenkomst die op de dag van opzegging:
                   <ol><li>korter dan vijf jaar heeft geduurd: één maand;</li>
                   <li>vijf jaar of langer, maar korter dan tien jaar heeft geduurd: twee maanden;</li>
                   <li>tien jaar of langer, maar korter dan vijftien jaar heeft geduurd: drie maanden;</li>
                   <li>vijftien jaar of langer heeft geduurd: vier maanden.</li></ol>
                   </p>'''

    if not res:
        res = '<p>Deze vaststellingsovereenkomst lijkt helemaal in orde.</p>'
    return res

def analyze_vso(vso_text: str):
    gpt = GPT()
    gpt.model = "gpt-4-1106-preview"
    gpt.temperature = 0

    prompt_file = Path(__file__).absolute().parent / "prompts.toml"
    set_prompt_file(prompt_file)
    prompt = get_prompt('DATA', vso_text=vso_text)
    print(prompt)
    response = gpt.chat(prompt)
    data = process_response(response)
    advice = generate_advice(data)
    return data, advice


if __name__ == "__main__":
    input_file = get_params()
    text = read_file(input_file)
    data, advice = analyze_vso(text)
    print_response(data)
    print(advice)
