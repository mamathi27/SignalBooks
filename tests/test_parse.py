import json

from app.ingest.clean import clean_text
from app.ingest.parse import extract_headings, parse_directory, parse_pdf
from tests.sample_docs import create_sample_pdf


def test_clean_text_joins_broken_words_and_normalizes_whitespace():
    result = clean_text("inter-\nnational\n\n\nfinancial report")
    assert result == "international\n\nfinancial report"


def test_extract_headings_detects_uppercase_heading():
    assert extract_headings("QUARTERLY FINANCIAL RESULTS\nOther content") == [
        "QUARTERLY FINANCIAL RESULTS"
    ]


def test_extract_headings_ignores_contact_details():
    assert extract_headings("Contact us at example@company.com\nOrdinary paragraph") == []


def test_parse_pdf_creates_records_and_inherits_heading(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    create_sample_pdf(pdf_path, ["QUARTERLY FINANCIAL RESULTS", "Revenue increased"])
    records = parse_pdf(pdf_path, tmp_path)

    assert len(records) == 2
    assert records[0]["page"] == 1
    assert records[1]["page"] == 2
    assert records[0]["headings"] == ["QUARTERLY FINANCIAL RESULTS"]
    assert records[1]["headings"] == records[0]["headings"]
    assert set(records[0]) == {
        "doc_id", "source_file", "page", "headings", "text", "tables", "method"
    }


def test_parse_directory_writes_jsonl(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    create_sample_pdf(input_dir / "sample.pdf", ["FINANCIAL RESULTS"])
    output_file = tmp_path / "output" / "pages.jsonl"

    parse_directory(input_dir, output_file)

    records = [
        json.loads(line)
        for line in output_file.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 1
    assert records[0]["source_file"] == "sample.pdf"
    assert records[0]["method"] == "text"
