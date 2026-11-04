import argparse
import json
import os
import re
from pathlib import Path

import pdfplumber
import pytesseract

from app.ingest.clean import clean_text

TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)
OCR_LANG = os.getenv("OCR_LANG", "eng")

if Path(TESSERACT_CMD).is_file():
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def extract_headings(text: str) -> list[str]:
    """Identify the primary heading from the beginning of page body text."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    # Recognize the financial statement title in scanned company reports.
    for line in lines:
        if line.lower().startswith("statement of unaudited consolidated financial results"):
            return [line]

    # Recognize the auditor report heading split across OCR lines.
    if (
        len(lines) >= 3
        and lines[0].startswith("Price Waterhouse")
        and "Auditors" in lines[1]
    ):
        return [f"{lines[1]} {lines[2]}"]

    for line in lines[:15]:
        if not line or len(line) > 120:
            continue

        if line.startswith(("?", "?", "-", "?")):
            continue
        if re.match(r"^\d+[\.)]?\s+", line):
            continue
        date_pattern = (
            r"\b(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b"
        )
        if re.search(date_pattern, line, re.I):
            continue
        if "@" in line or line.lower().startswith("contact us"):
            continue
        if line.upper() in {"TEJAS", "NETWORKS", "TEJAS|", "ETWORKS"}:
            continue
        if line.lower() in {"tejas networks limited", "holding company", "subsidiaries"}:
            continue
        if line.lower().startswith(("registered office", "tel:", "fax:", "e-mail:", "email:", "website:")):
            continue
        if line.lower().startswith("tejas networks limited"):
            continue
        if line.lower().startswith("corporate identity number"):
            continue
        if any(term in line.lower() for term in ("village", "hobli", "bengaluru", "karnataka", "india.")):
            continue

        words = line.split()
        if len(words) <= 14 and (
            line.isupper()
            or ":" in line
            or " - " in line
            or (len(words) <= 10 and line.istitle())
        ):
            return [line]

    return []

def extract_tables_and_body(page):
    """Extract tables first, then remove their character regions from body text."""
    tables = []
    table_objects = page.find_tables()

    for table in table_objects:
        rows = table.extract()
        if rows:
            tables.append(rows)

    table_boxes = [table.bbox for table in table_objects]

    def outside_tables(obj):
        if obj.get("object_type") != "char":
            return True

        x = (obj["x0"] + obj["x1"]) / 2
        y = (obj["top"] + obj["bottom"]) / 2

        return not any(
            x0 <= x <= x1 and top <= y <= bottom
            for x0, top, x1, bottom in table_boxes
        )

    body_page = page.filter(outside_tables)
    body_text = body_page.extract_text() or ""

    return clean_text(body_text), tables


def extract_page_text(page):
    """Use native PDF text first and OCR only for likely scanned pages."""
    body_text, tables = extract_tables_and_body(page)
    native_text = clean_text(body_text)

    table_text = "\n".join(
        " | ".join(str(cell or "").strip() for cell in row)
        for table in tables
        for row in table
    )

    combined_text = "\n".join(
        part for part in (native_text, table_text) if part
    ).strip()

    if len(native_text) < 25 and len(page.images) > 0:
        try:
            image = page.to_image(resolution=300).original
            ocr_text = clean_text(
                pytesseract.image_to_string(image, lang=OCR_LANG)
            )

            if ocr_text:
                return ocr_text, tables, "ocr"

            return combined_text, tables, "needs_ocr"

        except (pytesseract.TesseractNotFoundError, OSError):
            return combined_text, tables, "needs_ocr"

    if combined_text:
        return combined_text, tables, "text"

    return "", tables, "empty"


def parse_pdf(pdf_path: Path, source_root: Path) -> list[dict]:
    """Parse a PDF into one structured record per page."""
    records = []
    doc_id = pdf_path.stem
    previous_headings = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text, tables, method = extract_page_text(page)

            headings = extract_headings(text)

            if headings:
                previous_headings = headings
            else:
                headings = previous_headings.copy()

            records.append(
                {
                    "doc_id": doc_id,
                    "source_file": pdf_path.relative_to(source_root).as_posix(),
                    "page": page_number,
                    "headings": headings,
                    "text": text,
                    "tables": tables,
                    "method": method,
                }
            )

    return records


def parse_directory(input_dir: Path, output_file: Path, limit: int | None = None):
    """Parse PDF files in a directory and write page records as JSONL."""
    input_dir = input_dir.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(input_dir.rglob("*.pdf"))

    if limit is not None:
        pdf_files = pdf_files[:limit]

    total_pages = 0
    method_counts = {
        "text": 0,
        "ocr": 0,
        "needs_ocr": 0,
        "empty": 0,
    }

    with output_file.open("w", encoding="utf-8") as output:
        for pdf_path in pdf_files:
            print(f"Parsing: {pdf_path.name}")

            try:
                records = parse_pdf(pdf_path, input_dir)

                for record in records:
                    output.write(
                        json.dumps(record, ensure_ascii=False) + "\n"
                    )
                    method_counts[record["method"]] += 1
                    total_pages += 1

            except Exception as error:
                print(f"Failed to parse {pdf_path.name}: {error}")

    print("\nParsing summary")
    print(f"PDF files processed: {len(pdf_files)}")
    print(f"Pages processed: {total_pages}")

    for method, count in method_counts.items():
        print(f"{method}: {count}")

    print(f"Output: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Parse PDF documents into JSONL.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--limit", type=int, default=None)

    args = parser.parse_args()

    parse_directory(
        input_dir=args.input_dir,
        output_file=Path("data/parsed/pages.jsonl"),
        limit=args.limit,
    )


if __name__ == "__main__":
    main()