import json
import re
from typing import List, Optional


def extract_tag_text(html: str, tag: str, *, first: bool = False, strip_inner_html: bool = False) -> Optional[str] | List[str]:
    """
    Extract text inside <tag>...</tag> from an HTML/XML-ish string.

    - Handles attributes on the opening tag: <tag ...>
    - Works across newlines.
    - Avoids crossing into nested <tag> blocks (tempered dot).
    - Case-insensitive for the tag name.
    - If strip_inner_html=True, inner HTML tags are removed from the result(s).
    - By default returns a list of matches; with first=True returns the first match or None.
    """
    t = re.escape(tag)
    # Example for tag='plan' -> r"<plan\b[^>]*>((?:(?!</?plan\b).)*)</plan>"
    pattern = rf"<{t}\b[^>]*>((?:(?!</?{t}\b).)*)</{t}>"
    flags = re.IGNORECASE | re.DOTALL

    matches = re.findall(pattern, html, flags=flags)

    if strip_inner_html:
        matches = [re.sub(r"<[^>]+>", "", m) for m in matches]

    if first:
        return matches[0].strip() if matches else None
    return [m.strip() for m in matches]


def convert_to_sse_format(payload):
    return f"data: {json.dumps(payload)}\n\n"
