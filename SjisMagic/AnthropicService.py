import json
import logging
import os
from SjisMagic import FileUtilities
from collections import defaultdict

import anthropic

logger = logging.getLogger('translation')
logger.setLevel(logging.INFO)


def translate_file(input_file_path, output_file_path, dict_file_path):
    text_codec = os.getenv('TEXT_CODEC')

    translation_targets = FileUtilities.read_file_sjis(input_file_path)
    translation_targets = [x.decode(text_codec) for x in translation_targets]
    translated_dict = {}

    text_codec = os.getenv("TEXT_CODEC")

    # Claude is good at handling big chunks of data. So we'll send it in that way.
    chunk_size = 10
    jap_text_chunks = [translation_targets[x:x + chunk_size] for x in range(0, len(translation_targets), chunk_size)]

    logger.info(f"Split {len(translation_targets)} into {len(jap_text_chunks)} sub-lists.")

    # Track how far along we are
    i = 0

    for text_chunk in jap_text_chunks:
        try:
            i += 1
            logger.info(f"Translating chunk {i} of {len(jap_text_chunks)}...")
            # Translate the texts!
            translated_chunk = translate_text_list(text_chunk)

            # Accumulate in the main dictionary.
            translated_dict.update(translated_chunk)

        except Exception as e:
            logger.error(f"Couldn't translate: {text_chunk}")
            logger.error(f"{e}")

    # Write dict file
    output_lines = []
    for key in translated_dict:
        output_lines.append(f';{key};{translated_dict[key]}'.encode(text_codec, errors='ignore'))

    FileUtilities.write_popnhax_dict(dict_file_path, output_lines)
    logger.info(f'Writing translated file: {dict_file_path}')

    # Write a debug file
    with (open(output_file_path, 'w', encoding='utf-8') as translated_file):
        for key in translated_dict:
            translated_file.write(f'Orig: {key}\n')
            translated_file.write(f'Translated: {translated_dict[key]}\n')
            translated_file.write('\n')
        translated_file.close()


def translate_text_list(fields):
    client = anthropic.Client(api_key=f"{os.environ['ANTHROPIC_API_KEY']}")

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        system='''\
Your job is to translate Japanese phrases from the rhythm game Pop'n Music into English. You will receive lists of phrases that should be individually translated.

Process them using the following steps:

- Count the number of characters in the Japanese phrase.
- If the Japanese is nonsensical translate it as 'NNN'.
- If the phrase is intended to be parsed by a program rather than read by a human translate it as 'PPP'
- If the phrase contains Chinese characters, translate it as 'CCC'
- Otherwise translate it to English, succinctly as possible.
- If the English phrase is longer than the Japanese one, shorten it via paraphrasing, abbreviation, and other methods.
- Compare the length of the shortened English phrase to the original Japanese phrase.
- If the English phrase is still longer than the Japanese, remove letters from it.

Please return JSON in the following format:
{ 
  translations:[
    original:""
    translation:""
  ]
}
''',
        messages=[
            {"role": "user", "content": f"{fields}"},
            {"role": "assistant", "content": "{}"},
            {"role": "user", "content": "Review your response and shorten any translations that are longer than the "
                                        "original text. Removing letters, incorrect spelling, paraphrasing, and "
                                        "abbreviation is ok."}
        ]
    )

    response_text = response.content[0].text

    translation_dic = parse_response_to_dic(response_text)

    translation_dic = cull_translations(translation_dic)

    return translation_dic


def parse_response_to_dic(response_text):
    # Parse the json we received into a dictionary
    json_array = json.loads(response_text)
    translation_dic = defaultdict()

    for item in json_array["translations"]:
        original = item["original"]
        translation = item["translation"]
        translation_dic[original] = translation

    logger.debug(f"Translated: {translation_dic}")
    return translation_dic


def cull_translations(translation_dic: dict):
    logger.debug(f"Culling translations: {translation_dic}")

    unwanted_things = {'NNN', 'PPP', 'CCC'}  # better membership test than list

    keys_to_remove = [key for key, value in translation_dic.items() if value in unwanted_things]
    for key in keys_to_remove:
        del translation_dic[key]

    logger.debug(f"Culled: {translation_dic}")
    return translation_dic
