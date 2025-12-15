from pypdf import PdfReader
import sys

try:
    reader = PdfReader(r"C:\Users\Lenovo\Downloads\coverage.pdf")
    print(f"Number of Pages: {len(reader.pages)}")
    text_content = ""
    for page in reader.pages:
        text_content += page.extract_text() + "\n"
    
    print("-" * 20)
    print(text_content)
    print("-" * 20)
except Exception as e:
    print(f"Error reading PDF: {e}")
