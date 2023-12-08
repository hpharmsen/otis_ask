import sys
from pathlib import Path

import rich

from otis_ask.checks import Check, Checks

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


def color_print(text, color, end='\n'):
    rich.get_console().print(text, style=color, end=end)


def get_params():
    if len(sys.argv) != 2:
        color_print("Usage: python main.py <pdf_file>", "RED")
        sys.exit(1)
    return sys.argv[1]


def process_response(response, checks):
    print('########\n', response.strip(), '\n########')
    lines = response.strip().split('\n')
    for line in lines:
        if not line.strip():
            continue
        try:
            number, value = line.split(' ', 1)
        except ValueError:
            number, value = line, ''
        try:
            i = int(number)
            check = checks[i-1]
        except ValueError:
            print('Error: ', line)
            continue
        except IndexError:
            continue

        if value and value.lower() != 'nee':
            check.passed = True
        else:
            check.passed = False
        check.value = value

    opzegdatum = parse_date(checks, 'DATUM_ONDERTEKENING')
    einddatum = parse_date(checks, 'EINDDATUM')
    parse_date(checks, 'EINDAFREKENING')

    if opzegdatum:
        opzegtermijn = opzegdatum.last_day_of_month() + 1
        opzeg_str = '-> ' + str(opzegtermijn)
    else:
        opzeg_str = ''

    # Voeg extra check toe: opzegtermijn
    termijn = ''
    passed = False
    if opzegdatum and einddatum:
        try:
            termijn = f'{einddatum - opzegdatum} dagen'
            passed = True
        except ValueError:
            pass  # Geen correct datum
    checks.add(Check('OPZEGTERMIJN', 'Opzegtermijn', '', Day, [], passed, termijn + opzeg_str))
    return checks


def parse_date(checks: Checks, id):
    """ Checks the indexed number in res and converts it to a date if possible. If not sets the passed flag to False """
    for check in checks:
        if check.id == id:
            try:
                check.value = Day(check.value)
            except ValueError:
                check.value = None
                check.passed = False
            return check.value


def print_response(checks: Checks):
    for check in checks:
        value = check.value
        if value:
            value = '-'
        if check.passed:
            print("✅", end=" ")
        else:
            print("❌", end=" ")
        color_print(f"{check.description}", GRAY, end="")
        if value and value.lower() not in ('ja', 'nee'):
            color_print(": ", GRAY, end="")
            color_print(value, BLUE)
        else:
            print()


def generate_advice(checks: Checks):
    # Check for missing data
    res = ''
    missing_data_sentence = ''
    missing_clauses_sentence = ''
    for check in checks:
        if not check.passed:
            if check.options == ['ja', 'nee']:
                missing_clauses_sentence += '<li>' + check.description + '</li>'
            else:
                missing_data_sentence += f'<li>{check.description}</li>'
    if missing_data_sentence:
        res += get_prompt('MISSING_DATA', missing_data_sentence=missing_data_sentence)
    if missing_clauses_sentence:
        res += get_prompt('MISSING_CLAUSES', missing_clauses_sentence=missing_clauses_sentence)

    opzegtermijn_check = checks.get('OPZEGTERMIJN')
    opzegdatum_check = checks.get('DATUM_ONDERTEKENING')
    einddatum_check = checks.get('EINDDATUM')
    if not opzegtermijn_check.passed:
        if not opzegdatum_check.passed or not einddatum_check.passed:
            res += get_prompt('DATES_MISSING')
        res += get_prompt('TERMINATION_TERM_DETAILS')

    if not res:
        res = get_prompt('NO_ADVICE')
    return res


def create_prompt(vso_text: str, checks: Checks):
    # Create checks text from Checks
    date_checks = []
    checks_string = ''
    for i, check in enumerate(checks):
        checks_string += f'{i+1} {check.prompt}'
        if check.options:
            checks_string += ' (' + str_combine(check.options, 'of') + ')'
        if check.check_type == Day:
            date_checks += [str(i+1)]
        checks_string += '\n'
    if date_checks:
        checks_string += get_prompt('EXTRACT_DATE_FORMAT', fields=str_combine(date_checks, "en"))

    # Create answer format
    answer_format = ''
    for i, check in enumerate(checks[:6]):
        how = check.options[0] if check.options else check.description
        answer_format += f'{i+1} {how}\n'

    prompt = get_prompt('ANALYZE_DOC_PROMPT', vso_text=vso_text, checks_string=checks_string,
                        answer_format=answer_format)
    return prompt


def str_combine(items: list, sep: str):
    """ ["yes", "no", "maybe"] -> "yes, no or maybe" """
    if not items:
        return ''
    if len(items) == 1:
        return str(items[0])
    return ",".join([str(item) for item in items[:-1]]) + " " + sep + " " + str(items[-1])


def analyze_vso(vso_text: str):
    gpt = GPT()
    gpt.model = "gpt-4-1106-preview"
    gpt.temperature = 0

    set_prompt_file(Path(__file__).absolute().parent / "prompts.toml")
    checks = Checks()
    prompt = create_prompt(vso_text=vso_text, checks=checks)
    print(prompt)
    response = gpt.chat(prompt)
    process_response(response, checks)
    advice = generate_advice(checks)
    return checks, advice


if __name__ == "__main__":
    input_file = get_params()
    text = read_file(input_file)
    checks, advice = analyze_vso(text)
    print_response(checks)
    print(advice)
