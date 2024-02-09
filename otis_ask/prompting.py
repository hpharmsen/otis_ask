from justai import get_prompt2
from justdays import Day

from otis_ask.checks import Checks


def create_prompt(document_text: str, checks: Checks):

    checks_string = create_checks_string(checks)
    answer_format = create_answer_format(checks)

    prompt = get_prompt2('ANALYZE_DOCUMENT', document_text=document_text, checks=checks_string,
                        answer_format=answer_format)
    return prompt.replace('\\n', '\n')


def create_checks_string(checks: Checks):
    """ Convert a list of checks to a text that can be used in the prompt """
    date_checks = []
    checks_string = ''
    for i, check in enumerate(checks):
        checks_string += f'{i + 1} {check.prompt}'
        if check.options:
            checks_string += ' (antwoord met ' + str_combine(check.options, 'of') + ')'
        if check.check_type == Day:
            date_checks += [str(i + 1)]
        checks_string += ';\n'
    if date_checks:
        checks_string += get_prompt('EXTRACT_DATE_FORMAT', fields=str_combine(date_checks, "en"))
    return checks_string


def create_answer_format(checks: Checks, length=6):
    """ Convert a list of checks to a text that specifies the answer format for in the prompt """
    answer_format = ''
    for i, check in enumerate(checks[:length]):
        how = check.options[0] if check.options else check.description
        answer_format += f'{i+1} {how}\n'
    return answer_format


def str_combine(items: list, sep: str):
    """ ["yes", "no", "maybe"] -> "yes, no or maybe" """
    if not items:
        return ''
    if len(items) == 1:
        return str(items[0])
    return ",".join([str(item) for item in items[:-1]]) + " " + sep + " " + str(items[-1])
