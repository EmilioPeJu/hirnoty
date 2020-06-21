#!/usr/bin/env python3
import unittest
from hirnoty.jobs import Runner
from hirnoty.utils import get_source
from utils import async_test


class JobsTest(unittest.TestCase):
    @async_test
    async def test_example_script_returns_correct_result(self):
        runner = Runner(get_source("scripts"), "test", ["OK", "Passed"])
        result = []
        async for item in runner.work():
            result.append(item)
        self.assertTrue(
            result[0].endswith("Test script called with OK Passed\n"))

    def test_sanitize_template(self):
        self.assertEqual(Runner._sanitize_template("abCD123-..+=4/5"),
                         "abCD123-45")


if __name__ == "__main__":
    unittest.main()
