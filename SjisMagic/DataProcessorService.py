import asyncio
import re
from enum import Enum
from typing import Callable

import unicodedata

import utils
from SjisMagic import OpenAIService, AnthropicService
from SjisMagic.DatabaseService import *
from SjisMagic.DatabaseService import exclude_string
from utils import announce_status

logger = logging.getLogger('dataprocessor')
logger.setLevel(logging.DEBUG)


# We're supporting multiple models for translation and paraphrasing.
# We'll then compare the translations and accept the best one.
class Brain(Enum):
    ChatGPT = 1
    Claude = 2
    Google = 3


async def crank_up_translation_machine(batch_size=100):
    """
    Look for stuff in the DB that needs translation or other work. Then start queuing up tasks, so we can get it
    done. :param batch_size: We'll query and queue items in small batches for monitoring, performance testing,
    etc. The entire batch gets queued up and translation runs in parallel.
    """
    utils.announce_status('Starting translation machine')

    # Do we have any outstanding work?
    workitems_count = get_untranslated_items_count()
    logger.info(f'Found {workitems_count:,} missing translations.')

    if workitems_count == 0:
        logger.info(f'No work to do!')
        return
    else:
        logger.info(f"We'll handle em in batches of {batch_size:,}.")

    # Get all things that need translating
    translateables = get_untranslated_items(-1)
    for translateable in chunked(translateables, batch_size):
        with sqlite_db.atomic():
            logger.info(f'Processing {len(translateable)} strings.')
            taskset = set()
            # Put it in the queue
            for trans in translateable:
                # Do we need Claude version?

                if trans.anthropic_translation == '':
                    task_claude = asyncio.create_task(translate_and_save(trans, Brain.Claude))
                    taskset.add(task_claude)

                # Do we need GPT translation?
                if trans.openai_translation == '':
                    task_openai = asyncio.create_task(translate_and_save(trans, Brain.ChatGPT))
                    taskset.add(task_openai)

            # Log any errors.
            # We don't break, too annoying to set it off on 10k+ translations and have it fail on 5,000...
            results = await (asyncio.gather(*taskset, return_exceptions=True))
            for i, result in enumerate(results, start=1):
                if isinstance(result, Exception):
                    logger.warning(f"Error on task {i}: {result}")

    else:
        logger.info(f'No more items to queue!')


async def translate_and_save(trans: Translation, brain):
    logger.debug(f"Translating '{trans.extracted_text}'...")
    if brain == Brain.ChatGPT:
        trans.openai_translation = OpenAIService.translate(trans.extracted_text)
        logger.debug(f'Translated (GPT): "{trans.extracted_text}" to "{trans.openai_translation}"')
    elif brain == Brain.Claude:
        trans.anthropic_translation = AnthropicService.translate(trans.extracted_text)
        logger.debug(f'Translated (Claude): "{trans.extracted_text}" to "{trans.anthropic_translation}"')
    elif brain == Brain.Google:
        raise NotImplemented
    else:
        logger.error(f'Unknown brain {brain}')

    trans.save()


def exclude_strings(exclusion_reason: str, excluder: Callable, *kwargs):
    """
    Test all strings in the DB against the given function.
    :param exclusion_reason: Reason to list in DB  for why these strings are excluded
    :param excluder: Function to test string against. True = exclude, False = include
    """
    announce_status(f"Excluding strings via function {excluder}.")

    non_excluded_strings = Translation.select().where(Translation.exclude_from_translation == 0).count()
    logger.info(f'Reviewing {non_excluded_strings:,} strings.')

    exclusion_count = 0
    # Let's go through em all.
    stuff_to_review = Translation.select().where(Translation.exclude_from_translation == 0)
    with sqlite_db.atomic():
        for item in stuff_to_review:
            jap_text = item.extracted_text
            # Test string against our exclusion function
            if not excluder(jap_text, *kwargs):
                exclude_string(jap_text, exclusion_reason)
                exclusion_count += 1

        logger.info(f'Excluded {exclusion_count:,} strings. Reason: {exclusion_reason}')


