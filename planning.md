# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
My tool basically searches and looks through the existing listings to return 3 matching listings/ items which are sorted by relavance based on the User's input.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Key words from the users input of what they want basically
- `size` (str): size of the item (S, M, L,XL etc)
- `max_price` (float): the maximum cap of the price set by the user

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
This tool returns three most relavant listings related to the user's input. It also returns the place where the listing is on along with the condition of the item. Each listing is a dict with: id, title, description, category, style_tags, size, condition, price, colors, brand, and platform (depop / thredUp / poshmark).

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If the listings dont match, output that "lisings not found, try something else". The tool itself just returns an empty list (no crashing), and the agent turns that empty list into the friendly message.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
It takes the item the user found and looks at the clothes already in their closet (wardrobe), then asks the LLM to put together 1-2 full outfits that mix the new item with stuff they already own.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): the listing the user is thinking about buying (the top result from search_listings).
- `wardrobe` (dict): the user's closet — a dict with an `items` key that holds a list of their clothes (each has name, category, colors, style_tags, notes).

**What it returns:**
<!-- Describe the return value -->
A string of text describing 1-2 outfit ideas that pair the new item with specific pieces from the wardrobe (called out by name).

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the wardrobe is empty (a new user with no clothes saved), it doesn't error out — instead it asks the LLM for general styling advice for that item (what kinds of pieces and vibe go well with it). It always returns a non-empty string.

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
It turns the outfit idea into a short, casual social-media style caption (like an OOTD post for Instagram or TikTok) about the thrifted find.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): the outfit suggestion text that came back from suggest_outfit.
- `new_item` (dict): the listing dict for the thrifted item, so the caption can mention its name, price, and platform.

**What it returns:**
<!-- Describe the return value -->
A short 2-4 sentence string that sounds like a real OOTD caption, naturally mentioning the item name, its price, and where it's from.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the `outfit` string is empty or just blank spaces, it returns a clear error message string instead of a caption — it does not crash or raise an exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->
None — I'm sticking with the three required tools.

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
My agent runs the three tools in a fixed order, one after another, and uses the results to decide whether to keep going or stop early:

1. First it reads the user's query and pulls out the description, size, and max_price.
2. It calls `search_listings` with those. **If nothing comes back (empty list), it stops here** and sets an error message — there's no point styling an item that doesn't exist.
3. If there are results, it picks the top one (best match) as the item to style and calls `suggest_outfit`.
4. Then it calls `create_fit_card` on that outfit.
5. It's done once the fit card is made. The whole thing is one straight path, and the only place it branches is the "no listings found" exit.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
Everything lives in one `session` dictionary that I create at the start of each run (with `_new_session`). Each step writes its result into the session, and the next step reads what it needs from there. The session tracks:
- `query` — the original text the user typed
- `parsed` — the description / size / max_price I pulled out of the query
- `search_results` — the list of matching listings
- `selected_item` — the top result, which gets passed into suggest_outfit
- `wardrobe` — the user's closet
- `outfit_suggestion` — the text from suggest_outfit
- `fit_card` — the final caption
- `error` — stays None unless something stops the run early

So instead of passing a bunch of variables around, each tool's output is saved in the session and the next tool grabs it from there.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Stops the loop early, sets `session["error"]` to a friendly "no listings found, try something else" message, and does NOT call the other tools. |
| suggest_outfit | Wardrobe is empty | Doesn't crash — gives general styling advice for the item instead of outfits built from specific closet pieces. |
| create_fit_card | Outfit input is missing or incomplete | Returns a plain error message string instead of a caption, so the run still finishes cleanly. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect -->

```
        User query ("vintage graphic tee under $30, size M")
                              |
                              v
                  +-----------------------+
                  |   Planning Loop       |
                  |   (run_agent)         | <----> session dict (state)
                  +-----------------------+        - query, parsed
                              |                     - search_results
                              v                     - selected_item
                  [1] search_listings               - wardrobe
                              |                      - outfit_suggestion
                  empty? --YES--> set error,        - fit_card
                              |    STOP & return     - error
                              NO
                              v
                  [2] suggest_outfit  (empty wardrobe -> general advice)
                              |
                              v
                  [3] create_fit_card (blank outfit -> error message)
                              |
                              v
                  Final session returned to the UI (app.py)
```

---

## AI Tool Plan

<!-- For each part of the implementation, describe the tool, input, expected output, and how you'll verify it. -->

**Milestone 3 — Individual tool implementations:**
I'll use Claude (in Claude Code). For each tool I'll paste that tool's section from this planning.md (inputs, return value, failure mode) plus the matching docstring/TODO already in `tools.py`, and ask it to implement just that one function using `load_listings()` from the data loader for search_listings and the Groq LLM client for the other two. I'll verify each tool on its own before trusting it:
- `search_listings`: test 3 queries — one that clearly matches ("vintage denim"), one with a price cap, and one nonsense query that should return an empty list.
- `suggest_outfit`: test once with the example wardrobe and once with the empty wardrobe to make sure both paths give a non-empty string.
- `create_fit_card`: test with a real outfit string, and with an empty string to confirm I get the error message, not a crash.

**Milestone 4 — Planning loop and state management:**
I'll give Claude the Planning Loop, State Management, and Architecture sections above plus the TODO in `agent.py`, and ask it to fill in `run_agent` so it follows the exact step order and the early-exit on no results. To verify, I'll run `python agent.py`, which already has a happy-path test (graphic tee) and a no-results test (designer ballgown) — the first should print an item, outfit, and fit card; the second should print only the error message.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? -->
The agent parses the query into: description = "vintage graphic tee", size = None (not given), max_price = 30. It saves this in `session["parsed"]` and calls `search_listings("vintage graphic tee", None, 30)`.

**Step 2:**
<!-- What happens next? -->
search_listings returns a list of matching tees under $30, sorted best-match first, into `session["search_results"]`. The agent picks the top one (say a vintage band tee, $24, from depop) as `session["selected_item"]` and calls `suggest_outfit(selected_item, wardrobe)`.

**Step 3:**
<!-- Continue until done -->
suggest_outfit looks at the example wardrobe (baggy jeans, etc.) and returns outfit text like "Pair the band tee with your baggy dark-wash jeans and chunky sneakers for an easy streetwear look." That's saved in `session["outfit_suggestion"]`. Then the agent calls `create_fit_card(outfit_suggestion, selected_item)`, which writes a short caption and stores it in `session["fit_card"]`. The agent returns the session.

**Final output to user:**
<!-- What does the user actually see? -->
In the UI the user sees three panels: (1) the matching listing(s) with price, platform, and condition, (2) the outfit suggestion built from their wardrobe, and (3) the shareable fit-card caption for the thrifted find.
