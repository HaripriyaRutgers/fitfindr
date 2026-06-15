# FitFindr 🛍️

FitFindr is a fashion assistant agent that helps you shop secondhand. You describe what you're looking for, and it searches a dataset of thrift listings, picks the best match, suggests how to style it with clothes you already own, and writes a little Instagram-style caption for the look. It uses three tools wired together by a planning loop, plus the Groq LLM for the styling parts.

## Setup

```bash
pip install -r requirements.txt
```

Put your Groq API key in a `.env` file in the project root (free key at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Then run it:

```bash
python app.py          # launch the Gradio UI (open the localhost URL it prints)
python agent.py        # run the two built-in test interactions in the terminal
pytest                 # run the tool tests
```

> **Note on Python version:** this project runs on Python 3.9, so `requirements.txt` pins `gradio==4.44.1` (gradio 6.x needs Python 3.10+). If you upgrade to 3.10+, you can bump gradio.

## Tool Inventory

| Tool | Inputs | Returns | What it's for |
|------|--------|---------|---------------|
| **`search_listings`** | `description: str`, `size: str \| None`, `max_price: float \| None` | A `list[dict]` of matching listings, sorted by relevance (best first). Each listing dict has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. | Finds clothing items in the dataset that match the user's keywords, filtered by size and price if those were given. |
| **`suggest_outfit`** | `new_item: dict` (a listing), `wardrobe: dict` (has an `"items"` list) | A `str` — a plain-English outfit idea from the LLM that pairs the new item with named pieces from the wardrobe. | Styles the found item using clothes the user already owns. |
| **`create_fit_card`** | `outfit: str`, `new_item: dict` | A `str` — a short, casual Instagram-style caption (under 100 words). | Turns the outfit idea into something shareable for an OOTD post. |

A quick note on keys: the listings in the dataset use `title` (not `name`). `suggest_outfit` and `create_fit_card` check for `name` first and fall back to `title`, so they work whether you hand them a listing or a wardrobe item.

## Planning Loop

The agent doesn't blindly call all three tools every time — it looks at what each step returns and decides whether to keep going. The logic lives in `run_agent()` in `agent.py`:

1. **Parse the query** into a description, an optional size, and an optional max price (regex + keyword matching — e.g. "under $30" → `max_price=30.0`, "size M" → `size="M"`).
2. **Run `search_listings`** with those parameters.
3. **Branch on the search result.** If it comes back as an empty list, the agent stops right here: it sets an error message telling the user nothing matched and to try different keywords or a higher price, and returns early. **It does not call `suggest_outfit` or `create_fit_card`** — there's no item to style, so running them would either crash or produce nonsense.
4. **If there are results**, pick the top one (highest relevance) as the item to work with.
5. **Run `suggest_outfit`** on that item plus the user's wardrobe.
6. **Run `create_fit_card`** on the outfit suggestion.
7. **Return** the finished session.

So the one place the agent stops early is when the search finds nothing. That's the test that proves the planning loop actually works: a no-results query (like "designer ballgown size XXS under $5") produces an error and a `None` fit card, while a real query goes all the way through to a caption.

## State Management

Everything for one interaction lives in a single **session dictionary** created at the start of `run_agent()`. Each step writes its result into the session, and the next step reads what it needs from there — the user never re-enters anything mid-run. The session tracks:

- `query` — the original text the user typed
- `parsed` — the description / size / max_price pulled out of the query
- `search_results` — the list returned by `search_listings`
- `selected_item` — the top search result, which gets passed straight into `suggest_outfit`
- `outfit_suggestion` — the string `suggest_outfit` returned, which gets passed straight into `create_fit_card`
- `fit_card` — the final caption
- `error` — stays `None` unless the run stopped early

The important part is that state flows by reference: the exact `selected_item` dict stored in the session is the same object handed to `suggest_outfit`, and the exact `outfit_suggestion` string is the same one handed to `create_fit_card`. Nothing gets re-derived or re-typed between steps.

## Error Handling

**`search_listings` — no matches.** If nothing in the dataset matches the keywords (after applying the size and price filters), it returns an empty list `[]` instead of crashing. The planning loop catches that empty list and tells the user: *"No listings matched your search — try different keywords, a larger size range, or a higher price."* Then it stops.

**`suggest_outfit` — empty wardrobe.** If `wardrobe["items"]` is empty, the tool doesn't bother calling the LLM. It returns *"Your wardrobe is empty — try adding some items first!"* The agent keeps running with that message as the "outfit" so the interaction still finishes cleanly.

**`create_fit_card` — missing outfit.** If the `outfit` string is empty or `None`, it returns *"Cannot create a fit card without an outfit description."* instead of calling the LLM or raising an exception.

## Spec Reflection

**One thing planning.md caught:** Writing out the planning loop on paper first is what made me put the early-return on empty search results. Before that I was just going to call the three tools in a row. Mapping out the "what if search returns nothing?" branch made it obvious that handing an empty list to `suggest_outfit` would either crash or make the LLM hallucinate an outfit for an item that doesn't exist. So the branch came from the planning step, not from hitting a bug later.

**One thing that diverged:** My planning notes assumed an empty wardrobe should *stop* the agent and ask the user to add items, the same way an empty search does. When I actually built it, I made `suggest_outfit` return its fallback message and let the loop keep going to still produce a fit card. Stopping felt like worse UX — a brand-new user with an empty closet should still get *something* back, not a dead end. So the empty-wardrobe case is a soft fallback, while empty-search is the only real hard stop.

## AI Usage

I used Claude to help build two of the tools, and reviewed everything before trusting it:

- **`search_listings`:** I gave Claude the function spec (inputs, return value, failure mode) and the existing stub from `tools.py`. I checked that it used `load_listings()` instead of re-writing the file-reading logic, which it did. I did have to fix the filtering — its first version used exact string matching, so "vintage tee" wouldn't match "Vintage Graphic Tee." I had it switch to case-insensitive substring matching so partial keywords work.

- **`create_fit_card`:** I gave it the stub and spec. Its first version set the LLM temperature to 0.7, so I explicitly asked for 0.9 so the captions actually vary between runs instead of sounding the same. I also double-checked the empty-outfit guard returned the error string instead of raising an exception, which it did correctly.

## Project Files

```
fitfindr/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # helpers for loading the data
├── tools.py                   # the three tools
├── agent.py                   # the planning loop (run_agent)
├── app.py                     # Gradio UI
├── tests/
│   └── test_tools.py          # tool tests
├── planning.md                # design doc, filled out before coding
└── requirements.txt
```
