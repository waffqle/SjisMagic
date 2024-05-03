import asyncio
import logging
import functools
import sys

from decouple import config

from SjisMagic import DataProcessorService, DatabaseService, SjisExtractor, FileUtilities

from utils import announce_status

# Let's setup some logging!
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)


async def main():
    """
    Extract shift-jis strings from a file. (Like a dll from your favorite Japanese rhythm game...) Export a dictionary
    of what we find. Translate the sjis strings via AI. Invalid sjis strings will be dropped
    from the final file. Final result is a popnhax compatible translation file!

    NOTE: This uses the Anthropic, Google, and/or, OpenAI APIs. (Usage is optional) This is a paid service,
    You'll need an account, and it will cost a little money. Ollama is free, just make sure you've got it running.
    """

    # Let's get things setup
    setup_logging()
    DatabaseService.setup_db()

    # Fetch our params
    input_file_path, output_file_path, text_codec = await fetch_settings()
    logger.info(f"Extracting: {input_file_path}")
    logger.info(f"Creating:   {output_file_path}")
    logger.info(f'Codec: {text_codec}')

    # Ok. Time to get to work
    announce_status('Starting up')

    # Extract strings from binary
    extract = False
    if not extract:
        announce_status('Skipping extraction')
    else:
        SjisExtractor.extract_strings(input_file_path, text_codec)

    # Exclude stuff we don't want to translate
    # All validations skip items that are already excluded. So do the slowest things last.
    DataProcessorService.exclude_strings("Not Japanese Enough",
                                         functools.partial(DataProcessorService.is_string_japanese_enough,
                                                           min_jap_perc=50))

    DataProcessorService.exclude_strings("Not Variant Enough",
                                         functools.partial(DataProcessorService.is_string_variant_enough,
                                                           min_variety=50))

    DataProcessorService.exclude_strings("Too Many Repeating Chars",
                                         functools.partial(DataProcessorService.is_string_nonrepeating,
                                                           repetition_limit=5))

    DataProcessorService.exclude_strings("Too Short",
                                         functools.partial(DataProcessorService.is_string_long_enough, min_length=3))

    # DataProcessorService.exclude_strings("Half Width Latin Chars",
    #                                     functools.partial(DataProcessorService.are_latin_chars_fullwidth))

    # This takes way longer than our other validations. Make sure to do it last.
    # exclude_unfindable_strings(input_file_path, text_codec)

    # Pop'n doesn't like half width latin chars.
    # DataProcessorService.convert_everythings_width("standard")

    # How many things are we actually gonna spend money/time on?
    announce_status(f'{DatabaseService.get_untranslated_items_count():,} phrases left to translate')

    # We work in batches for performance
    await DataProcessorService.crank_up_translation_machine(10)

    logger.info('Translation Complete!')

    logger.info('Exporting .dict file...')
    FileUtilities.write_popnhax_dict(output_file_path)
    logger.info('All done!')


async def fetch_settings():
    text_codec = config('TEXT_CODEC', default='shift_jisx0213')
    input_file_path = config('INPUT_FILE_PATH', default='working/popn22.dll')
    output_file_path = config('OUTPUT_FILE_PATH', default='working/popn22.dict')
    return input_file_path, output_file_path, text_codec


def setup_logging():
    log_formatter = logging.Formatter(fmt="{levelname:<7}| {name} | {message}", style="{")
    root_logger = logging.getLogger()
    # Logger won't write our fancy characters if we don't give it a robust encoding.
    file_handler = logging.FileHandler("sjismagic.log", encoding="utf-8", mode="w+")
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


if __name__ == "__main__":
    asyncio.run(main())
