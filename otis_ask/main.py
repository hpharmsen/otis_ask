import mimetypes
import os
import sys

from otis_ask import analyze_vso, check_document_type, analyze_ao
from otis_ask.analysis import check_vso_with_ao, generate_advice, analyze_ls, calculate_transitievergoeding
from otis_ask.checks import Checks
from otis_ask.output import color_print, print_response

try:
    from documentreader import read_file
except ImportError:
    try:
        from .documentreader import read_file
    except ImportError:
        from otis_ask.documentreader import read_file


def get_params():
    if len(sys.argv) < 2:
        color_print("Usage: python main.py <file> <file>", "RED")
        sys.exit(1)
    return sys.argv[1:]


LOCAL_POPPLER_PATH = '/opt/homebrew/Cellar/poppler/23.12.0/bin'

if __name__ == "__main__":
    checks = {'vso': Checks(), 'ao': Checks(), 'ls': Checks()}
    for input_file in get_params():
        poppler_path = LOCAL_POPPLER_PATH if os.path.isdir(LOCAL_POPPLER_PATH) else None
        print('POPPLER_PATH', poppler_path)
        mimetype = mimetypes.guess_type(input_file)[0]

        text = read_file(input_file, mime_type=mimetype, poppler_path=poppler_path)
        document_type = check_document_type(text)
        print()
        print(input_file)
        print('---------------------------------------------------------------''')
        print('Dit is een', document_type)
        match document_type:
            case 'vaststellingsovereenkomst':
                vso_text = text
                analyze_vso(text, checks)
            case 'arbeidsovereenkomst':
                ao_text = text
                analyze_ao(text, checks)
            case 'loonstrook':
                ls_text = text
                analyze_ls(text, checks)
            case _:
                print(f'Document type {document_type} not recognized')
                sys.exit()

        print_response(checks['vso'])
        print_response(checks['ao'])
        print_response(checks['ls'])

        combined_checks = Checks()
        extra_advice = ''
        if checks.get('vso') and checks.get('ao'):
            extra_advice = check_vso_with_ao(checks)
            print('-----')
            print_response(combined_checks)
        advice = generate_advice(checks, extra_advice)
        print(advice)

    transitievergoeding = calculate_transitievergoeding(checks)
    if transitievergoeding:
        print(transitievergoeding)
