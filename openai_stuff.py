import os

import openai

import utils


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
                "content": f"Your job is to translate Japanese to English. If the translation is longer than {length} "
                           f"characters, paraphrase and abbreviate so that it is below {length}"
                           f"characters. You never provide responses longer than {length}. You do not comment about your"
                           f"tasks."
            },
            {
                "role": "user",
                "content": f"Shorten the string '{source}' to  {length} characters.",
            }
        ],
        model="gpt-3.5-turbo",
    )

    translated_string = response.choices[0].message.content.replace('\'', '')

    if len(translated_string) > length:
        translated_string = shorten_string(translated_string, length)

    return translated_string


def translate_file(input_file_path, output_file_path, dict_file_path):
    translation_targets = utils.read_file_sjis(input_file_path)
    translated_dict = {}

    text_codec = os.getenv("TEXT_CODEC")
    for text_bytes in translation_targets:
        text = text_bytes.decode(text_codec)
        # Translate the text!
        translation = translate_text(text)
        translated_dict[text] = translation

        print(f'Orig: {text}')
        print(f'Tran: {translation}')
        print()

    # Write dict file
    output_lines = []
    for key in translated_dict:
        output_lines.append(f';{key};{translated_dict[key]}'.encode(text_codec, errors='ignore'))

    utils.write_popnhax_dict(dict_file_path, output_lines)

    # Write a debug file
    with (open(output_file_path, 'w', encoding='utf-8') as translated_file):
        print('Writing translated file...')
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
