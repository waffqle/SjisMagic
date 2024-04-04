import logging
import os
from collections import defaultdict
import re
from SjisMagic import FileUtilities, StringAnalyzer
from SjisMagic.DatabaseService import *

logger = logging.getLogger('cleanup')
logger.setLevel(logging.INFO)


def exclude_too_short_strings(min_length: int):
    announce_status(f"Excluding strings below {min_length} from translation.")

    with sqlite_db.atomic():
        query = Translation.update(exclude_from_translation=True, exclusion_reason='Too Short').where(
            Translation.text_length < min_length, Translation.exclude_from_translation == False)
        rows_touched = query.execute()
    logger.info(f"Excluded {rows_touched:,} short phrases.")


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
    min_japaneseness = 20

    # Minimum length. It's hard to do anything useful with 2 character katakana strings and such.
    min_length = 4

    # Only process the first X rows
    # Set this to a value, and we'll only process that many rows. (Makes debugging faster/cheaper.)
    # We take select these rows AFTER doing all culling, so they should be valid translation targets.
    only_process_first_rows = 0

    #
    # Stop fucking with stuff below here, unless you know what you're doing. =)
    #
    text_codec = os.getenv("TEXT_CODEC")

    logger.info('')
    logger.info('**************************')
    logger.info('Culling extracted strings!')
    logger.info('**************************')

    logger.debug(f'Retrieving strings from {input_file_path}')

    # Read the whole input file.
    # Get a list of all potential translation targets
    # This returns the raw bytes
    all_bytes = FileUtilities.read_file_sjis(dict_file_path)
    # Decode the strings
    all_fields = [x.decode(text_codec) for x in all_bytes]

    logger.info(f'Strings to process: {len(all_fields)}')

    translation_targets = []
    errors = defaultdict(int)

    # Run our validations against the fields.
    # Do the easiest validations first, hardest last.

    logger.info(f'Removing strings with escape sequences...')
    translation_targets = [x for x in all_fields if has_no_escape_sequences(x, errors)]

    logger.info(f'Remove strings shorter than {min_length} characters...')
    translation_targets = [x for x in translation_targets if is_long_enough(x, min_length, errors)]

    logger.info(f'Removing strings less than  {min_japaneseness}% Japanese characters...')
    translation_targets = [x for x in translation_targets if is_japanese_enough(x, min_japaneseness, errors)]

    logger.info(f'Removing strings with Chinese characters...')
    translation_targets = [x for x in translation_targets if has_no_chinese_char(x, errors)]

    if logger.level == logging.DEBUG:
        # Not the best practice to change logic when you're debugging. I KNOW.
        # But this is a heavy activity, and it shouldn't fail unless we've changed
        # something in the extraction logic.
        # If something is fucked up, this is worth checking.
        logger.info(f'Checking that strings exist in source file.')
        check_strings_exist_in_source(input_file_path, all_fields, translation_targets, errors, text_codec)

    for error in errors:
        logger.warning(f'Cull: {error}: {errors[error]}')

    logger.info(f'Translatable: {len(translation_targets)}')

    # If a debug limit is specified, only process that many rows.
    if 0 < only_process_first_rows <= len(translation_targets):
        logger.info(f'Trimming list to: {only_process_first_rows} (Debug limit was specified)')
        translation_targets = translation_targets[:only_process_first_rows]

    # Dump the dict to a file.
    # Make sure to send it bytes, not strings
    logger.info(f'Culled list: {output_file_path}')
    FileUtilities.write_file_sjis(output_file_path, [x.encode(text_codec) for x in translation_targets])


def has_no_escape_sequences(field, errors):
    # Find percent symbols followed by a letter.
    pattern = r'%[a-zA-Z]'

    if re.search(pattern, field):
        errors['Escape Sequence'] += 1
        return False
    else:
        return True


def is_long_enough(field, min_length, errors):
    if len(field) < min_length:
        errors['To Short'] += 1
        return False
    else:
        return True


def is_japanese_enough(field, min_japaneseness, errors):
    # Is string Japanese enough?
    # We want to exclude mostly-english, overly punctuated, etc
    japaneseness = StringAnalyzer.calc_japaneseness(field)
    if japaneseness < min_japaneseness:
        errors['Not Japanese'] += 1
        logger.debug(f'Not Jap enough({japaneseness:.0f}%):  "{field}"')
        return False
    else:
        return True


def has_no_chinese_char(field, errors):
    has_chinese = StringAnalyzer.contains_chinese(field)
    if has_chinese:
        errors['Chinese Characters'] += 1
        logger.debug(f'Chinese char found: {field}')
        return False
    else:
        return True


def check_strings_exist_in_source(source_file, all_fields, translation_targets, errors, text_codec):
    # This function wants the RAW BYTES.
    # Not the decoded string.

    # We'll look to make sure our strings exist in this file
    with open(source_file, 'rb') as f:
        contents = f.read()

    # It's a bit wasteful to re-encode stuff we just decoded.
    # However, it's a handy validation that our values are round-tripping accurately
    for field in [x.encode(text_codec) for x in all_fields]:
        try:
            # Make sure the data is actually in the file.
            # If we can't match the string to the source file... we fucked up somewhere.
            if contents.find(field) == -1:
                errors['Missing In Source'] += 1
                logger.error(f"Unable to relocate extracted string in original file: {field.decode(text_codec)}")
                continue
            else:
                translation_targets.append(field.decode(text_codec))

        except Exception as e:
            errors[type(e).__name__] += 1
            logger.debug(f"Field: {field}")
            logger.debug(f"Issue: {e}")
