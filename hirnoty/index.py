import io
import json
import hashlib
import logging
import re
import zlib
from collections import namedtuple
from os import path, access, R_OK

from hirnoty.file_manager import CompressingFileManager
from hirnoty.utils import create_file

log = logging.getLogger(__name__)
# Separators for the index entry
# they should be different
SEP_FIELDS = "|"
SEP_ENTRY = "\n"
SEP_SUB = " "
METADATA_FILENAME = ".metadata.txt"

IndexEntry = namedtuple("IndexEntry", ["entry_type", "entry_id", "filename",
                                       "keywords", "extra"])

FILE_ABSENT = "A"
FILE_PRESENT = "P"


class SimpleIndex(object):
    def __init__(self, meta_dir, fm=None, use_inverted_index=False):
        self.meta_dir = meta_dir
        if fm:
            self.fm = fm
        else:
            self.fm = CompressingFileManager(meta_dir)
        self.meta_path = path.join(meta_dir, METADATA_FILENAME)
        if not path.exists(self.meta_path):
            create_file(self.meta_path)
        if use_inverted_index:
            self.engine = InvertedIndexSearch(self.meta_path, self.fm)
        else:
            self.engine = LinearSearch(self.meta_path, self.fm)

    @staticmethod
    def _verify_entry_id(entry_id):
        if not re.match("[a-f0-9]{64}", entry_id):
            raise IndexError("Invalid entry_id")

    def close(self):
        log.info("Closing index system")
        # don't use object after calling this
        self.engine.close()

    def get_file(self, entry_id):
        self._verify_entry_id(entry_id)
        return self.fm.get_file(entry_id)

    def search(self, text):
        return self.engine.search(text)

    def add_entry(self, filename, keywords, content="", extra=""):
        return self.engine.add_entry(filename, keywords, content, extra)


def load_index_entry(line):
    entry_type, entry_id, filename, keywords, extra = line.split(SEP_FIELDS, 4)
    return IndexEntry(replace_sep(entry_type),
                      replace_sep(entry_id),
                      replace_sep(filename),
                      replace_sep(keywords),
                      replace_entry_sep(extra))


def replace_sep(text):
    return text.replace(SEP_FIELDS, SEP_SUB).replace(SEP_ENTRY, SEP_SUB)


def replace_entry_sep(text):
    return text.replace(SEP_ENTRY, SEP_SUB)


def dump_index_entry(entry):
    return f"{SEP_FIELDS.join(entry)}{SEP_ENTRY}"


def _calculate_entry_id(filename, keywords, content=b"", extra=""):
    if content:
        return hashlib.sha256(content).hexdigest()
    else:
        return hashlib.sha256(
            f"{SEP_FIELDS.join((filename, keywords,extra))}{SEP_ENTRY}"
            .encode()).hexdigest()


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
        text = text.strip()
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
        return result

    def add_entry(self, filename, keywords, content="", extra=""):
        keywords = keywords.strip() if keywords else ""
        filename = filename.strip() if filename else ""
        if content:
            entry_type = FILE_PRESENT
        else:
            entry_type = FILE_ABSENT
        entry_id = _calculate_entry_id(filename, keywords, content, extra)
        if self.fm.contains(entry_id):
            raise FileExistsError("File already added")
        entry = IndexEntry(entry_type, entry_id, filename, keywords, extra)
        raw_entry = dump_index_entry(entry)
        # write to memory buffer
        self.metadata.write(raw_entry)
        # update metadata file
        self.metadata_file.write(raw_entry)
        self.metadata_file.flush()
        # write file with content
        self.fm.write_content(entry_id, content)
        return entry


class InvertedIndexSearch(object):
    BLACKLISTED_WORDS = set(["pdf", "zip", "", "\n"])

    def __init__(self, metadata_path, fm):
        self.metadata_path = metadata_path
        self.fm = fm
        self.inv_index = {}
        self.entry_id_index = {}
        self.load_data()

    def close(self):
        self.metadata_file.close()

    @staticmethod
    def split(text):
        return [item.strip() for item in re.split(r"[\n.,_\-\s]", text)]

    def _insert_to_inv_index(self, entry):
        self.entry_id_index[entry.entry_id] = entry
        for word in self.split(entry.filename) + self.split(entry.keywords):
            if word not in self.BLACKLISTED_WORDS:
                self.inv_index.setdefault(word, []).append(entry.entry_id)

    def load_data(self):
        with open(self.metadata_path, 'r') as fhandle:
            for line in fhandle:
                entry = load_index_entry(line[:-1])
                self._insert_to_inv_index(entry)
        # keep it open to add new data
        self.metadata_file = open(self.metadata_path, 'a')

    def add_entry(self, filename, keywords, content="", extra=""):
        keywords = keywords.strip() if keywords else ""
        filename = filename.strip() if filename else ""
        if content:
            entry_type = FILE_PRESENT
        else:
            entry_type = FILE_ABSENT
        entry_id = _calculate_entry_id(filename, keywords, content, extra)
        if entry_id in self.entry_id_index:
            raise FileExistsError("File already added")
        entry = IndexEntry(entry_type, entry_id, filename, keywords, extra)
        self._insert_to_inv_index(entry)
        # update metadata file
        self.metadata_file.write(dump_index_entry(entry))
        self.metadata_file.flush()
        # write file with content
        self.fm.write_content(entry_id, content)
        return entry

    def search(self, text):
        text = text.strip()
        acc = set()
        first = True
        for keyword in self.split(text):
            entry_ids = self.inv_index.get(keyword, [])
            if first:
                acc = acc.union(set(entry_ids))
            else:
                acc = acc.intersection(set(entry_ids))
            first = False
        return [self.entry_id_index[i] for i in acc]
