import asyncio
import getopt
import os
import sys
from dotenv import load_dotenv
import extract_sjis
import file_cleanup
import google_trans

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

    load_dotenv()

    input_file_path, output_file_path = parse_args(argv)

    print('Beginning sjis extraction...')
    extract_file_path = f"{input_file_path}_sjis_dump.txt"
    if os.path.isfile(extract_file_path):
        print(f'Extract file already exists. Skipping extraction. File: {extract_file_path}')
    else:
        extract_sjis.extract_strings(input_file_path, extract_file_path)
    print(f'Complete! Extracted shift-jis to {extract_file_path}.\n\n')

    print('Remove anything we don\'t want to translate...')
    cleanup_file_path = f'{input_file_path}_sjis_dump_cleaned.txt'
    file_cleanup.cleanup_file(input_file_path, extract_file_path, cleanup_file_path)
    print('Complete!\n\n')

    quit()

    print('Translating japanese text via Google ...')
    trans_file_path = f'{input_file_path}_translated.txt'
    dict_file_path = f'{input_file_path}_dict.txt'
    if os.path.isfile(trans_file_path) and os.path.isfile(dict_file_path):
        print(f'Dictionary file already exists. Skipping creation. File: {trans_file_path}')
    else:
        google_trans.translate_text_google(cleanup_file_path, trans_file_path, dict_file_path)
    print('Complete!')


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


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
