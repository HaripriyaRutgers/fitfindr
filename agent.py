"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── query parsing ─────────────────────────────────────────────────────────────

_SIZE_WORDS = ["xxl", "xl", "l", "m", "s", "xs"]

# Filler words that would otherwise match as substrings everywhere and pollute
# the keyword ranking (e.g. "a" is inside "black").
_STOPWORDS = {
    "looking", "for", "a", "an", "the", "i", "im", "want", "need", "some",
    "under", "below", "less", "than", "in", "size", "with", "and", "of",
    "me", "find", "to", "my", "is", "are", "that", "this", "what", "out",
    "there", "how", "would", "style", "it", "mostly", "wear",
}


def _parse_query(query: str) -> dict:
    """
    Pull a description, optional size, and optional max_price out of a free-text
    query using simple regex/keyword rules.

    Returns a dict: {"description": str, "size": str | None, "max_price": float | None}
    """
    text = query.lower()
    size = None
    max_price = None

    # max_price: "under $30", "below 40", "$25", "less than $20"
    price_match = re.search(r"(?:under|below|less than)\s*\$?\s*(\d+(?:\.\d+)?)", text)
    if not price_match:
        price_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", text)
    if price_match:
        max_price = float(price_match.group(1))

    # size: explicit "size M" / "size 8" / "size 8.5"
    size_match = re.search(r"size\s+([\w/.]+)", text)
    if size_match:
        size = size_match.group(1).upper()
    else:
        # standalone clothing size token (longest first so "xl" beats "l")
        for token in _SIZE_WORDS:
            if re.search(rf"\b{token}\b", text):
                size = token.upper()
                break

    # description: drop the price phrase, any "$30"/"size X" tokens, and filler
    # words so only the real garment keywords drive the search ranking.
    cleaned = re.sub(r"(?:under|below|less than)\s*\$?\s*\d+(?:\.\d+)?", " ", text)
    cleaned = re.sub(r"\$\s*\d+(?:\.\d+)?", " ", cleaned)
    cleaned = re.sub(r"size\s+[\w/.]+", " ", cleaned)
    words = [w for w in re.findall(r"[a-z0-9]+", cleaned) if w not in _STOPWORDS]
    description = " ".join(words) if words else query

    return {"description": description, "size": size, "max_price": max_price}


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    # Step 1: fresh session — the single source of truth for this interaction.
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into description / size / max_price.
    session["parsed"] = _parse_query(query)

    # Step 3: search listings with the parsed parameters.
    session["search_results"] = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )

    # BRANCH: if nothing matched, stop here. Do NOT call the styling tools.
    if not session["search_results"]:
        session["error"] = (
            "No listings matched your search — try different keywords, "
            "a larger size range, or a higher price."
        )
        return session

    # Step 4: select the top result (best relevance match).
    session["selected_item"] = session["search_results"][0]

    # Step 5: suggest an outfit using the selected item + wardrobe.
    session["outfit_suggestion"] = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=session["wardrobe"],
    )

    # Step 6: turn the outfit into a shareable fit card.
    session["fit_card"] = create_fit_card(
        outfit=session["outfit_suggestion"],
        new_item=session["selected_item"],
    )

    # Step 7: done.
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
