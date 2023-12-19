"""
Thanks to CrazyRedMachine for this little gem.
I owe this fella way too many beers at this point.
-FuckwilderTuesday
"""
from itertools import count

import main
import translation_validation
import utils
from utils import write_file_sjis


def extract_strings(input_file_path: str, output_file_path: str):
    """
    Extract shift-jis strings from a file. Due to the nature of the encoding, shift-jis can't be identified with 100%
    precision. Expect to get some false positives.
    Output is de-duped.

    :param input_file_path: Source file
    :param output_file_path: Dictionary of strings with address where they were
    found in source file. Semicolon delimited.
    """

    print(f"Extracting: {input_file_path}")

    inputfile = open(input_file_path, "rb")

    extracted_strings = []

    byte1 = inputfile.read(1)
    word = bytearray()
    length = 0
    count = 0
    decoding_errors = 0
    offset = 0
    off_comp = 1
    rearm = 0
    has_dbl = 0
    while byte1:
        if sjis_valid_single(byte1) and has_dbl:
            word.extend(byte1)
            length += 1
            off_comp += 1
        else:
            byte2 = inputfile.read(1)
            offset += 1
            if sjis_valid_double(byte1, byte2):
                has_dbl = 1
                word.extend(byte1)
                word.extend(byte2)
                length += 1
                off_comp += 2
            else:
                if length > 1 and has_dbl:  # end of word reached (minlen 2), add to file
                    if word not in extracted_strings:
                        try:
                            # Add word to list
                            extracted_strings.append(word)
                            count += 1
                        except UnicodeDecodeError as e:
                            decoding_errors += 1

                    # Reset for next word
                    word = bytearray()
                    has_dbl = 0
                    length = 0
                    off_comp = 1
                    rearm = 1
        if rearm:
            byte1 = byte2
            rearm = 0
        else:
            byte1 = inputfile.read(1)
            offset += 1

    utils.write_file_sjis(output_file_path, extracted_strings)

    print(f"Found {count} sjis strings. Had {decoding_errors} decoding errors.")


def cleanup_file(dict_file_path, output_file_path):
    """
    Read the file created by the extract_sjis module. Any invalid sjis strings will be
    dropped. Also, dropping misc other things that we don't want to translate.

    :param dict_file_path: Path to input dict file
    :param output_file_path: Path to dump output dictionary
    """
    # Read the whole input file.
    with open(dict_file_path, 'rb') as dict_file:
        file_contents = dict_file.read()

    # Split it on semicolons - Remember, some strings are multi-line
    all_fields = file_contents.split(b';;;\x0A')

    print(f'Found {len(all_fields)} fields in {dict_file_path}\n')

    # Collect our translation targets
    translation_targets = []
    parsing_errors = 0
    non_translatable_strings = 0
    for field in all_fields:
        try:
            # Decode the bytes
            sjis_text = field.decode('sjis')

            # Is it something we want to translate?
            if translation_validation.string_is_translation_target(sjis_text):
                translation_targets.append(sjis_text.encode('sjis'))
                continue
            else:
                non_translatable_strings += 1
        except UnicodeDecodeError as e:
            # print(f'Parsing error. We expect a few of these. Error: {e}')
            parsing_errors += 1
        except Exception as e:
            print(f'Unexpected parsing issue: {e.__class__.__name__}: {e}')

    print(f'Parsing errors: {parsing_errors}.')
    print(f'Found {non_translatable_strings} undesirable/non-translatable strings.')
    print(f'File contains {translation_targets.__len__()} translation targets.')

    # If a debug limit is specified, only process that many rows.
    if 0 < main.only_process_first_rows <= len(translation_targets):
        print(f'Trimming list to: {main.only_process_first_rows} (Debug limit was specified)')
        translation_targets = translation_targets[:main.only_process_first_rows]

    # Dump the dict to a file.
    write_file_sjis(output_file_path, translation_targets)


def sjis_valid_double(first, second):
    # print("test ", first,second)
    valid_first = (b"\x81" <= first <= b"\x9F") or (b"\xE0" <= first <= b"\xFC")
    valid_second = (b"\x40" <= second <= b"\x9E") or (b"\x9F" <= second <= b"\xFC")
    return valid_first and valid_second


def sjis_valid_single(char):
    ascii = (char == b"\x0A") or (b"\x20" <= char <= b"\x7F")
    custom = (b"\xA1" <= char <= b"\xDF")
    # return ascii
    return ascii or custom
