from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from reproweave.bibliography import load_csl_json, parse_bibtex, parse_csl_json
from reproweave.errors import ValidationError


class BibliographyTests(unittest.TestCase):
    def test_bibtex_article(self) -> None:
        papers = parse_bibtex(
            "@article{Smith2025, title={A {Nested} Title}, author={A Smith and B Doe}, "
            "year={2025}, journal={Journal}, doi={10.1/x}}"
        )
        self.assertEqual(papers[0]["id"], "smith2025")
        self.assertEqual(papers[0]["authors"], ["A Smith", "B Doe"])

    def test_bibtex_parentheses(self) -> None:
        papers = parse_bibtex('@inproceedings(k, title="A title", year=2024, author="A")')
        self.assertEqual(papers[0]["year"], 2024)

    def test_bibtex_ignores_comment(self) -> None:
        self.assertEqual(parse_bibtex("@comment{hello}"), [])

    def test_bibtex_requires_title(self) -> None:
        with self.assertRaises(ValidationError):
            parse_bibtex("@article{x,year={2025},author={A}}")

    def test_bibtex_requires_year(self) -> None:
        with self.assertRaises(ValidationError):
            parse_bibtex("@article{x,title={T},author={A}}")

    def test_bibtex_unbalanced(self) -> None:
        with self.assertRaises(ValidationError):
            parse_bibtex("@article{x,title={T}")

    def test_bibtex_duplicate_key(self) -> None:
        with self.assertRaises(ValidationError):
            parse_bibtex("@article{x,title={A},year=2020}@article{x,title={B},year=2021}")

    def test_csl_single_object(self) -> None:
        papers = parse_csl_json(
            '{"id":"p1","title":"A","author":[{"given":"Ada","family":"Lovelace"}],'
            '"issued":{"date-parts":[[2025]]}}'
        )
        self.assertEqual(papers[0]["authors"], ["Ada Lovelace"])

    def test_csl_literal_author(self) -> None:
        papers = parse_csl_json(
            '{"title":"A","author":[{"literal":"Research Lab"}],"issued":{"date-parts":[[2025]]}}'
        )
        self.assertEqual(papers[0]["authors"], ["Research Lab"])

    def test_csl_invalid_json(self) -> None:
        with self.assertRaises(ValidationError):
            parse_csl_json("{")

    def test_csl_rejects_duplicate_keys_and_non_standard_numbers(self) -> None:
        for text in (
            '{"id":"one","id":"two","title":"A","issued":{"date-parts":[[2025]]}}',
            '{"title":"A","score":NaN,"issued":{"date-parts":[[2025]]}}',
        ):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_csl_json(text)

    def test_csl_requires_year(self) -> None:
        for text in (
            '{"title":"A"}',
            '{"title":"A","issued":{"date-parts":[{}]}}',
        ):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_csl_json(text)

    def test_csl_rejects_invalid_author_shapes(self) -> None:
        for author in ("null", "{}", '[["Ada"]]'):
            text = '{"title":"A","author":' + author + ',"issued":{"date-parts":[[2025]]}}'
            with self.subTest(author=author), self.assertRaises(ValidationError):
                parse_csl_json(text)

    def test_load_csl_reports_invalid_utf8_as_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "invalid.json"
            source.write_bytes(b"\xff\xfe")
            with self.assertRaisesRegex(ValidationError, "cannot read CSL JSON source"):
                load_csl_json(source)

    def test_csl_null_optional_fields_remain_empty(self) -> None:
        paper = parse_csl_json(
            '{"id":"p1","title":"A","DOI":null,"URL":null,"abstract":null,'
            '"container-title":null,"issued":{"date-parts":[[2025]]}}'
        )[0]
        self.assertEqual(
            {field: paper[field] for field in ("doi", "url", "abstract", "venue")},
            {"doi": "", "url": "", "abstract": "", "venue": ""},
        )

    def test_csl_rejects_non_text_title_and_optional_fields(self) -> None:
        for text in (
            '{"title":null,"issued":{"date-parts":[[2025]]}}',
            '{"title":"A","DOI":{},"issued":{"date-parts":[[2025]]}}',
            '{"title":"A","URL":[],"issued":{"date-parts":[[2025]]}}',
        ):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_csl_json(text)


if __name__ == "__main__":
    unittest.main()
