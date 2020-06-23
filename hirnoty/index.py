import io
import json
import hashlib
import logging
import re
from collections import namedtuple
from os import path, access, R_OK

from hirnoty.utils import create_file

log = logging.getLogger(__name__)
# Separators for the index entry
# they should be different
SEP_FILEID = "|"
SEP_KEYWORDS = "^"
SEP_ENTRY = "\n"
METADATA_FILENAME = ".metadata.txt"

IndexEntry = namedtuple("IndexEntry", ["fileid", "filename", "keywords"])


class SimpleIndex(object):
    def __init__(self, save_path, use_inverted_index=False):
        self.save_path = save_path
        self.fm = FileManager(save_path)
        self.meta_path = path.join(save_path, METADATA_FILENAME)
        if not path.exists(self.meta_path):
            create_file(self.meta_path)
        if use_inverted_index:
            self.engine = InvertedIndexSearch(self.meta_path, self.fm)
        else:
            self.engine = LinearSearch(self.meta_path, self.fm)

    @staticmethod
    def _verify_fileid(fileid):
        if not re.match("[a-f0-9]{64}", fileid):
            raise IndexError("Invalid fileid")

    def close(self):
        # don't use object after calling this
        self.engine.close()

    def get_file(self, fileid):
        self._verify_fileid(fileid)
        return self.fm.get_file(fileid)

    def search(self, text):
        return self.engine.search(text)

    def add_entry(self, filename, keywords, content):
        return self.engine.add_entry(filename, keywords, content)


def load_index_entry(line):
    fileid, rest = line.split(SEP_FILEID)
    filename, keywords = rest.split(SEP_KEYWORDS)
    return IndexEntry(fileid, filename, keywords)


def dump_index_entry(entry):
    return f"{entry.fileid}{SEP_FILEID}{entry.filename}" \
           f"{SEP_KEYWORDS}{entry.keywords}{SEP_ENTRY}"


def replace_index_separators(text, sub=" "):
    return text.replace(SEP_FILEID, sub).replace(SEP_KEYWORDS, sub) \
        .replace(SEP_ENTRY, sub)


class LinearSearch(object):
    def __init__(self, metadata_path, fm):
        self.metadata_path = metadata_path
        self.fm = fm
        self.load_data()

    def close(self):
        self.metadata_file.close()

    def load_data(self):
        with open(self.metadata_path, 'r') as fhandle:
            self.metadata = io.StringIO(fhandle.read())
        # keep it open to add new data
        self.metadata_file = open(self.metadata_path, 'a')

    def search(self, text):
        text = replace_index_separators(text).strip()
        metadata_content = self.metadata.getvalue()
        i = 0
        result = []
        while True:
            i = metadata_content.find(text, i)
            if i == -1:
                break
            while i >= 0 and metadata_content[i] != SEP_ENTRY:
                i -= 1
            start_index = i + 1
            i += 1
            while metadata_content[i] != SEP_ENTRY:
                i += 1
            entry = load_index_entry(metadata_content[start_index:i])
            result.append(entry)
            log.debug("Found index result %s", entry)
        return result

    def add_entry(self, filename, keywords, content):
        keywords = replace_index_separators(keywords).strip() \
            if keywords else ""
        filename = replace_index_separators(filename).strip() \
            if filename else ""
        fileid = hashlib.sha256(content).hexdigest()
        if self.fm.contains(fileid):
            raise FileExistsError("File already added")
        entry = IndexEntry(fileid, filename, keywords)
        raw_entry = dump_index_entry(entry)
        # write to memory buffer
        self.metadata.write(raw_entry)
        # update metadata file
        self.metadata_file.write(raw_entry)
        self.metadata_file.flush()
        # write file with content
        self.fm.write(fileid, content)
        return entry


class InvertedIndexSearch(object):
    BLACKLISTED_WORDS = set(["pdf", "zip", "", "\n"])

    def __init__(self, metadata_path, fm):
        self.metadata_path = metadata_path
        self.fm = fm
        self.inv_index = {}
        self.fileid_index = {}
        self.load_data()

    def close(self):
        self.metadata_file.close()

    @staticmethod
    def split(text):
        return [item.strip() for item in re.split(r"[\n.,_\-\s]", text)]

    def _insert_to_inv_index(self, entry):
        self.fileid_index[entry.fileid] = entry
        for word in self.split(entry.filename) + self.split(entry.keywords):
            if word not in self.BLACKLISTED_WORDS:
                self.inv_index.setdefault(word, []).append(entry.fileid)

    def load_data(self):
        with open(self.metadata_path, 'r') as fhandle:
            for line in fhandle:
                entry = load_index_entry(line)
                self._insert_to_inv_index(entry)
        # keep it open to add new data
        self.metadata_file = open(self.metadata_path, 'a')

    def add_entry(self, filename, keywords, content):
        keywords = replace_index_separators(keywords).strip() \
            if keywords else ""
        filename = replace_index_separators(filename).strip() \
            if filename else ""
        fileid = hashlib.sha256(content).hexdigest()
        if fileid in self.fileid_index:
            raise FileExistsError("File already added")
        entry = IndexEntry(fileid, filename, keywords)
        self._insert_to_inv_index(entry)
        # update metadata file
        self.metadata_file.write(dump_index_entry(entry))
        self.metadata_file.flush()
        # write file with content
        self.fm.write(fileid, content)
        return entry

    def search(self, text):
        text = replace_index_separators(text).strip()
        acc = set()
        first = True
        for keyword in self.split(text):
            fileids = self.inv_index.get(keyword, [])
            if first:
                acc = acc.union(set(fileids))
            else:
                acc = acc.intersection(set(fileids))
            first = False
        return [self.fileid_index[i] for i in acc]


class FileManager(object):
    # This class manages files based on a file id
    def __init__(self, path):
        self.path = path

    def contains(self, fileid):
        return access(path.join(self.path, fileid), R_OK)

    def get_file(self, fileid):
        return open(path.join(self.path, fileid), "rb")

    def write(self, fileid, content):
        with open(path.join(self.path, fileid), 'wb') as fhandle:
            fhandle.write(content)

    def make_read_only(self, fileid):
        pass

    def read(self, fileid):
        with open(path.join(self.path, fileid), "rb") as fhandle:
            return fhandle.read()
