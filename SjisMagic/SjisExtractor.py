"""
Thanks to CrazyRedMachine for the original version of this little gem.
I owe this fella way too many beers at this point.
-FuckwilderTuesday
"""
import re
import time
from collections import defaultdict

from SjisMagic.DatabaseService import *
from utils import announce_status

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

    announce_status("Extracting strings")

    if encoding == 'sjis':
        codec_regex = b'[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]+'
    elif encoding == 'shift_jisx0213':
        codec_regex = (b'(?:[\x87-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]+|[\x81-\x84][\x40-\x7e\x80-\xfc]|[\xed-\xee]['
                       b'\x40-\x7e\x80-\xfc]|[\xfa-\xfc][\x40-\x7e\x80-\xfc])+\x00')
    elif encoding == 'cp932':
        codec_regex = b'[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]+\x00'

    else:
        raise Exception('Invalid encoding.')

    extract_strings_with_codec(input_file_path, codec_regex, encoding)


def extract_strings_with_codec(input_file_path: str, codec_regex: bytes, encoding: str):
    logger.info(f"Extracting from: {input_file_path}")
    with open(input_file_path, 'rb') as file:
        binary_data = file.read()

    logger.debug(f"Read {len(binary_data):,} bytes from {input_file_path}")

    extracted_strings = set()
    collected_errors = defaultdict(int)
    # Regular expression to match Shift JIS X 0213 encoded strings
    pattern = re.compile(codec_regex)

    matches = pattern.finditer(binary_data)
    for match in matches:
        byte_sequence = match.group()[:-1]  # Strip the null byte
        try:
            decoded_string = byte_sequence.decode('shift_jisx0213')
            extracted_strings.add(decoded_string)
        except UnicodeDecodeError:
            collected_errors["DecodeError"] += 1
        except Exception as e:
            collected_errors[type(e).__name__] += 1
            logger.debug(f"Bytes: {match}")
            logger.debug(f"Issue: {e}")

    for error in collected_errors.keys():
        logger.warning(f"{error}: {collected_errors[error]:,}")

    logger.info(f"Unique strings: {len(extracted_strings):,}")
    upsert_extracted_texts(extracted_strings)


def upsert_extracted_texts(texts):
    announce_status(f"Inserting {len(texts):,} translations")

    start_time = time.time()

    results = defaultdict(int)
    with sqlite_db.atomic():
        for text in texts:
            try:
                # Remove extra whitespace
                text = text.strip()

                if not text or text.isspace():
                    results['Whitespace'] += 1
                    continue  # Can't translate whitespace

                # Insert if it's not in here already
                upserted_tran = Translation.insert(extracted_text=text,
                                                   text_length=len(text)).on_conflict_ignore().execute()

                if upserted_tran:
                    results['New Phrase'] += 1
                    logger.debug(f'New phrase: {text}')
                else:
                    results['Already Exists'] += 1
                    logger.debug(f"Already inserted: {text}")
            except Exception as e:
                logger.error(f"Insert failed for '{text}'\n{type(e).__name__}: {e}")

    elapsed_time = time.time() - start_time
    for result in results.keys():
        logger.info(f"Result '{result}' count: {results[result]:,}")

    logger.info(f"Inserted {results['New Phrase']:,} new strings.")
    logger.info(f"Processed {len(texts):,} texts in {elapsed_time:,.2f} seconds.")
    logger.info(f"Rec/sec: {len(texts) / elapsed_time:,.0f} ")
