from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

from reproweave.errors import ValidationError
from reproweave.store import read_json
from reproweave.util import (
    canonical_json,
    ensure_id,
    ensure_text,
    html_escape,
    pretty_json,
    sha256_file,
    sha256_text,
    slugify,
)


class UtilTests(unittest.TestCase):
    def test_non_standard_json_numbers_are_rejected_on_read(self) -> None:
        for value in ("NaN", "Infinity", "-Infinity", "1e9999", "-1e9999"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "value.json"
                path.write_text('{"value":' + value + "}", encoding="utf-8")
                with self.assertRaisesRegex(ValidationError, "finite|standard JSON"):
                    read_json(path)

    def test_json_writers_refuse_non_finite_values(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                pretty_json({"value": value})
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_json({"value": value})

    def test_valid_id(self) -> None:
        self.assertEqual(ensure_id("paper-42"), "paper-42")

    def test_invalid_uppercase_id(self) -> None:
        with self.assertRaises(ValidationError):
            ensure_id("Paper")

    def test_invalid_leading_number(self) -> None:
        with self.assertRaises(ValidationError):
            ensure_id("42-paper")

    def test_id_length_budget_matches_filename_portability_boundary(self) -> None:
        self.assertEqual(ensure_id("a" + "1" * 199), "a" + "1" * 199)
        with self.assertRaises(ValidationError):
            ensure_id("a" + "1" * 200)

    def test_ensure_text_strips(self) -> None:
        self.assertEqual(ensure_text("  value ", "field"), "value")

    def test_ensure_text_rejects_blank(self) -> None:
        with self.assertRaises(ValidationError):
            ensure_text("  ", "field")

    def test_slugify(self) -> None:
        self.assertEqual(slugify("A Great Paper: v2!"), "a-great-paper-v2")

    def test_slugify_numeric_prefix(self) -> None:
        self.assertEqual(slugify("2025 Results"), "item-2025-results")

    def test_canonical_json_order(self) -> None:
        self.assertEqual(canonical_json({"b": 2, "a": 1}), '{"a":1,"b":2}')

    def test_sha256_text_is_prefixed(self) -> None:
        self.assertTrue(sha256_text("x").startswith("sha256:"))

    def test_sha256_file_matches_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.txt"
            path.write_text("hello", encoding="utf-8")
            self.assertEqual(sha256_file(path), sha256_text("hello"))

    def test_html_escape(self) -> None:
        self.assertEqual(html_escape('<a x="1">&'), "&lt;a x=&quot;1&quot;&gt;&amp;")


if __name__ == "__main__":
    unittest.main()
