"""
Thanks to CrazyRedMachine for this little gem.
I owe this fella way too many beers at this point.
-FuckwilderTuesday
"""


def extract_strings(input_file_path: str, output_file_path: str = "") -> str:
    """
    Extract shift-jis strings from a file. Due to the nature of the encoding, shift-jis can't be identified with 100%
    precision. Expect to get some false positives.

    :param input_file_path: Source file
    :param output_file_path: Dictionary of strings with address where they were found in source file. Semicolon delimited
    :return: Path to output file. (Handy if you didn't specify one.)
    """
    output_file_path = output_file_path if output_file_path else f"{input_file_path}_sjis_dump.txt"

    print(f"Extracting: {input_file_path}")

    inputfile = open(input_file_path, "rb")
    outputfile = open(output_file_path, "wb")

    byte1 = inputfile.read(1)
    word = bytearray()
    len = 0
    count = 0
    offset = 0
    off_comp = 1
    rearm = 0
    has_dbl = 0
    while byte1:
        if sjis_valid_single(byte1) and has_dbl:
            word.extend(byte1)
            len += 1
            off_comp += 1
        else:
            byte2 = inputfile.read(1)
            offset += 1
            if sjis_valid_double(byte1, byte2):
                has_dbl = 1
                word.extend(byte1)
                word.extend(byte2)
                len += 1
                off_comp += 2
            else:
                if len > 1 and has_dbl:  # end of word reached (minlen 2), add to file
                    outputfile.write(bytes(hex(offset - off_comp), 'ascii'))
                    outputfile.write(b';;;')
                    outputfile.write(word)
                    outputfile.write(b';;;')
                    outputfile.write(b'\x0A')
                    count += 1
                word = bytearray()
                has_dbl = 0
                len = 0
                off_comp = 1
                rearm = 1

        if rearm:
            byte1 = byte2
            rearm = 0
        else:
            byte1 = inputfile.read(1)
            offset += 1

    print(f"Found {count} sjis strings.")
    return output_file_path


def sjis_valid_double(first, second):
    # print("test ", first,second)
    valid_first = (b"\x81" <= first <= b"\x9F") or (b"\xE0" <= first <= b"\xFC")
    valid_second = (b"\x40" <= second <= b"\x9E") or (b"\x9F" <= second <= b"\xFC")
    return valid_first and valid_second


def sjis_valid_single(char):
    ascii = (char == b"\x0A") or (b"\x20" <= char <= b"\x7F")
    custom = (b"\xA1" <= char <= b"\xDF")
    # return ascii
    return ascii or custom
