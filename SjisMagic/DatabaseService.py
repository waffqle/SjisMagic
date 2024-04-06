import logging
import os
from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase
from playhouse.hybrid import *

from utils import announce_status

logger = logging.getLogger('database')
logger.setLevel(logging.INFO)

database_folder = 'database'
database_name = 'sjisMagic.db'
database_path = f'sqlite:///../{database_folder}/{database_name}'

# Gonna need one of these!
sqlite_db = SqliteExtDatabase(database_path)


# Probably one of these too
class BaseModel(Model):
    class Meta:
        database = sqlite_db


class Translation(BaseModel):
    extracted_text = TextField(primary_key=True, default='')
    unicode_text = TextField(default='')
    openai_translation = TextField(default='')
    anthropic_translation = TextField(default='')
    google_translation = TextField(default='')
    best_translation = TextField(default='')
    shortened_translation = TextField(default='')
    exclude_from_translation = IntegerField(default=False)
    exclusion_reason = TextField(default='')
    text_length = IntegerField(default=0)

    @hybrid_property
    def untranslated(self):
        return self.openai_translation == '' or self.anthropic_translation == '' or self.google_translation == ''


def setup_db():
    # Create the db if it doesn't exist already
    if not os.path.exists(database_folder):
        logger.info('Creating database folder')
        os.makedirs(database_folder)
    logger.info(f'Connecting database: {database_path}')
    sqlite_db.connect()
    logger.info(f'Connected.')
    sqlite_db.create_tables([Translation])
    logger.info(f'Created tables.')
