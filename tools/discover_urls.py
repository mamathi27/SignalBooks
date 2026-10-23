import csv
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

ROOT = Path(__file__).resolve().parents[1]
URLS_FILE = ROOT / "urls.txt"
OUTPUT = ROOT / "data" / "discovered_urls.csv"
DELAY = 2

HEADERS = {
    "User-Agent": "SignalBooksStudentProject/1.0 (educational research)"
}
EXTENSIONS = (".pdf", ".xlsx", ".xls", ".csv")
session = requests.Session()
session.headers.update(HEADERS)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            attrs = dict(attrs)
            href = attrs.get("href")
            if href:
                self.links.append((href, attrs.get("title", "")))


def allowed_by_robots(url):
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"

    try:
        response = session.get(robots_url, timeout=15)
        if response.status_code != 200:
            print(f"SKIP: Cannot verify robots.txt: {robots_url}")
            return False

        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser.can_fetch(HEADERS["User-Agent"], url)
    except requests.RequestException:
        print(f"SKIP: Cannot check robots.txt: {robots_url}")
        return False


def main():
    if not URLS_FILE.exists():
        raise SystemExit("ERROR: urls.txt not found.")

    seeds = [
        line.strip()
        for line in URLS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    found = {}

    for page_url in seeds:
        print(f"\nChecking: {page_url}")

        if not allowed_by_robots(page_url):
            continue

        try:
            response = session.get(page_url, timeout=25)
            response.raise_for_status()

            if "html" not in response.headers.get("Content-Type", "").lower():
                print("SKIP: Seed URL did not return HTML.")
                continue

            parser = LinkParser()
            parser.feed(response.text)

            for href, title in parser.links:
                link = urldefrag(urljoin(response.url, href))[0]
                parsed = urlparse(link)
                path = parsed.path.lower()

                if parsed.scheme not in ("http", "https"):
                    continue

                if path.endswith(EXTENSIONS):
                    found[link] = {
                        "document_url": link,
                        "found_on_page": page_url,
                        "link_text": title,
                        "extension": Path(path).suffix.lower(),
                    }

            print("Links checked.")
        except requests.RequestException as error:
            print(f"ERROR: {error}")

        time.sleep(DELAY)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        fields = [
            "document_url", "found_on_page", "link_text", "extension"
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(found.values())

    print(f"\nCandidate links found: {len(found)}")
    print(f"Review the results in: {OUTPUT}")
    print("These are candidates only; they have not been downloaded.")


if __name__ == "__main__":
    main()
