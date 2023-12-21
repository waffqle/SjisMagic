def check_file_contains_bytes(search_bytes, source_file_path):
    # Make sure it all exits in the source file
    with open(source_file_path, 'rb') as f:
        contents = f.read()

    if contents.find(search_bytes) == -1:
        return False
    else:
        return True


def read_file_sjis(input_file_path):
    input_file = open(input_file_path, "rb")
    contents = input_file.read()
    all_fields = contents.split(b';;;\x0A')
    return all_fields


def write_file_sjis(output_file_path, list_of_items):
    outputfile = open(output_file_path, "wb")
    for word in list_of_items:
        outputfile.write(word)
        outputfile.write(b';;;\x0A')


def write_popnhax_dict(output_file_path, list_of_items):
    outputfile = open(output_file_path, "wb")
    for word in list_of_items:
        outputfile.write(word)
        outputfile.write(b'\x0A')

    outputfile.write(b';')
