import json
import logging
import os
from collections import defaultdict

import anthropic

logger = logging.getLogger('translation')
logger.setLevel(logging.INFO)


def translate(text: str) -> str:
    client = anthropic.Client(api_key=f"{os.environ['ANTHROPIC_API_KEY']}")

    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1500,
        temperature=0,
        system="Your job is to translate Japanese phrases from the rhythm game Pop'n Music into English. "
               "\nProcess phrases using the following "
               "steps:\n\n- If the Japanese is nonsensical, translate it as 'NNN'.\n- If the phrase is meant to be "
               "parsed by a program, translate it as 'PPP'.\n- Otherwise translate it to English. \n- Your "
               "translations should be as short as possible. Paraphrasing, abbreviation, using incorrect spelling, "
               "and symbols are all ok. \n- Your translation should not be longer than the Japanese phrase. Spaces "
               "and symbols count towards the length.\n\n\nPlease return the translations as JSON in the following "
               "format:\n{ \n  translations:[\n    original:\"\"\n    translation:\"\"\n  ]\n}",
        messages=[{

        }]
    )

    logger.debug(f"response: {message}")
    response_content = message.choices[0].message.content
    translated_string = json.loads(response_content)["response"]
    logger.debug(f"translated_string: {translated_string}")
    return translated_string


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
