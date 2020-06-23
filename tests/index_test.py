#!/usr/bin/env python3
import os
import unittest
from hirnoty.index import SimpleIndex
from utils import async_test
import tempfile

EXAMPLE1_FILENAME = "example_file.pdf"
EXAMPLE1_KEYWORDS = "example keywords here"
EXAMPLE1_CONTENT = b"example content"
EXAMPLE1_FILEID = "a2dee47ba6268925da97750ab742baf67f02e2fb54ce23d499fb66a5b" \
                  "0222903"
EXAMPLE2_FILENAME = "example_file2.pdf"
EXAMPLE2_KEYWORDS = "example badwords there"
EXAMPLE2_CONTENT = b"example content2"
EXAMPLE2_FILEID = "400ae780e7a437dda7d518fb9ed09ba5e80754ceef632a49470e9a5a9" \
                  "1291e84"


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tempfolder = tempfile.TemporaryDirectory()
        self.tempfolder_path = self.tempfolder.__enter__()
        self.create_index()
        self.add_example_entries()

    def create_index(self):
        self.index = SimpleIndex(self.tempfolder_path)

    def tearDown(self):
        self.index.close()
        self.tempfolder.__exit__(None, None, None)

    def add_example_entries(self):
        self.result1 = self.index.add_entry(EXAMPLE1_FILENAME,
                                            EXAMPLE1_KEYWORDS,
                                            EXAMPLE1_CONTENT)
        self.result2 = self.index.add_entry(EXAMPLE2_FILENAME,
                                            EXAMPLE2_KEYWORDS,
                                            EXAMPLE2_CONTENT)

    def test_add_entry_metadata(self):
        self.assertEqual(self.result1.filename, EXAMPLE1_FILENAME)
        self.assertEqual(self.result1.fileid, EXAMPLE1_FILEID)
        self.assertEqual(self.result1.keywords, EXAMPLE1_KEYWORDS)

    def test_saved_content(self):
        for file_id, file_content in [(EXAMPLE1_FILEID, EXAMPLE1_CONTENT),
                                      (EXAMPLE2_FILEID, EXAMPLE2_CONTENT)]:
            fhandle = self.index.get_file(file_id)
            self.assertEqual(fhandle.read(), file_content)
            fhandle.close()

    def test_closing_and_opening_keeps_data(self):
        self.index.close()
        self.create_index()
        self.test_saved_content()

    def test_search_one_metadata(self):
        result = self.index.search("keywords")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].filename, EXAMPLE1_FILENAME)
        self.assertEqual(result[0].fileid, EXAMPLE1_FILEID)
        self.assertEqual(result[0].keywords, EXAMPLE1_KEYWORDS)

    def test_search_many_metadata(self):
        result = self.index.search("example")
        self.assertEqual(len(result), 2)
        # make sure the order is deterministic
        result.sort(key=lambda x: x.filename)
        self.assertEqual(result[0].filename, EXAMPLE1_FILENAME)
        self.assertEqual(result[0].fileid, EXAMPLE1_FILEID)
        self.assertEqual(result[0].keywords, EXAMPLE1_KEYWORDS)
        self.assertEqual(result[1].filename, EXAMPLE2_FILENAME)
        self.assertEqual(result[1].fileid, EXAMPLE2_FILEID)
        self.assertEqual(result[1].keywords, EXAMPLE2_KEYWORDS)

    def test_double_adding(self):
        self.assertRaises(FileExistsError, self.index.add_entry, "no matter",
                          "never mind", EXAMPLE1_CONTENT)


class InvertedIndexTest(IndexTest):
    def create_index(self):
        self.index = SimpleIndex(self.tempfolder_path, True)


if __name__ == "__main__":
    unittest.main()
