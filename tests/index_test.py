#!/usr/bin/env python3
import os
import unittest
from hirnoty.index import SimpleIndex
from utils import async_test
import tempfile

# Case without extra data
EXAMPLE1_ENTRY_TYPE = "P"
EXAMPLE1_FILENAME = "example_file.pdf"
EXAMPLE1_KEYWORDS = "example keywords here"
EXAMPLE1_CONTENT = b"example content"
EXAMPLE1_ENTRY_ID = "a2dee47ba6268925da97750ab742baf67f02e2fb54ce23d499fb66a5b" \
                  "0222903"
EXAMPLE1_EXTRA = ""
# Case with extra data
EXAMPLE2_ENTRY_TYPE = "P"
EXAMPLE2_FILENAME = "example_file2.pdf"
EXAMPLE2_KEYWORDS = "example badwords there"
EXAMPLE2_CONTENT = b"example content2"
EXAMPLE2_ENTRY_ID = "400ae780e7a437dda7d518fb9ed09ba5e80754ceef632a49470e9a5a9" \
                  "1291e84"
EXAMPLE2_EXTRA = "extra meat"

# Case with no content
EXAMPLE3_ENTRY_TYPE = "A"
EXAMPLE3_FILENAME = "file3.zip"
EXAMPLE3_KEYWORDS = "every good boy does good"
EXAMPLE3_CONTENT = b""
EXAMPLE3_ENTRY_ID = "91c45a67989316c4b1786d234d7042f0f878f116847c2b33287aa53e0" \
                    "9585656"
EXAMPLE3_EXTRA = ""


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
        for i in range(1, 4):
            setattr(self, f"result{i}", self.index.add_entry(
                globals()[f"EXAMPLE{i}_FILENAME"],
                globals()[f"EXAMPLE{i}_KEYWORDS"],
                globals()[f"EXAMPLE{i}_CONTENT"],
                globals()[f"EXAMPLE{i}_EXTRA"]))

    def test_add_entry_metadata(self):
        for i in range(1, 4):
            self.assertEqual(getattr(self, f"result{i}").entry_type,
                             globals()[f"EXAMPLE{i}_ENTRY_TYPE"])
            self.assertEqual(getattr(self, f"result{i}").entry_id,
                             globals()[f"EXAMPLE{i}_ENTRY_ID"])
            self.assertEqual(getattr(self, f"result{i}").filename,
                             globals()[f"EXAMPLE{i}_FILENAME"])
            self.assertEqual(getattr(self, f"result{i}").keywords,
                             globals()[f"EXAMPLE{i}_KEYWORDS"])
            self.assertEqual(getattr(self, f"result{i}").extra,
                             globals()[f"EXAMPLE{i}_EXTRA"])

    def test_saved_content(self):
        for entry_id, file_content in [(EXAMPLE1_ENTRY_ID, EXAMPLE1_CONTENT),
                                       (EXAMPLE2_ENTRY_ID, EXAMPLE2_CONTENT)]:
            fhandle = self.index.get_file(entry_id)
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
        self.assertEqual(result[0].entry_type, EXAMPLE1_ENTRY_TYPE)
        self.assertEqual(result[0].entry_id, EXAMPLE1_ENTRY_ID)
        self.assertEqual(result[0].keywords, EXAMPLE1_KEYWORDS)
        self.assertEqual(result[0].extra, EXAMPLE1_EXTRA)

    def test_search_many_metadata(self):
        result = self.index.search("example")
        self.assertEqual(len(result), 2)
        # make sure the order is deterministic
        result.sort(key=lambda x: x.filename)
        self.assertEqual(result[0].filename, EXAMPLE1_FILENAME)
        self.assertEqual(result[0].entry_type, EXAMPLE1_ENTRY_TYPE)
        self.assertEqual(result[0].entry_id, EXAMPLE1_ENTRY_ID)
        self.assertEqual(result[0].keywords, EXAMPLE1_KEYWORDS)
        self.assertEqual(result[0].extra, EXAMPLE1_EXTRA)
        self.assertEqual(result[1].filename, EXAMPLE2_FILENAME)
        self.assertEqual(result[1].entry_type, EXAMPLE2_ENTRY_TYPE)
        self.assertEqual(result[1].entry_id, EXAMPLE2_ENTRY_ID)
        self.assertEqual(result[1].keywords, EXAMPLE2_KEYWORDS)
        self.assertEqual(result[1].extra, EXAMPLE2_EXTRA)

    def test_double_adding(self):
        self.assertRaises(FileExistsError, self.index.add_entry, "no matter",
                          "never mind", EXAMPLE1_CONTENT)


class InvertedIndexTest(IndexTest):
    def create_index(self):
        self.index = SimpleIndex(self.tempfolder_path, None, True)


if __name__ == "__main__":
    unittest.main()
