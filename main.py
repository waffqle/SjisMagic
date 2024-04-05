import asyncio
import getopt
import os
import sys
from dotenv import load_dotenv
from SjisMagic import SjisExtractor, DataCleaner, AnthropicService, DatabaseService
import logging
from utils import announce_status

# Let's setup some logging!
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)


async def main(argv):
    """
    Extract shift-jis strings from a file. (Like a dll from your favorite Japanese rhythm game...) Export a dictionary
    of what we find. Translate the sjis strings via GPT. Invalid sjis strings will be dropped
    from the final file. Final result is a popnhax compatible translation file!

    NOTE: This uses the OpenAI API. This is a paid service, You'll need an account, and it will cost a little money.
    (If you translate enough to use up the free monthly allocation.) https://platform.openai.com/

    :param argv: -i Path to input file, -o Path for output file. (opt)
    """

    # Let's get things setup
    setup_logging()
    load_dotenv()
    DatabaseService.setup_db()

    # Fetch our params
    text_codec = os.getenv("TEXT_CODEC")
    input_file_path, output_file_path = parse_args(argv)

    # Ok. Time to get to work
    announce_status('Starting up')
    logger.info(f"Extracting: {input_file_path}")
    logger.info(f"Creating:   {output_file_path}")
    logger.info(f'Codec: {text_codec}')

    # Extract strings from binary
    SjisExtractor.extract_strings(input_file_path, text_codec)

    # Clean out stuff we don't want to translate
    DataCleaner.exclude_too_short_strings(min_length=4)

    logger.info('Translating japanese text ...')
    dict_file_path = f'{input_file_path.replace('.dll', '.dict')}'
    DataCleaner.translate_strings()
    logger.info('Complete!')


def parse_args(argv):
    # Retrieve our arguments
    opts, args = getopt.getopt(argv, "i:o:", ["inputFile=", "outputFile="])

    # Parse out the file names
    input_file_path = ""
    output_file_path = ""
    for opt, arg in opts:
        if opt in ("-i", "--inputFile"):
            input_file_path = arg
        elif opt in ("-o", "--outputFile"):
            output_file_path = arg
    output_file_path = output_file_path if output_file_path else input_file_path + "_translated.dict"
    return input_file_path, output_file_path


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
    asyncio.run(main(sys.argv[1:]))
