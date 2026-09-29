from pathlib import Path

from pypdf import PdfReader
from PIL import Image
import pytesseract
import pymupdf

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FOLDER = BASE_DIR / "data" / "medicines"
CHROMA_FOLDER = BASE_DIR / "chroma_db"

TESSERACT_PATH = r"C:\Tesseract-OCR\tesseract.exe"


# Tell pytesseract where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# -----------------------------
# LOAD DOCUMENTS
# -----------------------------
documents = []


# ============================================================
# 1. LOAD PDF DOCUMENTS
# ============================================================

for pdf_file in DATA_FOLDER.glob("*.pdf"):

    print(f"\nLoading PDF: {pdf_file.name}")

    reader = PdfReader(str(pdf_file))

    for page_number, page in enumerate(reader.pages):

        text = page.extract_text()

        # ----------------------------------------------------
        # Normal PDF text extraction
        # ----------------------------------------------------
        if text and text.strip():

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source": pdf_file.name,
                        "page": page_number + 1,
                        "extraction_method": "PDF text extraction"
                    }
                )
            )

            print(
                f"  Page {page_number + 1}: "
                f"Text extracted"
            )

        # ----------------------------------------------------
        # Scanned PDF page
        # If normal text extraction fails, use OCR
        # ----------------------------------------------------
        else:

            print(
                f"  Page {page_number + 1}: "
                f"No text found → OCR"
            )

            try:

                pdf_document = pymupdf.open(str(pdf_file))

                pdf_page = pdf_document[page_number]

                pixmap = pdf_page.get_pixmap(dpi=200)

                image = Image.frombytes(
                    "RGB",
                    [pixmap.width, pixmap.height],
                    pixmap.samples
                )

                ocr_text = pytesseract.image_to_string(
                    image,
                    lang="eng"
                )

                pdf_document.close()

                if ocr_text and ocr_text.strip():

                    documents.append(
                        Document(
                            page_content=ocr_text,
                            metadata={
                                "source": pdf_file.name,
                                "page": page_number + 1,
                                "extraction_method": "Tesseract OCR"
                            }
                        )
                    )

                    print(
                        f"  Page {page_number + 1}: "
                        f"OCR successful"
                    )

                else:

                    print(
                        f"  Page {page_number + 1}: "
                        f"OCR returned no text"
                    )

            except Exception as e:

                print(
                    f"  Page {page_number + 1}: "
                    f"OCR error: {e}"
                )


# ============================================================
# 2. LOAD IMAGE DOCUMENTS
# ============================================================

image_extensions = [
    "*.jpg",
    "*.jpeg",
    "*.png"
]


for pattern in image_extensions:

    for image_file in DATA_FOLDER.glob(pattern):

        print(f"\nLoading image: {image_file.name}")

        try:

            image = Image.open(image_file)

            ocr_text = pytesseract.image_to_string(
                image,
                lang="eng"
            )

            if ocr_text and ocr_text.strip():

                documents.append(
                    Document(
                        page_content=ocr_text,
                        metadata={
                            "source": image_file.name,
                            "page": 1,
                            "extraction_method": "Tesseract OCR"
                        }
                    )
                )

                print("  OCR successful")

            else:

                print("  OCR returned no text")

        except Exception as e:

            print(f"  OCR error: {e}")


# -----------------------------
# DOCUMENT COUNT
# -----------------------------
print(
    f"\nDocuments/pages loaded: "
    f"{len(documents)}"
)


# -----------------------------
# SPLIT INTO CHUNKS
# -----------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

chunks = text_splitter.split_documents(documents)

print(f"Total chunks: {len(chunks)}")


# -----------------------------
# EMBEDDING MODEL
# -----------------------------
print("\nLoading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# -----------------------------
# STORE IN CHROMADB
# -----------------------------
print("\nCreating ChromaDB...")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=str(CHROMA_FOLDER),
    collection_name="medicine_knowledge"
)


print("\n✅ RAG ingestion completed successfully!")

print(f"Stored {len(chunks)} chunks in ChromaDB.")