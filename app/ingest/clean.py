import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalize extracted document text while preserving meaningful content."""
    text = unicodedata.normalize("NFKC", text)

    # Remove invisible control characters, but preserve ZWJ and newlines.
    text = "".join(
        char
        for char in text
        if char in "\n\t\u200d" or unicodedata.category(char) != "Cf"
    )

    # Join words split across lines by PDF line wrapping.
    text = re.sub(r"(?<=[A-Za-z])-\s*\n\s*(?=[a-z])", "", text)

    # Normalize horizontal whitespace and excessive blank lines.
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()