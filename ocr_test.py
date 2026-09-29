from PIL import Image
import pytesseract

image_path = r"C:\pharmacy_rag_mcp\data\medicines\paracetamol.png"

# Tell Python where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = r"C:\Tesseract-OCR\tesseract.exe"

# Open image
image = Image.open(image_path)

# Extract text using OCR
text = pytesseract.image_to_string(image)

print("\n========== OCR RESULT ==========\n")
print(text)