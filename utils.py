def check_file_contains_bytes(dictionary_file_path: str, source_file_path):
    # Get dictionary text
    with open(dictionary_file_path, 'rb') as dictionary_file:
        dictionary_contents = dictionary_file.read()
        things = dictionary_contents.split(b';;;\x0A')

    # Make sure it all exits in the source file
    with open(source_file_path, 'rb') as f:
        contents = f.read()

    found_count = 0
    for thing in things:
        found = False if contents.find(thing) == -1 else True
        if found:
            found_count += 1

    print(f'Found {found_count} of {len(things)} strings in file {source_file_path}')


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
