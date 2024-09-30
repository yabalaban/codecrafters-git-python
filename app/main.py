from enum import Enum
from stat import S_ISLNK, S_ISREG, ST_MODE
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


def _parse_number(data, offset) -> tuple[int, int]:
    val = 0 
    while chr(data[offset]).isdigit():
        val *= 10 
        val += int(chr(data[offset]))
        offset += 1
    return (val, offset)

def _obj_data(prefix: str, content: str | bytearray) -> bytearray:
    data = bytearray()
    if type(content) == bytearray:
        bcontent = content
    else:
        bcontent = content.encode()
    data.extend(prefix.encode())
    data.append(ord(' '))
    data.extend(str(len(bcontent)).encode())
    data.append(0)
    data.extend(bcontent)
    return data


def _entry_data(mode: str, name: str, hash: str) -> bytearray:
    data = bytearray()
    data.extend(mode.encode())
    data.append(ord(' '))
    data.extend(name.encode())
    data.append(0)
    data.extend(bytes.fromhex(hash))
    return data


class GitTreeObjectMode(Enum):
    DIRECTORY = 40000
    REGULAR_FILE = 100644
    EXECUTABLE_FILE = 100755
    SYMBOLIC_FILE = 120000


class GitBlob:
    def __init__(self, content: str):
        self.content = content

    def write(self) -> bytes:
        data = _obj_data('blob', self.content)
        hash = hashlib.sha1(data).hexdigest()
        _write_object(hash, data)
        return hash
    
    @staticmethod
    def read(hash: bytearray):
        data = _read_object(hash)
        assert(data.startswith(b'blob '))
        offset = len(b'blob ')
        (l, offset) = _parse_number(data, offset)
        # skip \0
        offset += 1
        content = data[offset: offset + l]
        return GitBlob(content.decode())


class GitTreeEntry:
    def __init__(self, mode: GitTreeObjectMode, name: str, hash: str):
        self.mode = mode
        self.name = name 
        self.hash = hash

    def __repr__(self):
        return self.pformat(name_only=False)

    def pformat(self, name_only=False):
        if name_only:
            return self.name
        else:
            return f"{self.mode.value:06} {self.name} {self.hash}"
    
    def load(self): 
        return GitTree.read(hash) if self.mode == GitTreeObjectMode.DIRECTORY else GitBlob.read(hash) 

    def encode(self) -> bytes:
        return _entry_data(str(self.mode.value), self.name, self.hash)


class GitTree:
    def __init__(self, entries: list[GitTreeEntry]):
        self.entries = entries
    
    def __repr__(self):
        return self.pformat(name_only=False)
    
    def pformat(self, name_only=False):
        return '\n'.join([x.pformat(name_only) for x in self.entries])
    
    def write(self) -> bytes:
        body = bytearray()
        for entry in self.entries:
            body.extend(entry.encode())
        data = _obj_data('tree', body)
        hash = hashlib.sha1(data).hexdigest()
        _write_object(hash, data)
        return hash

    @staticmethod 
    def read(hash: bytearray):
        data = _read_object(hash)
        assert(data.startswith(b'tree '))

        offset = len(b'tree ')
        (l, offset) = _parse_number(data, offset)
        # skip \0
        offset += 1
        entries = []
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
            entries.append(GitTreeEntry(GitTreeObjectMode(mode), name, hash.hex()))
        return GitTree(entries)


class GitCommitTree:
    def __init__(self, tree_sha: str, commit_sha: str, message: str):
        self.tree_sha = tree_sha 
        self.commit_sha = commit_sha
        self.message = message 
    
    def write(self) -> bytes:
        body = bytearray()
        body.extend(b'tree ')
        body.extend(self.tree_sha.encode())
        body.extend(b'\n')
        body.extend(b'parent ')
        body.extend(self.commit_sha.encode())
        body.extend(b'\n')
        body.extend(b'author yabalaban <hahahoho@gmail.com> 1727729150 +0000\n')
        body.extend(b'committer nabalabay <hohohaha@gmail.com> 1727729150 +0000\n\n')
        body.extend(self.message.encode())
        body.extend(b'\n')
        data = _obj_data('commit', body)
        hash = hashlib.sha1(data).hexdigest()
        _write_object(hash, data)
        return hash


def init(_: list[any]):
    os.mkdir(Path.ROOT)
    os.mkdir(Path.OBJECTS)
    os.mkdir(Path.REFS)
    with open(Path.HEAD, "w") as f:
        f.write("ref: refs/heads/main\n")
    print("Initialized git directory")


def cat_file(argv: list[any]):
    blob_sha1 = argv[3] 
    blob = GitBlob.read(blob_sha1)
    print(blob.content, end='')


def hash_object(argv: list[any]):
    path = argv[3]
    with open(path, 'rb') as f:
        content = f.read()
    
    blob = GitBlob(content.decode())
    hash = blob.write()
    print(hash, end='')


def ls_tree(argv: list[any]):
    hash = argv[3]
    tree = GitTree.read(hash)
    print(tree.pformat(name_only=True))


def write_tree(argv: list[any]):
    def _create_tree(path) -> GitTree:
        entries = []
        for x in sorted(os.listdir(path)):
            fp = f'{path}/{x}'
            if x == '.git':
                continue 
            if os.path.isdir(fp):
                tree = _create_tree(fp)
                entries.append(GitTreeEntry(GitTreeObjectMode.DIRECTORY, x, tree.write()))
            else:
                with open(fp, 'rb') as f:
                    content = f.read()
                blob = GitBlob(content.decode())
                mode = os.stat(fp)[ST_MODE]
                filemode = GitTreeObjectMode.EXECUTABLE_FILE
                if S_ISLNK(mode):
                    filemode = GitTreeObjectMode.SYMBOLIC_FILE 
                if S_ISREG(mode):
                    filemode = GitTreeObjectMode.REGULAR_FILE
                entries.append(GitTreeEntry(filemode, x, blob.write()))
        tree = GitTree(entries)
        return tree

    tree = _create_tree('.')
    hash = tree.write()
    print(hash, end='')


def commit_tree(argv: list[any]):
    tree_sha = argv[2]
    commit_sha = argv[4]
    message = argv[6]
    commit = GitCommitTree(tree_sha, commit_sha, message)
    print(commit.write(), end='')


def main():
    cmd = sys.argv[1]
    {
        "init": init,
        "cat-file": cat_file,
        "hash-object": hash_object,
        "ls-tree": ls_tree,
        "write-tree": write_tree,
        "commit-tree": commit_tree,
    }[cmd](sys.argv)


if __name__ == "__main__":
    main()
