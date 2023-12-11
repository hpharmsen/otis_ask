from pathlib import Path
import pickle

from gpteasy import get_prompt, GPT, set_prompt_file
from justdays import Day

from otis_ask.checks import Check, Checks
from otis_ask.prompting import create_prompt

from functools import wraps

def cached(func):
    #func.cache = {}
    try:
        with open('gpt_cache.pickle', 'rb') as f:
            func.cache = pickle.load(f)
    except FileNotFoundError:
        func.cache = {}
    @wraps(func)
    def wrapper(*args):
        try:
            return func.cache[args]
        except KeyError:
            func.cache[args] = result = func(*args)
            with open('gpt_cache.pickle', 'wb') as f:
                pickle.dump(func.cache, f)
            return result
    return wrapper


@cached
def doprompt(prompt:str) -> str:
    gpt = GPT()
    gpt.model = "gpt-4-1106-preview"
    gpt.temperature = 0
    return gpt.chat(prompt)


def analyze_vso(text:str, ao_checks):
    """VSO has been uploaded AO might or might not be present.
    Create new (empty) vso_checks and analyze together with ao_checks"""
    vso_checks = Checks('vso_checks.toml')
    return analyze_document("vso", text, vso_checks, ao_checks)


def analyze_ao(text:str, vso_checks):
    """AO has been uploaded VSO might or might not be present.
    Create new (empty) ao_checks and analyze together with vso_checks"""
    ao_checks = Checks('ao_checks.toml')
    return analyze_document("ao", text, vso_checks, ao_checks)


def check_document_type(document_text: str):
    gpt = GPT()
    gpt.model = "gpt-4-1106-preview"
    gpt.temperature = 0

    set_prompt_file(Path(__file__).absolute().parent / "prompts.toml")
    prompt = get_prompt('CHECK_DOCUMENT_TYPE', document_text=document_text)
    #response = gpt.chat(prompt)
    response = doprompt(prompt)
    return response.strip().lower()


def analyze_document(document_type:str, document_text: str, vso_checks: Checks, ao_checks: Checks):
    # gpt = GPT()
    # gpt.model = "gpt-4-1106-preview"
    # gpt.temperature = 0

    set_prompt_file(Path(__file__).absolute().parent / "prompts.toml")
    if document_type == 'vso':
        checks = vso_checks
    elif document_type == 'ao':
        checks = ao_checks
    else:
        raise ValueError(f"Unknown document type: {document_type}")
    prompt = create_prompt(document_text=document_text, checks=checks)
    #print(prompt)
    #response = gpt.chat(prompt)
    response = doprompt(prompt)
    #print(response)
    process_response(response, checks) # Fill in value and passed fields in checks

    #!!advice = generate_advice(vso_checks)
    return checks#!!, advice


def process_response(response, checks):
    #print('########\n', response.strip(), '\n########')
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

        # Determine if check is passed
        check.value = value
        check.passed = False
        if value and value.lower() != 'nee':
            if check.check_type == str:
                check.passed = True
            elif check.check_type == Day:
                try:  # Day type only passes when it can be converted to a valid Day
                    check.value = Day(value)
                    check.passed = True
                except ValueError:
                    pass
            else:
                raise ValueError(f"Unknown check type: {check.check_type}")

    return checks


