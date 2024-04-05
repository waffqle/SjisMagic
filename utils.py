import logging
from enum import Enum

# Let's setup some logging!
logger = logging.getLogger('status')
logger.setLevel(logging.INFO)


def announce_status(status: str):
    length = len(status) + 7
    logger.info('')
    logger.info('*'.ljust(length, '*'))
    logger.info(f'*  {status.capitalize()}!  *')
    logger.info(''.ljust(length, '*'))
