import re

import unicodedata


def calc_japaneseness(text):
    total_chars = len(text)
    japanese_chars = 0
    for char in text:
        if unicodedata.name(char, '').startswith(('CJK UNIFIED IDEOGRAPH', 'HIRAGANA', 'KATAKANA')):
            japanese_chars += 1
    percentage = (japanese_chars / total_chars) * 100
    return percentage


def contains_chinese(text):
    pattern = re.compile(r'[\u4e00-\u9fff]')
    return bool(pattern.search(text))
