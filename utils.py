
def check_file_contains_bytes(filename:str, things:list[bytes]):
    with open(filename, 'rb') as f:
        contents = f.read()

        for thing in things:
            found = contents.find(thing)
            print(f'{found}: File contains: "{thing}"')
