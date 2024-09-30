import sys
import os
import zlib


class Path:
    ROOT = '.git'
    OBJECTS = f'{ROOT}/objects'
    REFS = f'{ROOT}/refs'
    HEAD = f'{ROOT}/HEAD'


def init(_: list[any]):
    os.mkdir(Path.ROOT)
    os.mkdir(Path.OBJECTS)
    os.mkdir(Path.REFS)
    with open(Path.HEAD, "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")


def cat_file(argv: list[any]):
    def parse_number(content, offset) -> tuple[int, int]:
        val = 0 
        while chr(content[offset]).isdigit():
            val *= 10 
            val += int(chr(content[offset]))
            offset += 1
        return (val, offset)

    blob_sha1 = argv[3] 
    pref, suff = blob_sha1[:2], blob_sha1[2:]

    with open(f'{Path.OBJECTS}/{pref}/{suff}', 'rb') as f:
        blob = f.read()
    
    content = zlib.decompress(blob)
    if content.startswith(b'blob '):
        offset = 5
        (l, offset) = parse_number(content, offset)
        # skip \0
        offset += 1
        data = content[offset: offset + l]
        print(data.decode(), end='')

def main():
    cmd = sys.argv[1]
    {
        "init": init,
        "cat-file": cat_file
    }[cmd](sys.argv)


if __name__ == "__main__":
    main()
