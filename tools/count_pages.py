"""Count PDF pages and report unreadable PDFs in the dataset."""

from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT = ROOT / "data" / "page_counts.csv"

rows = []
total_pages = 0
broken = 0

for pdf in DATA_DIR.rglob("*.pdf"):
    if "sample" in pdf.relative_to(DATA_DIR).parts:
        continue

    try:
        reader = PdfReader(str(pdf), strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("Encrypted PDF cannot be read")

        pages = len(reader.pages)
        rows.append({
            "filename": str(pdf.relative_to(ROOT)),
            "pages": pages,
            "status": "ok",
        })
        total_pages += pages
        print(f"OK: {pdf.name}: {pages} pages")

    except Exception as error:
        rows.append({
            "filename": str(pdf.relative_to(ROOT)),
            "pages": "",
            "status": f"broken: {error}",
        })
        broken += 1
        print(f"BROKEN: {pdf.name}: {error}")

import csv

with OUTPUT.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file, fieldnames=["filename", "pages", "status"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"\nPDF files scanned: {len(rows)}")
print(f"Total readable PDF pages: {total_pages}")
print(f"Broken/unreadable PDFs: {broken}")
print(f"Report saved to: {OUTPUT}")
