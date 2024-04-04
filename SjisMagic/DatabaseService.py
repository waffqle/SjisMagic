import logging
import os
import time
from collections import defaultdict
from peewee import *
from peewee import SqliteDatabase
from utils import announce_status

logger = logging.getLogger('database')
logger.setLevel(logging.INFO)

database_folder = 'database'
database_name = 'sjisMagic.db'
database_path = f'sqlite:///../{database_folder}/{database_name}'

# Gonna need one of these!
sqlite_db = SqliteDatabase(database_path)


# Probably one of these too
class BaseModel(Model):
    class Meta:
        database = sqlite_db


class Translation(BaseModel):
    extracted_text = TextField(primary_key=True, default='')
    unicode_text = TextField(default='')
    english_translation = TextField(default='')
    english_shortened = TextField(default='')
    exclude_from_translation = IntegerField(default=False)
    exclusion_reason = TextField(default='')
    text_length = IntegerField(default=0)


def setup_db():
    # Create the db if it doesn't exist already
    if not os.path.exists(database_folder):
        logger.info('Creating database folder')
        os.makedirs(database_folder)
    logger.info(f'Connecting database: {database_path}')
    sqlite_db.connect()
    logger.info(f'Connected.')


def upsert_extracted_texts(texts):
    announce_status(f"Inserting {len(texts):,} translations")

    start_time = time.time()

    results = defaultdict(int)
    with sqlite_db.atomic():
        for text in texts:
            try:
                # Remove extra whitespace
                text = text.strip()

                if not text or text.isspace():
                    results['Whitespace'] += 1
                    continue  # Can't translate whitespace

                # Insert if it's not in here already
                upserted_tran = Translation.insert(extracted_text=text,
                                                   text_length=len(text)).on_conflict_ignore().execute()

                if upserted_tran:
                    results['New Phrase'] += 1
                    logger.debug(f'New phrase: {text}')
                else:
                    results['Already Exists'] += 1
                    logger.debug(f"Already inserted: {text}")
            except Exception as e:
                logger.error(f"Insert failed for '{text}'\n{type(e).__name__}: {e}")

    elapsed_time = time.time() - start_time
    for result in results.keys():
        logger.info(f"Result '{result}' count: {results[result]:,}")

    logger.info(f"Inserted {results['New Phrase']:,} new strings.")
    logger.info(f"Processed {len(texts):,} texts in {elapsed_time:,.2f} seconds.")
    logger.info(f"Rec/sec: {len(texts) / elapsed_time:,.0f} ")
