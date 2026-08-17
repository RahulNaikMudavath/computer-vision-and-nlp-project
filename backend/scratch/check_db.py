import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads/document_ocr.db"))

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, original_filename, file_type, ocr_status, processing_status, uploaded_by, created_at FROM documents ORDER BY created_at DESC LIMIT 5;")
    print("Latest Documents:")
    for row in cursor.fetchall():
        print(row)
