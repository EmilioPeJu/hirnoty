import io
import zlib
from os import access, path, R_OK


class FileManager(object):
    # This class manages files based on a file id
    def __init__(self, path):
        self.path = path

    def contains(self, entry_id):
        if not entry_id:
            return False
        return access(path.join(self.path, entry_id), R_OK)

    def get_file(self, entry_id):
        if not entry_id:
            raise IOError("Invalid file id")
        return open(path.join(self.path, entry_id), "rb")

    def write_content(self, entry_id, content):
        if not entry_id:
            raise IOError("Invalid file id")
        with open(path.join(self.path, entry_id), 'wb') as fhandle:
            fhandle.write(content)

    def make_read_only(self, entry_id):
        if not entry_id:
            raise IOError("Invalid file id")
        pass

    def read_content(self, entry_id):
        if not entry_id:
            raise IOError("Invalid file id")
        with open(path.join(self.path, entry_id), "rb") as fhandle:
            return fhandle.read()


class CompressingFileManager(object):
    # This class manages files based on a file id
    def __init__(self, path):
        self._fm = FileManager(path)

    def contains(self, entry_id):
        return self._fm.contains(entry_id)

    def get_file(self, entry_id):
        with self._fm.get_file(entry_id) as fhandle:
            return io.BytesIO(zlib.decompress(fhandle.read()))

    def write_content(self, entry_id, content):
        return self._fm.write_content(entry_id, zlib.compress(content))

    def make_read_only(self, entry_id):
        return self._fm.make_read_only(entry_id)

    def read_content(self, entry_id):
        return zlib.decompress(self._fm.read_content(entry_id))
