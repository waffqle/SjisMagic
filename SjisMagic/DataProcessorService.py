import asyncio
from enum import Enum
import re

import unicodedata

import utils
from SjisMagic import OpenAIService, AnthropicService
from SjisMagic.DatabaseService import *
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

    # Keep on working till the work is done.
    while get_untranslated_items_count() > 0:
        # Fetch a chunk - Working in small chunks is easier to monitor than queuing up thousands of tasks at once
        translatables_batch = get_untranslated_items(batch_size)

        logger.info(f'Queuing up {len(translatables_batch):,} items.')

        taskset = set()
        # Put it in the queue
        for trans in translatables_batch:
            # Do we need Claude version?
            if trans.anthropic_translation == '':
                task_claude = asyncio.create_task(translate_and_save(trans, Brain.Claude))
                task_claude.add_done_callback(taskset.discard)
                taskset.add(task_claude)

            # Do we need GPT translation?
            if trans.openai_translation == '':
                task_openai = asyncio.create_task(translate_and_save(trans, Brain.ChatGPT))
                task_openai.add_done_callback(taskset.discard)
                taskset.add(task_openai)

        await (asyncio.gather(*taskset, return_exceptions=True))

    else:
        logger.info(f'No more items to queue!')


async def translate_and_save(trans: Translation, brain):
    if brain == Brain.ChatGPT:
        trans.openai_translation = OpenAIService.translate(trans.extracted_text)
        logger.debug(f'Translated (GPT): "{trans.extracted_text}" to "{trans.openai_translation}"')
    elif brain == Brain.Claude:
        trans.anthropic_translation = AnthropicService.translate(trans.extracted_text)
        logger.debug(f'Translated (Claude): "{trans.extracted_text}" to "{trans.anthropic_translation}"')
    elif brain == Brain.Google:
        raise NotImplemented

    trans.save()


def cull_translations(translation_dic: dict):
    logger.debug(f"Culling translations: {translation_dic}")

    unwanted_things = {'NNN', 'PPP', 'CCC'}  # better membership test than list

    keys_to_remove = [key for key, value in translation_dic.items() if value in unwanted_things]
    for key in keys_to_remove:
        del translation_dic[key]

    logger.debug(f"Culled: {translation_dic}")
    return translation_dic


def exclude_too_short_strings(min_length: int):
    announce_status(f"Excluding strings below {min_length} from translation.")

    with sqlite_db.atomic():
        query = Translation.update(exclude_from_translation=True, exclusion_reason='Too Short').where(
            Translation.text_length < min_length, Translation.exclude_from_translation == 0)
        rows_touched = query.execute()

    logger.info(f"Excluded {rows_touched:,} short phrases.")


def exclude_repetitive_strings(min_variety: int):
    announce_status(f"Excluding strings below {min_variety}% character variety.")

    non_excluded_strings = Translation.select().where(Translation.exclude_from_translation == 0).count()
    logger.info(f'Reviewing {non_excluded_strings:,} strings.')

    exclusion_count = 0
    # Let's go through em all.
    stuff_to_review = Translation.select().where(Translation.exclude_from_translation == 0)
    with sqlite_db.atomic():
        for item in stuff_to_review:
            jap_text = item.extracted_text
            # Does the string have a variety of different characters?
            char_variety = calc_character_variety_percentage(jap_text)

            # Does the same character repeat a bunch?
            pattern = r'(.)\1{' + str(4) + r'}'
            repeats = re.search(pattern, jap_text) is not None

            exclude = False
            reason = ''
            if char_variety < min_variety:
                exclude = True
                reason = 'No character variety'
                logger.debug(f"Excluded: {char_variety:.0f}% -  {jap_text}")
                exclusion_count += 1
            elif repeats:
                exclude = True
                reason = 'Character repeats'
                logger.debug(f"Excluded due to repeats:-  {jap_text}")
                exclusion_count += 1

            if exclude:
                Translation.update(exclude_from_translation=True, exclusion_reason=reason).where(
                    Translation.extracted_text == item).execute()

    logger.info(f"Excluded {exclusion_count:,} strings.")


def calc_character_variety_percentage(input_string):
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


def exclude_not_japanese_enough_strings(min_jap_perc):
    announce_status(f"Excluding strings below {min_jap_perc}% Japanese characters from translation.")

    non_jap_count = Translation.select().where(Translation.exclude_from_translation == 0).count()
    logger.info(f'Reviewing {non_jap_count:,} strings.')

    exclusion_count = 0
    # Let's go through em all.
    stuff_to_review = Translation.select().where(Translation.exclude_from_translation == 0)
    with sqlite_db.atomic():
        for item in stuff_to_review:
            jap_perc = calc_japanese_percentage(item.extracted_text)
            if jap_perc < min_jap_perc:
                Translation.update(exclude_from_translation=True, exclusion_reason='Not Japanese Enough').where(
                    Translation.extracted_text == item).execute()
                logger.debug(f"Excluded: {jap_perc:.0f}% -  {item.extracted_text}")
                exclusion_count += 1

    logger.info(f"Excluded {exclusion_count:,} strings.")


def calc_japanese_percentage(input_string):
    """Calculate the percentage of Japanese characters in a string."""
    if not input_string:
        return 0  # Return 0% if the input string is empty or None

    total_chars = len(input_string)
    japanese_chars = sum(is_japanese(char) for char in input_string)

    return (japanese_chars / total_chars) * 100


def is_japanese(char):
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


def exclude_unfindable_strings(source_file, all_fields, translation_targets, errors, text_codec):
    # This function wants the RAW BYTES.
    # Not the decoded string.

    announce_status(f"Examining '{source_file}' to ensure extracted strings are present.")
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
