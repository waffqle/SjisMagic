import asyncio
import getopt
import os
import sys
import utils
import openai
from dotenv import load_dotenv
from google.cloud import translate_v3 as translate

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

    print('Converting extracted data into dictionary and dropping any invalid sjis strings...')
    japanese_texts: dict[str, str] = create_japanese_text_dict(dict_file_path)
    print('Complete!')
    print()

    print('Translating japanese text via Google ...')
    translate_text_google(japanese_texts, 'popntranslator', inputfilepath)

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

    with open(f'{dict_file_path}_deduped.txt', 'w', encoding='utf-8') as deduped_file:
        for japanese_text in japanese_texts:
            deduped_file.write(japanese_text)
            deduped_file.write('\n')

    return japanese_texts


def translate_text_google(texts, project_id, inputfilepath) -> translate.TranslationServiceClient:
    """Translating Text."""
    client = translate.TranslationServiceClient()
    location = "global"
    parent = f"projects/{project_id}/locations/{location}"

    with open(f'{inputfilepath}_translated.txt', 'w', encoding='utf-8') as translated_file:
        for text in texts:
            response = client.translate_text(text, 'en', parent, '', 'ja')

            translated_text = ''
            for translation in response.translations:
                translated_text += translation.translated_text

            print(f'Orig: {text}')
            print(f'Tran: {translated_text}')
            print()

            translated_file.write(f'Orig: "{text}" Trans: "{translated_text}"\n')


def translate_text_gpt(texts: dict[str, str]) -> None:
    client = openai.OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    for text in texts:
        if text.__len__() < 40:
            continue

        print(f'Translating {text}...')
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a translator for Japanese text to English. You only return translated text. If "
                               "you cannot translate a piece of text, you return the original text."
                },
                {
                    "role": "user",
                    "content": f"Translate '{text}' to English. Do not return more characters than there are in the "
                               f"source text. Only return the translated text. Your translations will never be longer"
                               f" than the original text.",
                }
            ],
            model="gpt-3.5-turbo",
        )

        translation = response.choices[0].message.content.replace('\'', '')
        print(f'Translation: {translation}')


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
