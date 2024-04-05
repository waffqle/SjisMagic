import json
import logging
import os

import openai

logger = logging.getLogger('translation')
logger.setLevel(logging.INFO)


def translate(text):
    length = len(text)
    client = openai.OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    response = client.chat.completions.create(
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
                            '- Otherwise translate it to English. Make the translation extremely short. Paraphrasing, '
                            'abbreviation, symbols, emoji, and modified spelling are all acceptable. Removing letters '
                            'is also acceptable. \n'
                            '- The translation cannot be longer than the Japanese phrase. Spaces and symbols count.'
                            '\n'
                            'Think step by step. \n'
                            '\n'
                            'Please return the translations as JSON in the following format:\n'
                            '{ translations:[ original:"" translation:""]}'
                            )

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
