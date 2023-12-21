"""
Thanks to CrazyRedMachine for this little gem.
I owe this fella way too many beers at this point.
-FuckwilderTuesday
"""

import utils


def extract_strings(input_file_path: str, output_file_path: str):
    """
    Extract shift-jis strings from a file. Due to the nature of the encoding, shift-jis can't be identified with 100%
    precision. Expect to get some false positives.
    Output is de-duped.

    :param input_file_path: Source file
    :param output_file_path: Dictionary of strings with address where they were
    found in source file. Semicolon delimited.
    """

    print(f"Extracting: {input_file_path}")

    inputfile = open(input_file_path, "rb")

    extracted_strings = []

    byte1 = inputfile.read(1)
    word = bytearray()
    length = 0
    count = 0
    decoding_errors = 0
    offset = 0
    off_comp = 1
    rearm = 0
    has_dbl = 0
    while byte1:
        if sjis_valid_single(byte1) and has_dbl:
            word.extend(byte1)
            length += 1
            off_comp += 1
        else:
            byte2 = inputfile.read(1)
            offset += 1
            if sjis_valid_double(byte1, byte2):
                has_dbl = 1
                word.extend(byte1)
                word.extend(byte2)
                length += 1
                off_comp += 2
            else:
                if length > 1 and has_dbl:  # end of word reached (minlen 2), add to file
                    if word not in extracted_strings:
                        try:
                            # Add word to list
                            extracted_strings.append(word)
                            count += 1
                        except UnicodeDecodeError:
                            decoding_errors += 1

                    # Reset for next word
                    word = bytearray()
                    has_dbl = 0
                    length = 0
                    off_comp = 1
                    rearm = 1
        if rearm:
            byte1 = byte2
            rearm = 0
        else:
            byte1 = inputfile.read(1)
            offset += 1

    utils.write_file_sjis(output_file_path, extracted_strings)

    print(f"Found {count} sjis strings. Had {decoding_errors} decoding errors.")


def sjis_valid_double(first, second):
    # print("test ", first,second)
    valid_first = (b"\x81" <= first <= b"\x9F") or (b"\xE0" <= first <= b"\xFC")
    valid_second = (b"\x40" <= second <= b"\x9E") or (b"\x9F" <= second <= b"\xFC")
    return valid_first and valid_second


def sjis_valid_single(char):
    is_ascii = (char == b"\x0A") or (b"\x20" <= char <= b"\x7F")
    is_custom = (b"\xA1" <= char <= b"\xDF")
    # return ascii
    return is_ascii or is_custom
