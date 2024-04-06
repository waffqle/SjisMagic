import json
import logging
import os

import openai

logger = logging.getLogger('openAI')
logger.setLevel(logging.INFO)


def translate(text) -> str:
    length = len(text)
    client = openai.OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {
                "role": "system",
                "content": ('Your job is to translate Japanese phrases from the rhythm game Pop\'n Music into '
                            'English. You will receive lists of phrases that should be individually translated.\n'
                            '\n'
                            'Process them using the following steps:\n'
                            '- If the Japanese is nonsensical, translate it as \'NNN\'.\n'
                            '- If the phrase is intended to be parsed by a program rather than read by a human, '
                            'translate it as \'PPP\'.\n'
                            '- If the phrase contains Chinese characters, translate it as \'CCC\'.\n'
                            f'- Otherwise translate it to English. The translation must not be more than {length} '
                            f'characters, including spaces. Paraphrasing, abbreviation, symbols, emoji, and modified '
                            f'spelling are all acceptable. Removing letters is also acceptable. '
                            f'\n'
                            'Think step by step. \n'
                            '\n'
                            'Please return the translations as JSON in the following format:\n'
                            '{ translations:[ original:"" translation:""]}'
                            )
            },
            {
                "role": "user",
                "content": f'Translate "{text}". Do not use more than {len(text)} characters.'
            }

        ],

        response_format={"type": "json_object"}
    )

    response_content = response.choices[0].message.content
    logger.debug(f'Response content: {response_content}')

    translated_string = json.loads(response_content)["translations"][0]["translation"]
    logger.debug(f"Parsed JSON: {translated_string}")

    return translated_string
