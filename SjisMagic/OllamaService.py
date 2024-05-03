import json
import logging
import ollama

logger = logging.getLogger('ollama')
logger.setLevel(logging.INFO)


def translate(text) -> str:
    length = len(text)
    response = ollama.generate(model="llama3:instruct.",
                               system="Translate Japanese text to English. Do not respond conversationally. If it can't"
                                      f"be translated, respond 'XXX'. Try to provide a response with less than {length} "
                                      f"characters.",
                               prompt=f"{text}")

    logger.debug(f'Response content: {response}')

    translation = response['response']

    logger.debug(f"Translation: {translation}")

    return translation
