from enum import Enum
import sys
import os
import zlib
import hashlib


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


def _parse_number(data, offset) -> tuple[int, int]:
    val = 0 
    while chr(data[offset]).isdigit():
        val *= 10 
        val += int(chr(data[offset]))
        offset += 1
    return (val, offset)


class Path:
    ROOT = '.git'
    OBJECTS = f'{ROOT}/objects'
    REFS = f'{ROOT}/refs'
    HEAD = f'{ROOT}/HEAD'


class GitObjectType(Enum):
    BLOB = 1
    TREE = 2


class GitBlob:
    def __init__(self, content: str):
        self.content = content

    @staticmethod
    def from_bytes(data: bytearray):
        assert(data.startswith(b'blob '))

        offset = len(b'blob ')
        (l, offset) = _parse_number(data, offset)
        # skip \0
        offset += 1
        content = data[offset: offset + l]
        return GitBlob(content.decode())


class GitTreeObjectMode(Enum):
    DIRECTORY = 40000
    REGULAR_FILE = 100644
    EXECUTABLE_FILE = 100755
    SYMBOLIC_FILE = 120000


class GitTreeObject:
    def __init__(self, mode: int, name: str, hash: str):
        self.mode = GitTreeObjectMode(mode)
        self.name = name 
        self.hash = hash
        data = _read_object(hash)
        self.obj = GitTree.from_bytes(data) if mode == GitTreeObjectMode.DIRECTORY.value else GitBlob.from_bytes(data)

    def __repr__(self):
        return self.pformat(name_only=False)
    
    def pformat(self, name_only=False):
        if name_only:
            return self.name
        else:
            return f"{self.mode.value:06} {self.name} {self.hash}"



class GitTree:
    def __init__(self, objs: list[GitTreeObject]):
        self.objs = objs 
    
    @staticmethod
    def from_bytes(data: bytearray):
        assert(data.startswith(b'tree '))

        offset = len(b'tree ')
        (l, offset) = _parse_number(data, offset)
        # skip \0
        offset += 1
        
        objs = []
        i = offset 
        while i < offset + l:
            mode = int(data[i: i + 6].decode())
            mode, i = _parse_number(data, i)
            i += 1 # mode + ' ' 
            j = i + 1
            while data[j] != 0:
                j += 1
            name = data[i: j].decode()

            i = j + 1
            hash = data[i: i + 20]

            i += 20
            objs.append(GitTreeObject(mode, name, hash.hex()))

        return GitTree(objs)
    
    def __repr__(self):
        return self.pformat(name_only=False)
    
    def pformat(self, name_only=False):
        return '\n'.join([x.pformat(name_only) for x in self.objs])


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


def ls_tree(argv: list[any]):
    hash = argv[3]

    data = _read_object(hash)
    tree = GitTree.from_bytes(data)
    print(tree.pformat(name_only=True))


def main():
    cmd = sys.argv[1]
    {
        "init": init,
        "cat-file": cat_file,
        "hash-object": hash_object,
        "ls-tree": ls_tree,
    }[cmd](sys.argv)


if __name__ == "__main__":
    main()
