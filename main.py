import asyncio
import getopt
import os
import sys
from dotenv import load_dotenv
import extract_sjis
import file_cleanup
import logging
import openai_stuff

# Let's setup some logging!
main_log = logging.getLogger('main')
main_log.setLevel(logging.INFO)

# Set this to a value and we'll only process that many rows. (Makes debugging faster/cheaper.)
only_process_first_rows = 0


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
    text_codec = os.getenv("TEXT_CODEC")
    input_file_path, output_file_path = parse_args(argv)

    # Ok. Time to get to work.
    extract_file_path = f"{input_file_path}_dump.txt"
    main_log.info(f'Input file:  {input_file_path}')
    main_log.info(f'Output file: {output_file_path}')
    main_log.info(f'Codec: {text_codec}')

    extract_sjis.extract_strings(input_file_path, extract_file_path, text_codec)
    main_log.debug(f'Extracted to: {extract_file_path}')

    cleanup_file_path = f'{input_file_path}_dump_cleaned.txt'
    file_cleanup.cleanup_file(input_file_path, extract_file_path, cleanup_file_path)
    main_log.debug(f"File: {cleanup_file_path}")

    return

    main_log.info('Translating japanese text ...')
    trans_file_path = f'{input_file_path}_translated.txt'
    dict_file_path = f'{input_file_path.replace('.dll', '.dict')}'
    if os.path.isfile(trans_file_path) and os.path.isfile(dict_file_path):
        main_log.info(f'Dictionary file already exists. Skipping creation. File: {trans_file_path}')
    else:
        openai_stuff.translate_file(cleanup_file_path, trans_file_path, dict_file_path)
    main_log.info('Complete!')


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
    log_formatter = logging.Formatter(fmt="{levelname:<7}| {message}", style="{")
    root_logger = logging.getLogger()
    file_handler = logging.FileHandler("sjismagic.log")
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
