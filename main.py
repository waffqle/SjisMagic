import asyncio
import getopt
import os
import pathlib
import sys
from typing import Dict, Any

import utils
import openai
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate

import extract_sjis


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

    inputfilepath, outputfilepath = parse_args(argv)

    print('Beginning sjis extraction...')
    dict_file_path = extract_sjis.extract_strings(inputfilepath)
    print(f'Complete! Extracted shift-jis to {dict_file_path}.')
    print()

    print('Converting extracted data into dictionary and dropping anything we don\'t want to translate...')
    japanese_texts: dict[str, str] = create_japanese_text_dict(dict_file_path)
    print('Complete!')
    print()

    print('Translating japanese text via Google ...')
    translated_text = translate_text_google(japanese_texts, 'popntranslator', inputfilepath)
    print('Complete!')
    print()

    print('Use GPT to paraphrase strings that are too long...')
    shortened_text = shorten_text_gpt(translated_text)
    print('Complete!')

    print('Writing final dict file...')
    dictpath = inputfilepath.replace('.dll', '.dict')
    creat_dict_file(shortened_text, dictpath)
    print('Complete!')
    quit()


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


def create_japanese_text_dict(dict_file_path):
    """
    Read the file created by the extract_sjis module and convert it into a dictionary. Any invalid sjis strings will be
    dropped. Stings that are note purely katakana/hiragana will be also dropped.

    :param dict_file_path: Path to dict file
    :return: Dictionary of all sjis strings, keyed by address.
    """
    # Read the whole input file.
    # Split it on semicolons
    with open(dict_file_path, 'rb') as dict_file:
        file_contents = dict_file.read()
        all_fields = file_contents.split(b';;;')

    # Delete any trailing new lines
    last_field = all_fields[-1]
    if last_field == '' or last_field == b'\n':
        all_fields.remove(all_fields[-1])

    print(f'Found {len(all_fields)} fields in {dict_file_path}')
    print()

    # Create a dict of translation targets.
    parsing_errors = 0
    duplicates = 0
    non_translatable_strings = 0
    japanese_texts = {}
    for i in range(0, len(all_fields), 2):
        try:
            # Parse into a variable first, so we don't get empty dict entries on failures
            sjis_text = all_fields[i + 1].decode('sjis')

            if japanese_texts.__contains__(sjis_text):
                duplicates += 1
                continue

            if not utils.string_is_translation_target(sjis_text):
                non_translatable_strings += 1
                continue

            japanese_texts[sjis_text] = ''  # We'll put translations in here later!
        except UnicodeDecodeError as e:
            # print(f'Parsing error. We expect a few of these. Error: {e}')
            parsing_errors += 1
        except Exception as e:
            print(f'Unexpected parsing issue: {e.__class__.__name__}: {e}')

    print(f'Parsing errors: {parsing_errors}. (We expect some of these. Sjis detection is inherently troublesome.)')
    print(f'Found {non_translatable_strings} non-translatable strings.')
    print(f'Found {duplicates} duplicate strings.')
    print(f'File contains {japanese_texts.__len__()} unique, valid sjis strings that we actually want to translate.')

    # Dump the dict to a file.
    # Don't really need this, just handy for review/debug
    with open(f'{dict_file_path}_deduped.txt', 'w', encoding='utf-8') as deduped_file:
        for japanese_text in japanese_texts:
            deduped_file.write(f'{japanese_text}\n')

    return japanese_texts


def translate_text_google(texts, project_id, inputfilepath) -> dict[str, str]:
    """Translating Text."""
    client = translate.Client()

    translated_dict = {}

    with (open(f'{inputfilepath}_translated.txt', 'w', encoding='utf-8') as translated_file):
        for text in texts:
            if len(translated_dict) > 100:
                return translated_dict  # Save money when debugging

            response = client.translate(text, target_language='en', source_language='ja')

            translated_dict[text] = response['translatedText']

            print(f'Orig: {response['input']}')
            print(f'Tran: {response['translatedText']}')
            print()

            translated_file.write(f'Orig: "{text}" Trans: "{response['translatedText']}"\n')

    return translated_dict


def shorten_text_gpt(translated_texts: dict[str, str]) -> dict[str, str]:
    """
    Shorten a string to make it the same size as the original string.
    :param translated_texts: Dictionary[japaneseText, translatedText]
    :return: Same dictionary with shortened translated texts
    """
    client = openai.OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    for key in translated_texts:
        # If the translated text is longer than the original, ask gpt to shorten the string.
        if len(translated_texts[key]) <= len(key):
            print(f'String "{translated_texts[key]}" is ok as-is.')
            continue

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
                    "content": f"Shorten the string '{translated_texts[key]}' to  {len(key)} characters.",
                }
            ],
            model="gpt-3.5-turbo",
        )

        shortened_string = response.choices[0].message.content.replace('\'', '')
        print(f'Original:  {translated_texts[key]}')
        print(f'Shortened: {shortened_string}')

        translated_texts[key] = shortened_string

    return translated_texts


def creat_dict_file(dictionary, file_path):
    with (open(f'{file_path}', 'w', encoding='sjis') as dict_file):
        for text in dictionary:
            try:
                dict_file.write(f';{text};{dictionary[text]}\n')
            except Exception as e:
                print(f'Encoding error: {e}')
        dict_file.write(';')
        dict_file.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
