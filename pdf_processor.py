from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using pypdf.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        tuple: (Extracted text, Number of pages)
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        num_pages = len(reader.pages)
        for page in reader.pages:
            text += page.extract_text()
        return text, num_pages
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

if __name__ == "__main__":
    pass
