import io
import json
import hashlib
import logging
import re
from collections import namedtuple
from os import path, access, R_OK

log = logging.getLogger(__name__)
SEP_FILEID = "|"
SEP_KEYWORDS = "^"
METADATA_FILENAME = ".metadata.txt"

IndexEntry = namedtuple("IndexEntry", ["fileid", "filename", "keywords"])


class SimpleIndex(object):
    def __init__(self, save_path):
        self.save_path = save_path
        self.fm = FileManager(save_path)
        self.meta_path = path.join(save_path, METADATA_FILENAME)
        try:
            self.load_data()
        except FileNotFoundError:
            self.data = io.StringIO()
        self.data_file = open(self.meta_path, 'a')

    def load_data(self):
        with open(self.meta_path, 'r') as fhandle:
            self.data = io.StringIO(fhandle.read())

    @staticmethod
    def _verify_fileid(fileid):
        if not re.match("[a-f0-9]{64}", fileid):
            raise IndexError("Invalid fileid")

    @staticmethod
    def _replace_separators(text):
        return text.replace(SEP_FILEID, " ").replace(SEP_KEYWORDS, " ")

    def add_entry(self, filename, keywords, content):
        keywords = self._replace_separators(keywords) if keywords else ""
        filename = self._replace_separators(filename) if filename else ""
        fileid = hashlib.sha256(content).hexdigest()
        if self.fm.contains(fileid):
            raise FileExistsError("File already added")
        new_entry = f"{fileid}{SEP_FILEID}{filename}{SEP_KEYWORDS}{keywords}\n"
        self.data_file.write(new_entry)
        self.data_file.flush()
        # write to memory buffer
        self.data.write(new_entry)
        self.fm.write(fileid, content)
        return IndexEntry(fileid, filename, keywords)

    def close(self):
        # don't use object after calling this
        self.data_file.close()

    def get_file(self, fileid):
        self._verify_fileid(fileid)
        return self.fm.get_file(fileid)

    def search(self, text):
        data_content = self.data.getvalue()
        i = 0
        result = []
        while True:
            i = data_content.find(text, i)
            if i == -1:
                break
            while i >= 0 and data_content[i] != '\n':
                i -= 1
            start_index = i + 1
            i += 1
            while data_content[i] != '\n':
                i += 1
            fileid, rest = data_content[start_index:i].split(SEP_FILEID)
            filename, keywords = rest.split(SEP_KEYWORDS)
            result.append(IndexEntry(fileid, filename, keywords))
            log.debug("Found index result %s", result[-1])
        return result


class FileManager(object):
    def __init__(self, path):
        self.path = path

    def contains(self, filename):
        return access(path.join(self.path, filename), R_OK)

    def get_file(self, filename):
        return open(path.join(self.path, filename), "rb")

    def write(self, filename, content):
        with open(path.join(self.path, filename), 'wb') as fhandle:
            fhandle.write(content)

    def make_read_only(self, filename):
        pass

    def read(self, filename):
        with open(path.join(self.path, filename), "rb") as fhandle:
            return fhandle.read()
