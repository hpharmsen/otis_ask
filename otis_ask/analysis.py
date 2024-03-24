from pathlib import Path
import pickle

from justai import Agent, get_prompt, set_prompt_file
from justdays import Day

from otis_ask.checks import Check, Checks, ChecksDict
from otis_ask.prompting import create_prompt

from functools import wraps

MODEL = 'gpt-4-turbo-preview'


def cached(func):
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
            with open('gpt_cache.pickle', 'wb') as outf:
                pickle.dump(func.cache, outf)
            return result

    return wrapper


def doprompt(prompt: str) -> str:
    gpt = Agent(MODEL)
    gpt.temperature = 0
    return gpt.chat(prompt)


def analyze_vso(text: str, checks):
    """VSO has been uploaded AO might or might not be present.
    Create new (empty) vso_checks and analyze together with ao_checks"""
    checks['vso'] = Checks('vso_checks.toml')
    return analyze_document("vso", text, checks)


def analyze_ao(text: str, checks):
    """AO has been uploaded VSO might or might not be present.
    Create new (empty) ao_checks and analyze together with vso_checks"""
    checks['ao'] = Checks('ao_checks.toml')
    return analyze_document("ao", text, checks)


def analyze_ls(text: str, checks: ChecksDict):
    """LS has been uploaded
    Create new (empty) ls_checks and analyze"""
    checks['ls'] = Checks('ls_checks.toml')
    return analyze_document("ls", text, checks)


def check_document_type(document_text: str) -> str:
    agent = Agent(MODEL)
    agent.temperature = 0

    set_prompt_file(Path(__file__).absolute().parent / "prompts.toml")
    prompt = get_prompt('CHECK_DOCUMENT_TYPE', document_text=document_text)
    response = doprompt(prompt)
    return response.strip().lower()


def analyze_document(document_type: str, document_text: str, checks: ChecksDict):
    set_prompt_file(Path(__file__).absolute().parent / "prompts.toml")
    current_checks = checks.get(document_type, 'unknown')
    if current_checks == 'unknown':
        raise ValueError(f"Unknown document type: {document_type}")

    prompt = create_prompt(document_text=document_text, checks=current_checks)
    print(prompt)
    response = doprompt(prompt)
    process_response(response, current_checks)  # Fill in value and passed fields in checks
    return prompt, response  # For debugging purposes


def process_response(response: str, checks: Checks) -> Checks:
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
            check = checks[i - 1]
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
            elif check.check_type == int:
                try:
                    check.value = int(value)
                    check.passed = True
                except ValueError:
                    pass
            elif check.check_type == float:
                try:
                    check.value = float(value.replace(',', '.'))
                    check.passed = True
                except ValueError:
                    pass
            else:
                raise ValueError(f"Unknown check type: {check.check_type}")
    return checks


def check_vso_with_ao(checks: ChecksDict) -> str:
    vso_checks = checks['vso']
    ao_checks = checks['ao']
    extra_checks = Checks()
    extra_advice = ''

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
    if type(datum_ondertekening) is type(einddatum) is type(startdatum) is Day:
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

    # ######### Check op relatiebeding ##########

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

    # ######### Check op concurrentiebeding ##########

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

    # ######### Check op pensioenregeling ##########

    passed = True
    if ao_checks.get('PENSIOENREGELING').value == 'ja':
        if vso_checks.get('PENSIOENREGELING').value != 'ja':
            passed = False
            text = 'Niet voortgezet'
            extra_advice += get_prompt('PENSIOEN_VOORTZETTEN')
        else:
            text = 'Voortgezet'
    else:
        text = 'Geen'
    extra_checks.add(Check('PENSIOENREGELING', 'Voortzetten van pensioenregeling', '', str, [], True, passed, text))

    checks['combined'] = extra_checks
    return extra_advice


def generate_advice(checks: ChecksDict, extra_advice: str) -> str:
    if not checks.get('vso'):
        return ''  # Happens when only an AO is uploaded
    # Check for missing data
    advice = ''
    missing_data_sentence = ''
    missing_clauses_sentence = ''
    for check in checks['vso']:
        if not check.passed:
            print(f'Check {check.id} failed with options {check.options} and value {check.value}')
            if check.options == ['ja', 'nee']:
                missing_clauses_sentence += f'<li>{check.description}</li>'
            else:
                missing_data_sentence += f'<li>{check.description}</li>'

    failed_combined_checks_sentence = ''
    if checks.get('combined'):
        for check in checks['combined']:
            if not check.passed:
                print(f'Check {check.id} failed with options {check.options} and value {check.value}')
                failed_combined_checks_sentence += f'<li>{check.description}</li>'

    if missing_data_sentence:
        advice += get_prompt('MISSING_DATA', missing_data_sentence=missing_data_sentence)
    if missing_clauses_sentence:
        advice += get_prompt('MISSING_CLAUSES', missing_clauses_sentence=missing_clauses_sentence)
    if failed_combined_checks_sentence:
        advice += get_prompt('FAILED_COMBINED_CHECKS', failed_combined_checks_sentence=extra_advice)
    if not advice:
        advice = get_prompt('NO_ADVICE') if not checks.get('combined') else get_prompt('NO_ADVICE_INC_AO')

    return advice


