"""
Thanks to CrazyRedMachine for this little gem.
I owe this fella way too many beers at this point.
-FuckwilderTuesday
"""
import logging
import re
from collections import defaultdict

import utils

extraction_log = logging.getLogger('extraction')
extraction_log.setLevel(logging.INFO)


def extract_strings(input_file_path: str, output_file_path: str, encoding: str):
    """
    Extract shift-jis strings from a file. Due to the nature of the encoding, shift-jis can't be identified with 100%
    precision. Expect to get some false positives.
    Output is de-duped.

    :param encoding: sjis or shift_jisx0213
    :param input_file_path: Source file
    :param output_file_path: Dictionary of strings with address where they were
    found in source file. Semicolon delimited.
    """
    if encoding == 'sjis':
        codec_regex = b'(?:[\x87-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc ]+|[\x81-\x84][\x40-\x7e\x80-\xfc ]|[\xed-\xee][\x40-\x7e\x80-\xfc ]|[\xfa-\xfc][\x40-\x7e\x80-\xfc ])+'
        extract_strings_with_regex(input_file_path, output_file_path, codec_regex)
    elif encoding == 'shift_jisx0213':
        codec_regex = b'(?:[\x87-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc ]+|[\x81-\x84][\x40-\x7e\x80-\xfc ]|[\xed-\xee][\x40-\x7e\x80-\xfc ]|[\xfa-\xfc][\x40-\x7e\x80-\xfc ])+'
        extract_strings_with_regex(input_file_path, output_file_path, codec_regex)
    else:
        raise Exception('Invalid encoding.')


def extract_strings_with_regex(input_file_path, output_file_path,
                               codec_regex):
    extraction_log.info(f"Extracting from: {input_file_path}")
    with open(input_file_path, 'rb') as file:
        binary_data = file.read()

    extraction_log.debug(f"Read {len(binary_data)} bytes from {input_file_path}")

    shift_jis_strings = []
    # Regular expression to match Shift JIS X 0213 encoded strings
    pattern = re.compile(
        codec_regex)

    # Find all matches of Shift JIS encoded strings
    collected_errors = defaultdict(int)

    for match in pattern.findall(binary_data):
        try:
            # Decode the Shift JIS encoded string
            decoded_string = match.decode('shift_jisx0213')
            shift_jis_strings.append(decoded_string.encode('shift_jisx0213'))
        except Exception as e:
            collected_errors[type(e).__name__] += 1
            extraction_log.debug(f"Bytes: {match}")
            extraction_log.debug(f"Issue: {e}")

    utils.write_file_sjis(output_file_path, shift_jis_strings)
    extraction_log.info(f"Found strings: {len(shift_jis_strings)}")
    for error in collected_errors.keys():
        extraction_log.warning(f"{error}: {collected_errors[error]}")
