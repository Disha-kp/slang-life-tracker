"""
Urban Dictionary lookup
------------------------
Provides real slang definitions via Urban Dictionary's free, unauthenticated
public API. This replaces relying on incidental " is a " / " means " phrasing
inside random Reddit post text, which almost never naturally occurs and was
the actual reason most words came back as "Deep search returned no results."

API docs (unofficial but stable and widely used):
    GET https://api.urbandictionary.com/v0/define?term={word}
"""

import requests

UD_API_URL = "https://api.urbandictionary.com/v0/define"


def fetch_definition(word: str, timeout: int = 8):
    """
    Look up a word on Urban Dictionary.

    Returns a cleaned definition string (max ~300 chars), or None if the
    word wasn't found, the request failed, or the response was malformed.
    Never raises — callers can always fall back to another source.
    """
    word = (word or "").strip()
    if not word:
        return None

    try:
        response = requests.get(UD_API_URL, params={"term": word}, timeout=timeout)
        if response.status_code != 200:
            return None

        data = response.json()
        entries = data.get("list", [])
        if not entries:
            return None

        # Urban Dictionary's API doesn't always return entries pre-sorted by
        # score, so pick the entry with the best (thumbs_up - thumbs_down).
        best = max(entries, key=lambda e: e.get("thumbs_up", 0) - e.get("thumbs_down", 0))
        definition = best.get("definition", "")
        if not isinstance(definition, str):
            return None

        # Urban Dictionary uses [brackets] to link related terms within the
        # definition text — strip them so the brackets don't show up raw.
        definition = definition.replace("[", "").replace("]", "")
        definition = definition.replace("\r\n", " ").replace("\n", " ").strip()

        if not definition:
            return None
        if len(definition) > 300:
            definition = definition[:297] + "..."

        return definition

    except Exception:
        # Network error, timeout, malformed JSON, etc. — treat as "not found"
        # rather than raising, since this is just one of several fallback
        # definition sources.
        return None
