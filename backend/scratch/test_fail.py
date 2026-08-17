import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.services.pdf_service import pdf_service
from app.services.document_service import document_service

async def main():
    pdf_path = os.path.abspath("../uploads/pdfs/30e2f966-22a1-4d67-8cd6-c75d26b85c7d.pdf")
    print(f"Path: {pdf_path}")
    print(f"Exists: {os.path.exists(pdf_path)}")
    try:
        print("Running PDF OCR...")
        pdf_res = await pdf_service.process_pdf_ocr(pdf_path)
        ocr_text = pdf_res["full_text"]
        print("OCR Text length:", len(ocr_text))
        
        print("Running Document Analysis...")
        analysis_res = await document_service.analyze_document(ocr_text, "StudentbuspassApplication.pdf")
        import json
        print("Analysis Result:", json.dumps(analysis_res, indent=2, ensure_ascii=True))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
