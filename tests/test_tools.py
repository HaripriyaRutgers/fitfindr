"""
tests/test_tools.py

Unit tests for the three FitFindr tools.

The search_listings tests and the two failure-mode tests run fully offline
(no API key or network needed) because those paths never call the LLM.

Run from the project root with:
    pytest
"""

import os
import sys

# Make sure the project root is importable when running pytest from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import search_listings, suggest_outfit, create_fit_card


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ── suggest_outfit ─────────────────────────────────────────────────────────────

def test_suggest_empty_wardrobe():
    result = suggest_outfit({"name": "Graphic Tee"}, {"items": []})
    assert isinstance(result, str)
    assert len(result) > 0
    assert "empty" in result.lower()


# ── create_fit_card ─────────────────────────────────────────────────────────────

def test_fit_card_empty_outfit():
    result = create_fit_card("", {"name": "Graphic Tee"})
    assert result == "Cannot create a fit card without an outfit description."
