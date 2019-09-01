import json
import logging
from os import path
NOTUPLOADED_PREFIX = "_"
log = logging.getLogger(__name__)


class SimpleIndex(object):

    def __init__(self, index_dir):
        self.doc_index_path = path.join(index_dir, '.doc_index')
        self.lex_index_path = path.join(index_dir, '.lex_index')
        self.hash2docid_index_path = path.join(index_dir, '.hash2docid_index')
        self._lexicon = {}
        self._docs = {}
        self._hash2docid = {}
        if not path.exists(self.doc_index_path):
            self.save()
        else:
            self.load()

    def not_uploaded(self, doc_id):
        return doc_id.startswith(NOTUPLOADED_PREFIX)

    def has_doc(self, doc_id):
        return doc_id in self._docs

    def has_hash(self, hash_):
        return  hash_ in self._hash2docid

    def normalize_words(self, words):
        search =  'áéíóúü'
        replace = 'aeiouu'
        trans = str.maketrans(search, replace)
        for word in words:
            yield word.strip().lower().translate(trans)

    def index_file(self, doc_id, words, filename, hash_):
        if doc_id == None:
            doc_id = NOTUPLOADED_PREFIX + hash_;
        doc_entry = self._docs.get(doc_id)
        if not doc_entry:
            doc_entry = {'id': doc_id, 'keywords': []}
            self._docs[doc_id] = doc_entry
        doc_entry['keywords'].extend(words)
        doc_entry['filename'] = filename
        doc_entry['hash'] = hash_
        self._hash2docid[hash_] = doc_id
        for word in self.normalize_words(words):
            lex_entry = self._lexicon.get(word)
            if not lex_entry:
                lex_entry = []
                self._lexicon[word] = lex_entry
            lex_entry.append(doc_id)
        # it's horrible I know
        self.save()
        return doc_entry

    def update_docid(self, old, new):
        log.info('updating docid %s to %s', old, new)
        doc = self.get_metadata(old)
        del self._docs[old]
        self._docs[new] = doc
        self._hash2docid[doc['hash']] = new
        for word in doc['keywords']:
            lex_entry = self._lexicon[word]
            index = lex_entry.index(old)
            lex_entry[index] = new
        self.save()

    def search_word(self, word):
        return self._lexicon.get(word, [])

    def search_words(self, words):
        if not words:
            return []
        result = set(self.search_word(words[0]))
        for word in words[1:]:
            result = result & set(self.search_word(word))
        return list(result)

    def get_metadata(self, doc_id):
        return self._docs.get(doc_id)

    def load(self):
        with open(self.doc_index_path, 'r') as fhandler:
            self._docs = json.load(fhandler)
        with open(self.lex_index_path, 'r') as fhandler:
            self._lexicon = json.load(fhandler)
        with open(self.hash2docid_index_path, 'r') as fhandler:
            self._hash2docid = json.load(fhandler)

    def save(self):
        with open(self.doc_index_path, 'w') as fhandler:
            json.dump(self._docs, fhandler)
        with open(self.lex_index_path, 'w') as fhandler:
            json.dump(self._lexicon, fhandler)
        with open(self.hash2docid_index_path, 'w') as fhandler:
            json.dump(self._hash2docid, fhandler)

