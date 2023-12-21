from google.cloud import translate_v2 as translate
import utils
from openai_stuff import shorten_string


def translate_text_google(input_file_path, output_file_path, dict_file_path):
    translated_dict = {}

    translation_targets = utils.read_file_sjis(input_file_path)

    for text_bytes in translation_targets:
        text = text_bytes.decode('sjis')
        # Translate the text!
        translation = translate_ja_to_en(text)

        # If the translated text is longer than the original, paraphrase it
        shortened_text = shorten_string(translation, len(text))

        translated_dict[text] = translation if not shortened_text else shortened_text

        print(f'Orig: {text}')
        print(f'Tran: {translation}')
        if shortened_text:
            print(f'Shortened: {shortened_text}')
        print()

    # Write dict file
    output_lines = []
    for key in translated_dict:
        output_lines.append(f';{key};{translated_dict[key]}'.encode('sjis'))

    utils.write_popnhax_dict(dict_file_path, output_lines)

    # Write a debug file
    with (open(output_file_path, 'w', encoding='sjis') as translated_file):
        print('Writing translated file...')
        for key in translated_dict:
            translated_file.write(f'Orig: {key}\n')
            translated_file.write(f'Translated: {translated_dict[key]}\n')
            translated_file.write('\n')
        translated_file.close()


def translate_ja_to_en(text):
    client = translate.Client()
    response = client.translate(text, target_language='en', source_language='ja')
    translation = response['translatedText']
    return translation
