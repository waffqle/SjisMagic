import json
import logging
import os

import openai

logger = logging.getLogger('translation')
logger.setLevel(logging.INFO)


def shorten_string(text, target_length):
    shortened_text = ''
    if len(text) > target_length:
        shortened_text = shorten_text(text, target_length)
    return shortened_text


def translate_text(source: str) -> str:
    """
    Translate a string and make it the same size as the original string.
    :param source: Text to shorten
    :return: Shortened text
    """
    length = len(source)

    client = openai.OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"Your job is to translate {source} to English. If the string is not definitely a "
                           f"sensical Japanese phrase provide an empty response. If the translation is longer than {length} "
                           f"characters, paraphrase and abbreviate so that it is below {length}"
                           f"characters. Translations should never be longer than {length}."
                           f"Return a JSON object with the following structure:"
                           "{response: ''}"

            }
        ],
        model="gpt-3.5-turbo",
        response_format={"type": "json_object"}
    )

    logger.debug(f"response: {response}")

    response_content = response.choices[0].message.content

    translated_string = json.loads(response_content)["response"]
    logger.debug(f"translated_string: {translated_string}")

    return translated_string

    if len(translated_string) > length:
        translated_string = shorten_string(translated_string, length)

    return translated_string


def translate_file(input_file_path, output_file_path, dict_file_path):
    translation_targets = utils.read_file_sjis(input_file_path)
    translated_dict = {}

    text_codec = os.getenv("TEXT_CODEC")
    for jap_text in [x.decode(text_codec) for x in translation_targets]:
        if len(jap_text) < 1:
            continue

        try:
            # Translate the text!
            translation = translate_text(jap_text)

            if translation or translation.strip():
                translated_dict[jap_text] = translation
                logger.info(f'Orig: "{jap_text}"')
                logger.info(f'Tran: "{translation}"')
            else:
                logger.info(f'Untranslatable: {jap_text}')
        except Exception as e:
            logger.error(f"Couldn't translate: {jap_text}")
            logger.error(f"{e}")

    # Write dict file
    output_lines = []
    for key in translated_dict:
        output_lines.append(f';{key};{translated_dict[key]}'.encode(text_codec, errors='ignore'))

    utils.write_popnhax_dict(dict_file_path, output_lines)
    logger.info(f'Writing translated file: {dict_file_path}')

    # Write a debug file
    with (open(output_file_path, 'w', encoding='utf-8') as translated_file):
        for key in translated_dict:
            translated_file.write(f'Orig: {key}\n')
            translated_file.write(f'Translated: {translated_dict[key]}\n')
            translated_file.write('\n')
        translated_file.close()


def shorten_text(source: str, length: int) -> str:
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
                           "comments. You can abbreviate or rephrase the text if needed. You can also remove letters "
                           "from words if you need to. You do not comment on your tasks."
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
