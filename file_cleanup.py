import logging
import os
from collections import defaultdict

import main
import string_analysis
import utils
from utils import write_file_sjis

cleanup_log = logging.getLogger('cleanup')
cleanup_log.setLevel(logging.INFO)


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
    min_japaneseness = 60

    # Minimum length. It's hard to do anything useful with 2 character katakana strings and such.
    min_length = 8

    #
    # Stop fucking with stuff below here, unless you know what you're doing. =)
    #
    text_codec = os.getenv("TEXT_CODEC")
    cleanup_log.debug(f'Retrieving {text_codec} strings from {input_file_path}')

    # Read the whole input file.
    # Get a list of all potential translation targets
    all_fields = utils.read_file_sjis(dict_file_path)

    cleanup_log.info(f'Culling strings: {len(all_fields)}')

    # Remove unwanted strings
    i = 0
    translation_targets = []
    errors = defaultdict(int)
    for field in all_fields:

        try:
            i += 1

            cleanup_log.debug(f'Processing field {i} of {len(all_fields)}')

            # Decode the bytes
            sjis_text = field.decode(text_codec)
            cleanup_log.debug(f'{sjis_text = }')

            # Is string too short?
            if len(sjis_text) < min_length:
                errors['To Short'] += 1
                cleanup_log.debug(f'Too short({len(sjis_text)}): "{sjis_text}"')
                continue

            # Is string Japanese enough?
            # We want to exclude mostly-english, overly punctuated, etc
            japaneseness = string_analysis.calc_japaneseness(sjis_text)
            if japaneseness < min_japaneseness:
                errors['Not Japanese'] += 1
                cleanup_log.debug(f'Not Jap enough({japaneseness:.0f}%):  "{sjis_text}"')
                continue

            # Make sure the data is actually in the file.
            # (If we can't match the string to the file, we either fucked it up somewhere, or had a false positive
            # when reading it out in the first place.)
            if not utils.check_file_contains_bytes(field, input_file_path):
                errors['Missing In Source'] += 1
                cleanup_log.error(f"Unable to relocate extracted string in original file: {sjis_text}")
                continue

            # Passed all our tests!
            translation_targets.append(sjis_text.encode(text_codec))
        except Exception as e:
            errors[type(e).__name__] += 1
            cleanup_log.debug(f"Field: {field}")
            cleanup_log.debug(f"Issue: {e}")

    for error in errors:
        cleanup_log.warning(f'{error}: {errors[error]}')

    cleanup_log.info(f'Translatable: {translation_targets.__len__()}')

    # If a debug limit is specified, only process that many rows.
    if 0 < main.only_process_first_rows <= len(translation_targets):
        cleanup_log.info(f'Trimming list to: {main.only_process_first_rows} (Debug limit was specified)')
        translation_targets = translation_targets[:main.only_process_first_rows]

    # Dump the dict to a file.
    cleanup_log.info(f'Culled list: {output_file_path}')
    write_file_sjis(output_file_path, translation_targets)
