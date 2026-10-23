
"""Polite downloader for the SignalBooks dataset.

Usage:
    python tools/download.py

Reads one URL per line from urls.txt.
Downloads files into data/raw/ and records metadata in data/manifest.csv.
"""

import csv
import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.robotparser import RobotFileParser

import requests

ROOT = Path(__file__).resolve().parents[1]
URLS_FILE = ROOT / "urls.txt"
RAW_DIR = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifest.csv"
DELAY = 2

HEADERS = {
    "User-Agent": (
        "SignalBooksStudentProject/1.0 "
        "(educational research; contact: add-your-email)"
    )
}

FIELDS = [
    "filename",
    "source_url",
    "downloaded_on",
    "bytes",
    "sha256",
    "status",
]

robots_cache = {}


def allowed_by_robots(url):
    """Check robots.txt before requesting a URL."""
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin not in robots_cache:
        parser = RobotFileParser()
        parser.set_url(f"{origin}/robots.txt")

        try:
            response = requests.get(
                parser.url, headers=HEADERS, timeout=15
            )
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
                robots_cache[origin] = parser
            else:
                robots_cache[origin] = None
        except requests.RequestException:
            robots_cache[origin] = None

    parser = robots_cache[origin]

    # If robots.txt cannot be checked, fail closed.
    if parser is None:
        print(f"SKIP: Could not verify robots.txt for {origin}")
        return False

    return parser.can_fetch(HEADERS["User-Agent"], url)


def filename_for(url):
    name = unquote(Path(urlparse(url).path).name)
    return name or "downloaded-file"


def load_manifest():
    records = {}

    if MANIFEST.exists():
        with MANIFEST.open("r", newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                if row.get("status") == "downloaded":
                    records[row.get("source_url", "")] = row

    return records


def write_manifest(records):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)

    with MANIFEST.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records.values())


def main():
    if not URLS_FILE.exists():
        raise SystemExit("ERROR: urls.txt was not found.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    records = load_manifest()

    urls = []
    for line in URLS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)

    if not urls:
        raise SystemExit("ERROR: urls.txt contains no URLs.")

    with requests.Session() as session:
        session.headers.update(HEADERS)

        for url in urls:
            parsed = urlparse(url)

            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                print(f"SKIP: Invalid URL: {url}")
                continue

            if url in records and (RAW_DIR / records[url]["filename"]).exists():
                print(f"SKIP: Already recorded: {url}")
                continue

            if not allowed_by_robots(url):
                print(f"SKIP: Not downloading: {url}")
                continue

            try:
                with session.get(
                    url, stream=True, timeout=30, allow_redirects=True
                ) as response:
                    response.raise_for_status()

                    content_type = response.headers.get(
                        "Content-Type", ""
                    ).lower()

                    # This version downloads direct files only.
                    if (
                        "text/html" in content_type
                        or "application/xhtml+xml" in content_type
                    ):
                        print(
                            "SKIP: This URL returns a webpage, not a file. "
                            f"Find the official document link: {url}"
                        )
                        continue

                    filename = filename_for(response.url)
                    destination = RAW_DIR / filename

                    # Avoid overwriting an existing file.
                    if destination.exists():
                        stem = destination.stem
                        suffix = destination.suffix
                        destination = RAW_DIR / f"{stem}_{len(records)+1}{suffix}"
                        filename = destination.name

                    digest = hashlib.sha256()
                    byte_count = 0

                    with destination.open("wb") as output:
                        for chunk in response.iter_content(64 * 1024):
                            if chunk:
                                output.write(chunk)
                                digest.update(chunk)
                                byte_count += len(chunk)

                    records[url] = {
                        "filename": filename,
                        "source_url": url,
                        "downloaded_on": datetime.now(
                            UTC
                        ).isoformat(),
                        "bytes": byte_count,
                        "sha256": digest.hexdigest(),
                        "status": "downloaded",
                    }
                    write_manifest(records)
                    print(f"OK: {filename} ({byte_count} bytes)")

            except (requests.RequestException, OSError) as error:
                print(f"ERROR: {url}: {error}")

            time.sleep(DELAY)

    print(f"\nManifest: {MANIFEST}")
    print(f"Raw files: {RAW_DIR}")


if __name__ == "__main__":
    main()
