"""Concept markers in source must match the registry in docs/concepts.md."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "salesforce_agent"
CONCEPTS_DOC = REPO_ROOT / "docs" / "concepts.md"

EXPECTED_CONCEPTS = {
    "SFDC-1.0",
    "SFDC-1.1",
    "SFDC-1.2",
    "SFDC-1.3",
    "SFDC-1.4",
}


def _markers_in_source() -> set[str]:
    markers: set[str] = set()
    for path in PACKAGE.rglob("*.py"):
        markers.update(re.findall(r"CONCEPT:(SFDC-\d+\.\d+)", path.read_text()))
    return markers


@pytest.mark.concept("SFDC-1.0")
def test_all_expected_concepts_marked_in_source():
    assert _markers_in_source() == EXPECTED_CONCEPTS


@pytest.mark.concept("SFDC-1.0")
def test_concepts_doc_covers_all_markers():
    doc = CONCEPTS_DOC.read_text()
    for concept in _markers_in_source():
        assert concept in doc, f"{concept} missing from docs/concepts.md"
