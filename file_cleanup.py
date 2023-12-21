from collections import defaultdict

import main
import string_analysis
import utils
from utils import write_file_sjis

debug = True


def cleanup_file(input_file_path, dict_file_path, output_file_path):
    """
    Read a file and analyze all the sjis contents. This is the main culling function. We'll remove anything we can't
    translate, we don't want to translate, or otherwise want to exclude.


    :param input_file_path: Path to original input file
    :param dict_file_path: Path to input dict file
    :param output_file_path: Path to dump output dictionary
    """

    """
    Modifiable options
    Tweak these if you're not happy with the results you're seeing
    """
    # Minimum percentage of Japanese(ish) characters.
    # Running strings that are 90% english through the translator tends to do more harm than good.
    min_japaneseness = 40

    # Minimum length. It's hard to do anything useful with 2 character katakana strings and such.
    min_length = 3

    # Codec - You probably shouldn't change this, but here it is.
    text_codec = 'sjis'

    #
    # Stop fucking with stuff below here, unless you know what you're doing. =)
    #

    # Read the whole input file.
    all_fields = utils.read_file_sjis(dict_file_path)

    # Remove unwanted strings
    i = 0
    translation_targets = []
    errors = defaultdict(int)
    for field in all_fields:
        try:
            i += 1
            print()
            print(f'Processing field {i} of {len(all_fields)}')
            # Decode the bytes
            sjis_text = field.decode(text_codec)

            # Is string too short?
            if len(sjis_text) < min_length:
                errors['too_short'] += 1

                if debug:
                    print(f'Too short({len(sjis_text)}): "{sjis_text}"')
                continue

            # Is string Japanese enough?
            # We want to exclude mostly-english, overly punctuated, etc
            japaneseness = string_analysis.calc_japaneseness(sjis_text)
            if japaneseness < min_japaneseness:
                errors['not_japanese'] += 1
                if debug:
                    print(f'Not Jap enough({japaneseness:.0f}%):  "{sjis_text}"')
                continue

            # Make sure the data is actually in the file.
            # (If we can't match the string to the file, we either fucked it up somewhere, or had a false positive
            # when reading it out in the first place.)
            if not utils.check_file_contains_bytes(field, input_file_path):
                errors['missing_in_source'] += 1
                if debug:
                    print(f'Missing in source: {sjis_text}')
                continue

            # Passed all our tests!
            translation_targets.append(sjis_text.encode(text_codec))

        except UnicodeDecodeError as e:
            if debug:
                print(f'Decoding error: {e}')
                print(f' Field: {field}')
            errors['decoding_error'] += 1
            quit()
        except Exception as e:
            errors['unknown_error'] += 1
            print(f'Unexpected parsing issue: {e.__class__.__name__}: {e}')

    for error in errors:
        print(f'Error: {error} Count: {errors[error]}')

    print(f'File contains {translation_targets.__len__()} translation targets.')

    # If a debug limit is specified, only process that many rows.
    if 0 < main.only_process_first_rows <= len(translation_targets):
        print(f'Trimming list to: {main.only_process_first_rows} (Debug limit was specified)')
        translation_targets = translation_targets[:main.only_process_first_rows]

    # Dump the dict to a file.
    write_file_sjis(output_file_path, translation_targets)