def calculate_transitievergoeding(checks: ChecksDict) -> str:
    ao_checks = checks['ao']
    ls_checks = checks['ls']
    vso_checks = checks['vso']
    if not vso_checks:
        return ''
    if not ao_checks and not ls_checks:
        return 'Upload de arbeidsovereenkomst en laatste volledige loonstrook om de transitievergoeding te berekenen.'
    if not ao_checks:
        return 'Upload de arbeidsovereenkomst om de transitievergoeding te berekenen.'
    if not ls_checks:
        return 'Upload de laatste volledige loonstrook om de transitievergoeding te berekenen.'
    startdatum = ls_checks.get('STARTDATUM').value
    if vso_checks.get('STARTDATUM').value and vso_checks.get('STARTDATUM').value < startdatum:
        startdatum = vso_checks.get('STARTDATUM').value
    if not startdatum:
        return '<p>Transitievergoeding is niet te berekenen omdat er geen startdatum te vinden is in de loonstrook.</p>'

    einddatum = vso_checks.get('EINDDATUM').value
    if not einddatum:
        return '<p>Transitievergoeding is niet te berekenen omdat er geen einddatum te vinden is in de vaststellingsovereenkomst.</p>'
    years, rest_months, months = calculate_months(startdatum, einddatum)

    result = f'<p>De dienstbetrekking liep van {format_date(startdatum)} tot {format_date(einddatum)}, dat is '
    if years:
        if rest_months:
            result += f'{years} jaar en '
        else:
            result += f'precies {years} jaar. '
    if rest_months:
        result += f'{rest_months} maanden.'
    result += '</p>'

    bruto = ls_checks.get('BRUTO_MAANDSALARIS').value
    vergoeding = round(months * bruto / 36, 2)
    result += f'<p>Het laatste bruto maandsalaris bedroeg € {format_float(bruto)}.</p>'

    result += '<p>'
    # Berekenen van het maximum
    themax = 94_000
    themax_year = 2024
    jaarbruto = bruto * 12
    if jaarbruto > themax:
        if vergoeding > jaarbruto:
            vergoeding = jaarbruto
            result += f'De transitievergoeding wordt beperkt door het wettelijk maximum van 1 bruto jaarsalaris.'
    else:
        if vergoeding > themax:
            vergoeding = themax
            result += f'De transitievergoeding is in dit geval gelijk aan het wettelijk maximum in {themax_year}.'

    result += f'<br/>De transitievergoeding bedraagt hiermee <b>€ {format_float(vergoeding)}</b>.</p>'

    result += f'''<p><i>Op grond van de wet heeft een werknemer van rechtswege aanspraak op de transitievergoeding
        indien de arbeidsovereenkomst door de werkgever wordt beëindigd. Strikt genomen heeft een werknemer dus geen 
        wettelijke recht op de transitievergoeding indien een vaststellingsovereenkomst wordt gesloten, maar het geeft 
        partijen - ook bij het sluiten van een vso - wel enige handvatten, en de transitievergoeding kan dan ook als 
        minimaal uitgangspunt worden genomen als start voor eventuele onderhandelingen. Op basis van de door de 
        geüploade stukken, bedraagt de bruto transitievergoeding € {format_float(vergoeding)}. Dit bedrag kan hoger 
        uitvallen, aangezien het ‘loon’ kan worden vermeerderd (indien dat het geval is) met:<ul>

        <li>de vakantiebijslag (vaak 8%) en de vaste eindejaarsuitkering per jaar gedeeld door 12;</li>
        <li>de in de voorafgaande 12 maanden gemiddeld per maand ontvangen ‘vaste looncomponenten’; 
            zoals overwerkvergoeding en ploegentoeslag;</li>
        <li>de in de voorafgaande drie kalenderjaren gemiddeld per maand ontvangen ‘variabele looncomponenten’, 
        zoals bonussen, winstuitkeringen en variabele eindejaarsuitkeringen.</li></ul></p>'''
    return result


def calculate_months(startdatum: Day, einddatum: Day) -> (int, int, int):
    years = einddatum.y - startdatum.y
    rest_months = einddatum.m - startdatum.m
    if rest_months < 0:
        years -= 1
        rest_months += 12
    months = years * 12 + rest_months
    return years, rest_months, months


def format_date(day: Day) -> str:
    maanden = ['', 'januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober',
               'november', 'december']
    return f'{day.d} {maanden[day.m]} {day.y}'


def format_float(f: float) -> str:
    return f'{f:.2f}'.replace('.', ',')
