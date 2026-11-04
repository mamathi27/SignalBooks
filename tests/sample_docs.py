from reportlab.pdfgen import canvas


def create_sample_pdf(path, pages):
    """Create a small PDF with one text string per page."""
    pdf = canvas.Canvas(str(path))

    for page_text in pages:
        pdf.drawString(72, 750, page_text)
        pdf.showPage()

    pdf.save()
