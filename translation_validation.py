debug = False


def char_is_japanese(c) -> bool:
    """
    Determine if a character is katakana or hiragana
    :param c: Character to check
    :return: Japanese-ness
    """
    is_hiragana = u'\u3040' <= c <= u'\u309F'
    is_katakana = u'\u30A0' <= c <= u'\u30FF'
    is_chinese = u'\u4E00' <= c <= u'\u9FFF'
    is_otherjap = u'\uFF00' <= c <= u'\uFFEF'
    is_cjk = u'\u3000' <= c <= u'\u303F'

    translatable = is_hiragana or is_katakana or is_chinese or is_otherjap or is_cjk

    if debug:
        print(f'{c} is {c.encode('unicode-escape')} Translatable: {translatable}')

    return translatable


def string_is_japanese(s: str) -> bool:
    """
    Determine if a string is purely katakana and/or hiragana
    :param s: Any old string
    :return: Japanese-ness
    """
    return all(char_is_japanese(c) for c in s)


def char_is_translatable(c) -> bool:
    return char_is_japanese(c) or c.isascii()


def string_is_translation_target(s: str) -> bool:
    """
    Determine if a string is something we want to translate. Exclude non-Japanese texts. Maybe other things. This thing
    has a weird tweaks to help find the specific stuff I want to translate.
    :param s:  Any old string
    :return: Should we translate it?
    """
    if len(s) < 8:
        if debug:
            print(f'{s} is too short')
        return False

    if s.__contains__('ﾌﾌﾌ'):
        if debug:
            print(f'{s} has too many ﾌﾌﾌ')
        return False

    translatable = all(char_is_translatable(c) for c in s)

    if debug and not translatable:
        print(f'"{s}" is not translatable')
    return translatable
