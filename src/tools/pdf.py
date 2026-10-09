import io
import json
import urllib.request
from google.genai import types

def read_pdf_url(url: str) -> str:
    """Download and extract text from a PDF URL."""
    try:
        import PyPDF2
        
        # Use a standard urllib request to grab the PDF bytes
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            pdf_bytes = response.read()
            
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PyPDF2.PdfReader(pdf_file)
        
        # Extract text from all pages (capped at 50 to avoid token blowouts)
        text_content = ""
        for i in range(min(50, len(reader.pages))):
            page = reader.pages[i]
            text = page.extract_text()
            if text:
                text_content += text + "\n\n"
                
        if not text_content.strip():
            return json.dumps({"error": "No extractable text found in this PDF."})
            
        return text_content[:30_000] # Hard cap to avoid context window explosion
        
    except Exception as e:
        return json.dumps({"error": f"Failed to read PDF: {e}"})

PDF_DECLARATION = types.FunctionDeclaration(
    name="read_pdf_url",
    description="Download and read the text content of a PDF file from a given URL.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The direct URL to the PDF file."},
        },
        "required": ["url"],
    },
)
