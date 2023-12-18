"""
Thanks to CrazyRedMachine for this little gem.
I owe this fella way too many beers at this point.
-FuckwilderTuesday
"""
import os
from typing import List

import translation_validation
import utils


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

    extracted_strings: list[bytearray] = []

    byte1 = inputfile.read(1)
    word = bytearray()
    length = 0
    count = 0
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
                        # Add word to list
                        extracted_strings.append(word)
                        # Reset for next word
                        count += 1
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

    outputfile = open(output_file_path, "wb")
    for word in extracted_strings:
        outputfile.write(word)
        outputfile.write(b';;;')
        outputfile.write(b'\x0A')

    print(f"Found {count} sjis strings.")


def cleanup_file(dict_file_path, output_file_path):
    """
    Read the file created by the extract_sjis module and convert it into a dictionary. Any invalid sjis strings will be
    dropped. Also, dropping misc other things that we don't want to translate.

    :param dict_file_path: Path to input dict file
    :param output_file_path: Path to dump output dictionary
    """
    # Read the whole input file.
    with open(dict_file_path, 'rb', encoding='sjis') as dict_file:
        file_contents = dict_file.read()

    # Split it on semicolons - Remember, some strings are multi-line
    all_fields = file_contents.split(b';;;')

    print(f'Found {len(all_fields)} fields in {dict_file_path}\n')

    # Create a dict of translation targets.
    parsing_errors = 0
    duplicates = 0
    non_translatable_strings = 0
    japanese_texts = {}
    for field in all_fields:
        sjis_text = field.decode('sjis')


    for i in range(0, len(all_fields), 2):
        try:
            # Parse into a variable first, so we don't get empty dict entries on failures
            sjis_text = all_fields[i + 1].decode('sjis')

            if japanese_texts.__contains__(sjis_text):
                duplicates += 1
                continue

            if not translation_validation.string_is_translation_target(sjis_text):
                non_translatable_strings += 1
                continue

            japanese_texts[sjis_text] = ''  # We'll put translations in here later!
        except UnicodeDecodeError as e:
            # print(f'Parsing error. We expect a few of these. Error: {e}')
            parsing_errors += 1
        except Exception as e:
            print(f'Unexpected parsing issue: {e.__class__.__name__}: {e}')

    print(f'Parsing errors: {parsing_errors}. (We expect some of these. Sjis detection is inherently troublesome.)')
    print(f'Found {non_translatable_strings} non-translatable strings.')
    print(f'Found {duplicates} duplicate strings.')
    print(f'File contains {japanese_texts.__len__()} unique, valid sjis strings that we actually want to translate.')

    # Dump the dict to a file.
    # Don't really need this, just handy for review/debug
    with open(output_file_path, 'w', encoding='utf-8') as deduped_file:
        for japanese_text in japanese_texts:
            deduped_file.write(f'{japanese_text}\n')

    return japanese_texts


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
