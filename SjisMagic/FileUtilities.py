import logging

from SjisMagic.DatabaseService import Translation

logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)


def check_file_contains_bytes(search_bytes, source_file_path):
    # Make sure it all exits in the source file
    with open(source_file_path, 'rb') as f:
        contents = f.read()

    if contents.find(search_bytes) == -1:
        return False
    else:
        return True


def write_popnhax_dict(output_file_path):
    # Find everything we translated and didn't exclude.
    list_of_items = Translation.select().where(Translation.exclude_from_translation == 0,
                                               Translation.translation != '')

    logger.info(f'Exporting {list_of_items.count()} dictionary items.')
    outputfile = open(output_file_path, "w", encoding='shift_jisx0213')
    for trans in list_of_items:
        line = f';{trans.extracted_text};{trans.translation}\n'
        try:
            outputfile.write(line)
        except Exception as e:
            logger.warning(f'Error writing dict. Error: {e}\nLine: {line}')
