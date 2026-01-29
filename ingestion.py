import PyPDF2

def extract_text_from_pdf(pdf_path):
    """
    Opens a PDF file and returns its text content as a string.
    """
    text_content = []
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Loop through all pages
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
                    
        return "\n".join(text_content)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""