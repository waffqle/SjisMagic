debug = False


def char_is_japanese(c) -> bool:
    """
    Determine if a character is Japanese text. (Or at least, something that should be translated)
    :param c: Character to check
    :return: Japanese-ness
    """
    translatable = is_char_hiragana(c) or is_char_katakana(c) or is_char_chinese(c) or is_char_otherjap(
        c) or is_char_cjk(c)

    if debug:
        print(f'{c} is {c.encode('unicode-escape')} Translatable: {translatable}')

    return translatable


def is_char_cjk(c: str):
    return u'\u3000' <= c <= u'\u303F'


def is_char_otherjap(c: str):
    return u'\uFF00' <= c <= u'\uFFEF'


def is_char_chinese(c: str):
    return u'\u4E00' <= c <= u'\u9FFF'


def is_char_katakana(c: str):
    return u'\u30A0' <= c <= u'\u30FF'


def is_char_hiragana(c: str):
    is_hiragana = u'\u3040' <= c <= u'\u309F'
    return is_hiragana


def string_is_japanese(s: str) -> bool:
    """
    Determine if a string is purely katakana and/or hiragana
    :param s: Any old string
    :return: Japanese-ness
    """
    return all(char_is_japanese(c) for c in s)


def char_is_translatable(c) -> bool:
    return char_is_japanese(c) or c.isascii()


def calc_japaneseness(s: str):
    """
    Report the percentage of character types in a string. Something I'm playing with to help separate things that are
    worth translating from trash/untranslatable stuff.
    :param s: Any old string
    """
    analysis = {'hiragana': 0, 'katakana': 0, 'otherjap': 0, 'chinese': 0, 'cjk': 0}

    for c in s:
        # print(f'Analyzing {c}. Type: {type(c)}')
        if is_char_hiragana(c):
            analysis['hiragana'] += 1
            continue
        if is_char_katakana(c):
            analysis['katakana'] += 1
            continue
        if is_char_otherjap(c):
            analysis['otherjap'] += 1
            continue
        if is_char_chinese(c):
            analysis['chinese'] += 1
            continue
        if is_char_cjk(c):
            analysis['cjk'] += 1
            continue

    hiragana_perc = analysis["hiragana"] / len(s) * 100
    katakana_perc = analysis["katakana"] / len(s) * 100
    other_perc = analysis["otherjap"] / len(s) * 100
    chinese_perc = analysis["chinese"] / len(s) * 100
    cjk_perc = analysis["cjk"] / len(s) * 100
    translatability = hiragana_perc + katakana_perc + chinese_perc

    if debug:
        print(f'Hiragana: {hiragana_perc:.0f}%')
        print(f'Katakana: {katakana_perc:.0f}%')
        print(f'Otherjap: {other_perc:.0f}%')
        print(f'Chinese:  {chinese_perc:.0f}%')
        print(f'CJK:      {cjk_perc:.0f}%')
        print()
        print(f'Translatability: {translatability:0f}%')

    return translatability
