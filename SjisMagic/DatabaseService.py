import logging
import os
from collections import defaultdict

from pony.orm import *
import sqlite3

logger = logging.getLogger('database')
logger.setLevel(logging.INFO)

database_folder = 'database'
database_name = 'sjisMagic.db'
database_path = f'../{database_folder}/{database_name}'

# Gonna need one of these!
db = Database()


# Probably one of these too
class Translation(db.Entity):
    extracted_text = PrimaryKey(str)
    unicode_text = Optional(str, default='')
    english_translation = Optional(str, default='')
    english_shortened = Optional(str, default='')
    exclude_from_translation = Optional(int, default=False)
    exclusion_reason = Optional(str, default='')

    @property
    def text_length(self) -> int:
        return len(self.extracted_text)


def setup_db():
    # Create the db if it doesn't exist already
    if not os.path.exists(database_folder):
        logger.info('Creating database folder')
        os.makedirs(database_folder)
    logger.info(f"Binding database: '{database_path}'")
    db.bind(provider='sqlite', filename=f'{database_path}', create_db=True)
    logger.info(f'Connected to database: {database_name}')
    db.generate_mapping(create_tables=True)
    logger.debug('ORM mapping complete')


@db_session
def upsert_extracted_texts(texts):
    return
    logger.info(f"Inserting {len(texts)} translations")

    results = defaultdict(int)

    for text in texts:
        try:
            if text.isspace():
                results['Whitespace'] += 1
                continue  # Can't translate whitespace

            logger.debug(f"Inserting: {text}")
            transaction = Translation.get(extracted_text=text)
            if transaction is None:
                results['New Phrase'] += 1
                transaction = Translation(extracted_text=text)
            else:
                results['Already Exists'] += 1
                logger.debug(f"Already inserted: {text}")
        except Exception as e:
            logger.error(f"DB insert failed for '{text}'\n{type(e).__name__}: {e}")

    for result in results.keys():
        logger.info(f"Result '{result}' count: {results[result]}")

    commit()


def count_excluded_rows_by_reason(reason: str) -> int:
    pass


def count_translation_candidates() -> int:
    pass
