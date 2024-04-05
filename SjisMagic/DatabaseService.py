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



