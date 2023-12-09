import sys

from otis_ask import analyze_vso, check_document_type, analyze_ao
from otis_ask.analysis import check_vso_with_ao
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


if __name__ == "__main__":
    vso_checks = ao_checks = None
    for input_file in get_params():
        text = read_file(input_file)
        document_type = check_document_type(text)
        print()
        print(input_file)
        print('---------------------------------------------------------------''')
        print('Dit is een', document_type)
        match document_type:
            case 'vaststellingsovereenkomst':
                vso_text = text
                vso_checks, advice = analyze_vso(text, ao_checks)
            case 'arbeidsovereenkomst':
                ao_text = text
                ao_checks, advice = analyze_ao(text, vso_checks)
            case _:
                print(f'Document type {document_type} not recognized')
                sys.exit()


        print_response("vso", vso_checks)
        print_response("ao", ao_checks)
        print(advice)
        if vso_checks and ao_checks:
            combined_checks, extra_advice = check_vso_with_ao(vso_checks, ao_checks)
            print_response("vso", combined_checks)
            print(extra_advice)
