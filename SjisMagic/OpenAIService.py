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
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": ("Your job is to translate Japanese phrases from the rhythm game Pop'n Music into English. "
                            "\nProcess phrases using the following "
                            "steps:\n\n- If the Japanese is nonsensical, translate it as 'NNN'.\n- If the phrase is "
                            "meant to be parsed by a program, translate it as 'PPP'.\n- Otherwise translate it to "
                            "English. \n- Your translations should be as short as possible. Paraphrasing, "
                            "abbreviation, using incorrect spelling, and symbols are all ok. \n- Your translation "
                            "should not be longer than the Japanese phrase. Spaces and symbols count towards the "
                            "length.\n\nPlease return the translations as JSON in the following format:\n{ \n"
                            "translations:[\n    original:\"\"\n    translation:\"\"\n  ]\n}"
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
