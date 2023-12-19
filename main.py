import asyncio
import getopt
import os
import sys

import openai
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate

import extract_sjis
import utils

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

    input_file_path, outputfilepath = parse_args(argv)

    print('Beginning sjis extraction...')
    extract_file_path = f"{input_file_path}_sjis_dump.txt"
    if os.path.isfile(extract_file_path):
        print(f'Extract file already exists. Skipping extraction. File: {extract_file_path}')
    else:
        extract_sjis.extract_strings(input_file_path, extract_file_path)
    print(f'Complete! Extracted shift-jis to {extract_file_path}.\n\n')

    print('Remove anything we don\'t want to translate...')
    cleanup_file_path = f'{input_file_path}_sjis_dump_cleaned.txt'
    if os.path.isfile(cleanup_file_path):
        print(f'Clean file already exists. Skipping creation. File: {cleanup_file_path}')
    else:
        extract_sjis.cleanup_file(extract_file_path, cleanup_file_path)
    print('Complete!\n\n')

    print('Making sure translation targets exist in original file. i.e., We didn\'t fuck up the strings.')
    utils.check_file_contains_bytes(cleanup_file_path, input_file_path)

    print('Translating japanese text via Google ...')
    trans_file_path = f'{input_file_path}_translated.txt'
    dict_file_path = f'{input_file_path}_dict.txt'
    if os.path.isfile(trans_file_path) and os.path.isfile(dict_file_path):
        print(f'Dictionary file already exists. Skipping creation. File: {trans_file_path}')
    else:
        translate_text_google(cleanup_file_path, trans_file_path, dict_file_path)
    print('Complete!')


def parse_args(argv):
    # Retrieve our arguments
    opts, args = getopt.getopt(argv, "i:o:", ["inputFile=", "outputFile="])
    # Parse out the file names
    inputfilepath = ""
    outputfilepath = ""
    for opt, arg in opts:
        if opt in ("-i", "--inputFile"):
            inputfilepath = arg
        elif opt in ("-o", "--outputFile"):
            outputfilepath = arg
    outputfilepath = outputfilepath if outputfilepath else inputfilepath + "_translated.dict"
    return inputfilepath, outputfilepath


def translate_text_google(input_file_path, output_file_path, dict_file_path) -> dict[str, str]:
    """Translating Text."""
    client = translate.Client()

    translated_dict = {}

    translation_targets = utils.read_file_sjis(input_file_path)

    for text_bytes in translation_targets:
        text = text_bytes.decode('sjis')
        # Translate the text!
        response = client.translate(text, target_language='en', source_language='ja')
        translation = response['translatedText']

        # If the translated text is longer than the original, paraphrase it
        shortened_text = ''
        if len(translation) > len(text):
            shortened_text = shorten_text_gpt(translation, len(text))

        translated_dict[text] = translation if not shortened_text else shortened_text

        print(f'Orig: {text}')
        print(f'Tran: {translation}')
        if shortened_text:
            print(f'Shortened: {shortened_text}')
        print()

    # Write dict file
    output_lines = []
    for key in translated_dict:
        output_lines.append(f';{key};{translated_dict[key]}')

    utils.write_file_sjis(dict_file_path, output_lines)

    # Write a debug file
    with (open(output_file_path, 'w', encoding='sjis') as translated_file):
        print('Writing translated file...')
        for key in translated_dict:
            translated_file.write(f'Orig: {key}\n')
            translated_file.write(f'Translated: {translated_dict[key]}\n')
            translated_file.write('\n')
        translated_file.close()


def shorten_text_gpt(source: str, length: int) -> str:
    """
    Shorten a string to make it the same size as the original string.
    :param source: Text to shorten
    :param length: Length of the shortened string
    :return: Shortened text
    """
    client = openai.OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "Your job is to shorten strings. You only return shortened strings. If you can not "
                           "shorten the string, you only return the original string. You never make additional "
                           "comments."
            },
            {
                "role": "user",
                "content": f"Shorten the string '{source}' to  {length} characters.",
            }
        ],
        model="gpt-3.5-turbo",
    )

    shortened_string = response.choices[0].message.content.replace('\'', '')
    return shortened_string


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