def exclude_unfindable_strings(source_file, text_codec):
    announce_status(f"Examining '{source_file}' to ensure extracted strings are present.")
    # We'll look to make sure our strings exist in this file
    with open(source_file, 'rb') as f:
        contents = f.read()

    non_excluded_strings = Translation.select().where(Translation.exclude_from_translation == 0).count()
    logger.info(f'Reviewing {non_excluded_strings:,} strings.')

    exclusion_count = 0
    error_count = 0
    # Let's go through em all.
    stuff_to_review = Translation.select().where(Translation.exclude_from_translation == 0)
    with sqlite_db.atomic():
        # Make sure to catch exceptions here. If we fucked up our encoding/decoding somewhere, it'll show up here.
        for phrase in [x.extracted_text.encode(text_codec) for x in stuff_to_review]:
            try:
                # Make sure the data is actually in the file.
                # If we can't match the string to the source file... we fucked up somewhere.
                if contents.find(phrase) == -1:
                    logger.debug(f"Unable to relocate extracted string in original file: {phrase.decode(text_codec)}")
                    exclude_string(phrase, 'Missing in Source File')
                    exclusion_count += 1

            except Exception as e:
                logger.debug(f"Error checking for '{phrase}' in source: {e.__class__.__name__}")
                exclude_string(phrase, "Error Checking Source File")
                error_count += 1

    logger.info(f"Excluded {exclusion_count:,} strings. Reason: Missing in source.")
    logger.info(f"Excluded {error_count:,} strings. Reason: Error checking source.")


def cull_translations(translation_dic: dict):
    logger.debug(f"Culling translations: {translation_dic}")

    unwanted_things = {'NNN', 'PPP', 'CCC'}  # better membership test than list

    keys_to_remove = [key for key, value in translation_dic.items() if value in unwanted_things]
    for key in keys_to_remove:
        del translation_dic[key]

    logger.debug(f"Culled: {translation_dic}")
    return translation_dic


# region String validators
def is_string_japanese_enough(phrase: str, min_jap_perc: int):
    jap_perc = calc_japanese_percentage(phrase)
    if jap_perc < min_jap_perc:
        logger.debug(f"Japanese-ness: {jap_perc:.0f}% - Excluding: {phrase}")
        return False
    else:
        return True


def is_string_variant_enough(phrase: str, min_variety: int):
    # Does the string have a variety of different characters?
    char_variety = calc_character_variety_percentage(phrase)

    if char_variety < min_variety:
        logger.debug(f"Char Variety: {char_variety:.0f}% -  {phrase}")
        return False
    return True


def is_string_nonrepeating(phrase: str, repetition_limit: int):
    # Regular expression to match a sequence of repeating characters
    pattern = r'(.)\1{' + str(repetition_limit - 1) + r'}'

    if re.search(pattern, phrase) is not None:
        logger.debug(f"Too much repetition - Excluding: {phrase}")
        return False
    return True


def is_string_long_enough(phrase: str, min_length: int):
    if len(phrase) < min_length:
        logger.debug(f"Too short - Excluding: {phrase}")
        return False
    return True


# endregion

# region Supporting Items
def calc_character_variety_percentage(input_string: str):
    """
    Calculates the variety of characters in a string, expressed as a percentage.

    :param input_string: The input string to analyze.
    :return: The percentage of character variety in the string.
    """
    if not input_string:  # Handle empty string
        return 0

    total_chars = len(input_string)
    unique_chars = len(set(input_string))  # Set of unique characters

    variety_percentage = (unique_chars / total_chars) * 100
    return variety_percentage


def calc_japanese_percentage(input_string):
    """Calculate the percentage of Japanese characters in a string."""
    if not input_string:
        return 0  # Return 0% if the input string is empty or None

    total_chars = len(input_string)
    japanese_chars = sum(is_char_japanese(char) for char in input_string)

    return (japanese_chars / total_chars) * 100


def is_char_japanese(char):
    """Check if a character is Japanese."""
    # Check for Hiragana and Katakana
    if '\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF':
        return True
    # Check for common and uncommon Kanji
    if '\u4E00' <= char <= '\u9FAF' or '\u3400' <= char <= '\u4DBF':
        return True
    # Exclude full-width Roman characters
    # These don't actually need translation.
    # if '\uFF00' <= char <= '\uFFEF':
    #     return True
    # Additional checks for other characters considered as Japanese (e.g., punctuation)
    if '\u3000' <= char <= '\u303F':
        return True
    # Use unicodedata to check for the 'Lo' (Letter, other) category, which includes more Kanji
    if unicodedata.category(char) == 'Lo':
        return any(['CJK UNIFIED' in unicodedata.name(char, ''),
                    'HIRAGANA' in unicodedata.name(char, ''),
                    'KATAKANA' in unicodedata.name(char, '')])
    return False

# endregion