def check_vso_with_ao(vso_checks: Checks, ao_checks: Checks) -> tuple[Checks, str]:

    extra_checks = Checks()
    extra_advice = ''

    ########## Check op de opzegtermijn ##########

    # Opzegdatum is de laatste dag van de maand van ondertekening + 1
    # Opzegtermijn is:
    # 4 maanden als de werknemer 15 jaar of langer in dienst is,
    # 3 maanden als de werknemer 10 jaar of langer in dienst is,
    # 2 maanden als de werknemer 5 jaar of langer in dienst is,
    # 1 maand als de werknemer korter dan 5 jaar in dienst is.
    # Einddatum moet dus minimaal zoveel maanden veder liggen dan de opzegdatum

    datum_ondertekening = vso_checks.get('DATUM_ONDERTEKENING').value
    einddatum = vso_checks.get('EINDDATUM').value
    startdatum = ao_checks.get('STARTDATUM').value

    opzegtermijn_str = ''
    if type(datum_ondertekening) == type(einddatum) == type(startdatum) == Day:
        opzegdatum = datum_ondertekening.last_day_of_month() + 1
        years = (einddatum - startdatum) / 365.25
        opzegtermijn = 4 if years > 15 else 3 if years > 10 else 2 if years > 5 else 1
        opzegtermijn_str = f'minimaal {opzegtermijn} maanden'
        passed = einddatum >= opzegdatum.plus_months(opzegtermijn)
        if not passed:
            extra_advice += get_prompt('TERMINATION_TERM_DETAILS', opzegtermijn=opzegtermijn)
    else:
        passed = False
        extra_advice += get_prompt('DATES_MISSING')

    extra_checks.add(Check('OPZEGTERMIJN', 'Opzegtermijn', '', Day, [], True, passed, opzegtermijn_str))

    ########## Check op relatiebeding ##########

    passed = True
    if ao_checks.get('RELATIEBEDING').value == 'ja':
        if vso_checks.get('RELATIEBEDING').value != 'nee':
            passed = False
            text = 'Niet vervallen'
            extra_advice += get_prompt('RELATIEBEDING_NIET_VERVALLEN')
        else:
            text = 'Vervallen'
    else:
        text = 'Geen'
    extra_checks.add(Check('RELATEBEDING', 'Relatiebeding', '', str, [], True, passed, text))

    ########## Check op concurrentiebeding ##########

    passed = True
    if ao_checks.get('CONCURRENTIEBEDING').value == 'ja':
        if vso_checks.get('CONCURRENTIEBEDING').value != 'nee':
            passed = False
            text = 'Niet vervallen'
            extra_advice += get_prompt('CONCURRENTIEBEDING_NIET_VERVALLEN')
        else:
            text = 'Vervallen'
    else:
        text = 'Geen'
    extra_checks.add(Check('CONCURRENTIEBEDING', 'Concurrentiebeding', '', str, [], True, passed, text))

    ########## Check op pensioenregeling ##########

    passed = True
    if ao_checks.get('PENSIOENREGELING').value == 'ja':
        if vso_checks.get('PENSIOENREGELING').value != 'ja':
            passed = False
            extra_advice += get_prompt('PENSIOENREGELING')
            text = 'Niet voortgezet'
            extra_advice += get_prompt('PENSIOEN_VOORTZETTEN')
        else:
            text = 'Voortgezet'
    else:
        text = 'Geen'
    extra_checks.add(Check('PENSIOENREGELING', 'Voortzetten van pensioenregeling', '', str, [], True, passed, text))

    return extra_checks, extra_advice


def generate_advice(checks: Checks) -> str:
    print('GENERATE ADVICE\n---------------')
    if not checks:
        print("NO")
        return ''  # Happens when only an AO is uploaded
    print('YES', len(checks))
    # Check for missing data
    res = ''
    missing_data_sentence = ''
    missing_clauses_sentence = ''
    for check in checks:
        print(check.id, check.passed, check.value)
        if not check.passed:
            print(f'Check {check.id} failed with options {check.options} and value {check.value}')
            if check.options == ['ja', 'nee']:
                missing_clauses_sentence += f'<li>{check.description}</li>'
            else:
                missing_data_sentence += f'<li>{check.description}</li>'
    if missing_data_sentence:
        print('missing data')
        res += get_prompt('MISSING_DATA', missing_data_sentence=missing_data_sentence)
    if missing_clauses_sentence:
        print('missing clauses')
        res += get_prompt('MISSING_CLAUSES', missing_clauses_sentence=missing_clauses_sentence)

    # opzegtermijn_check = checks.get('OPZEGTERMIJN')
    # opzegdatum_check = checks.get('DATUM_ONDERTEKENING')
    # einddatum_check = checks.get('EINDDATUM')
    # if not opzegtermijn_check.passed:
    #     if not opzegdatum_check.passed or not einddatum_check.passed:
    #         res += get_prompt('DATES_MISSING')
    #     res += get_prompt('TERMINATION_TERM_DETAILS')

    if not res:
        res = get_prompt('NO_ADVICE')
    return res
