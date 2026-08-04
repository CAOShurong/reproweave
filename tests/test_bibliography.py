from __future__ import annotations

import unittest

from reproweave.bibliography import parse_bibtex, parse_csl_json
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

    def test_csl_requires_year(self) -> None:
        with self.assertRaises(ValidationError):
            parse_csl_json('{"title":"A"}')


if __name__ == "__main__":
    unittest.main()
