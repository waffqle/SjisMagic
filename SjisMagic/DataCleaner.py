from enum import Enum

from SjisMagic import OpenAIService, AnthropicService
from SjisMagic.DatabaseService import *

logger = logging.getLogger('cleanup')
logger.setLevel(logging.INFO)


class Brain(Enum):
    ChatGPT = 1
    Claude = 2


def exclude_too_short_strings(min_length: int):
    announce_status(f"Excluding strings below {min_length} from translation.")

    with sqlite_db.atomic():
        query = Translation.update(exclude_from_translation=True, exclusion_reason='Too Short').where(
            Translation.text_length < min_length, Translation.exclude_from_translation is False)
        rows_touched = query.execute()
    logger.info(f"Excluded {rows_touched:,} short phrases.")


def exclude_garbage_strings():
    """
    Go through the DB and apply misc exclusions. Lots of hand-tweaked
    stuff in here.
    """
    pass


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


def translate_strings():
    """
    Search the DB for untranslated strings and go to work on em. Commits in batches so work doesn't get lost.
    """
    # Is there anything to translate?
    translatables = Translation.select().where(Translation.english_translation == '',
                                               Translation.exclude_from_translation is False)
    # Let's go!
    for translatable in translatables.iterator():
        translatable.english_translation = translate(translatable.extracted_text, Brain.ChatGPT)
        logger.info(f"Translated '{translatable.extracted_text}' to '{translatable.english_translation}")


def translate(text: str, brain) -> str:
    if brain == Brain.ChatGPT:
        return OpenAIService.translate(text)
    elif brain == Brain.Claude:
        return AnthropicService.translate(text)
    else:
        return 'Fart Fart Fart'


def cull_translations(translation_dic: dict):
    logger.debug(f"Culling translations: {translation_dic}")

    unwanted_things = {'NNN', 'PPP', 'CCC'}  # better membership test than list

    keys_to_remove = [key for key, value in translation_dic.items() if value in unwanted_things]
    for key in keys_to_remove:
        del translation_dic[key]

    logger.debug(f"Culled: {translation_dic}")
    return translation_dic
