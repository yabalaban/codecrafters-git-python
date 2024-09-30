import sys
import os
import zlib
import hashlib


class Path:
    ROOT = '.git'
    OBJECTS = f'{ROOT}/objects'
    REFS = f'{ROOT}/refs'
    HEAD = f'{ROOT}/HEAD'


def _read_object(hash: str) -> bytes:
    pref, suff = hash[:2], hash[2:]
    with open(f'{Path.OBJECTS}/{pref}/{suff}', 'rb') as f:
        return zlib.decompress(f.read())


def _write_object(hash: str, data: bytes):
    pref, suff = hash[:2], hash[2:]
    os.makedirs(f'{Path.OBJECTS}/{pref}', exist_ok=True)
    with open(f'{Path.OBJECTS}/{pref}/{suff}', 'wb+') as f:
        f.write(zlib.compress(data))


def _prepare_blob(content: str) -> bytes:
    data = bytearray()
    data.extend(b'blob ')
    data.extend(str(len(content)).encode())
    data.append(0)
    data.extend(content)
    return data


def init(_: list[any]):
    os.mkdir(Path.ROOT)
    os.mkdir(Path.OBJECTS)
    os.mkdir(Path.REFS)
    with open(Path.HEAD, "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")


def cat_file(argv: list[any]):
    def _parse_number(data, offset) -> tuple[int, int]:
        val = 0 
        while chr(data[offset]).isdigit():
            val *= 10 
            val += int(chr(data[offset]))
            offset += 1
        return (val, offset)
    
    def _parse_blob(data: bytes) -> str:
        offset = 5
        (l, offset) = _parse_number(data, offset)
        # skip \0
        offset += 1
        content = data[offset: offset + l]
        return content.decode()

    blob_sha1 = argv[3] 
    data = _read_object(blob_sha1)

    if data.startswith(b'blob '):
        content = _parse_blob(data)
        print(content, end='')


def hash_object(argv: list[any]):
    path = argv[3]
    
    with open(path, 'rb') as f:
        content = f.read()
    
    data = _prepare_blob(content)
    hash = hashlib.sha1(data).hexdigest()
    
    _write_object(hash, data)
    print(hash, end='')


def main():
    cmd = sys.argv[1]
    {
        "init": init,
        "cat-file": cat_file,
        "hash-object": hash_object,
    }[cmd](sys.argv)


if __name__ == "__main__":
    main()
