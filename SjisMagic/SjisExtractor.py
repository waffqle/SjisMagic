"""
Thanks to CrazyRedMachine for the original version of this little gem.
I owe this fella way too many beers at this point.
-FuckwilderTuesday
"""
import logging
import re
from collections import defaultdict
from SjisMagic import FileUtilities, DatabaseService

logger = logging.getLogger('extraction')
logger.setLevel(logging.INFO)


def extract_strings(input_file_path: str, encoding: str):
    """
    Extract shift-jis strings from a file. Due to the nature of the encoding, shift-jis can't be identified with 100%
    precision. Expect to get some false positives.
    Output is de-duped.

    :param encoding: sjis or shift_jisx0213
    :param input_file_path: Source file
    found in source file. Semicolon delimited.
    """

    logger.info('')
    logger.info('*****************************')
    logger.info(f'Beginning string extraction!')
    logger.info('*****************************')

    if encoding == 'sjis':
        codec_regex = b'[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]+'
        extract_strings_with_codec(input_file_path, codec_regex)
    elif encoding == 'shift_jisx0213':
        codec_regex = b'(?:[\x87-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc ]+|[\x81-\x84][\x40-\x7e\x80-\xfc ]|[\xed-\xee][\x40-\x7e\x80-\xfc ]|[\xfa-\xfc][\x40-\x7e\x80-\xfc ])+'
        extract_strings_with_codec(input_file_path, codec_regex)
    else:
        raise Exception('Invalid encoding.')


def extract_strings_with_codec(input_file_path, codec_regex):
    logger.info(f"Extracting from: {input_file_path}")
    with open(input_file_path, 'rb') as file:
        binary_data = file.read()

    logger.debug(f"Read {len(binary_data)} bytes from {input_file_path}")

    extracted_strings = set()
    # Regular expression to match Shift JIS X 0213 encoded strings
    pattern = re.compile(
        codec_regex)

    # Find all matches of Shift JIS encoded strings
    collected_errors = defaultdict(int)

    potentials = pattern.findall(binary_data)
    logger.info(f'Potential strings: {len(potentials)}')

    for potential in potentials:
        try:
            # False positives will generate UnicodeDecodeError's
            extracted_strings.add(potential.decode('shift_jisx0213'))
        except Exception as e:
            collected_errors[type(e).__name__] += 1
            logger.debug(f"Bytes: {potential}")
            logger.debug(f"Issue: {e}")

    for error in collected_errors.keys():
        logger.warning(f"{error}: {collected_errors[error]}")

    logger.info(f"Unique strings: {len(extracted_strings)}")
    DatabaseService.upsert_extracted_texts(extracted_strings)

    logger.info(f"Storing {len(extracted_strings)} strings in the DB.")
