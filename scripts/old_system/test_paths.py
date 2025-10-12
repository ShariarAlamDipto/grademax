"""
Test different path formats to find what works
"""
from supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()

db_client = SupabaseClient()
pdf_path = "data\\processed\\4PH1_2019_Jun_1P\\pages\\q2.pdf"

test_paths = [
    "test/q2.pdf",  # Known working
    "2019_Jun_1P_Q2.pdf",  # Flat structure
    "2019/q2.pdf",  # One level
    "2019/Jun/q2.pdf",  # Two levels
    "2019/Jun/1P/Q2.pdf",  # Three levels (pipeline format)
    "papers/2019_Jun_1P/Q2.pdf",  # Alternative structure
]

print("Testing path formats:\n")

for dest_path in test_paths:
    try:
        result = db_client.upload_file(
            bucket='question-pdfs',
            file_path=pdf_path,
            destination_path=dest_path
        )
        print(f"✅ {dest_path}")
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "row-level security" in error_msg:
            print(f"❌ {dest_path} - RLS blocked")
        else:
            print(f"❌ {dest_path} - {error_msg[:50]}")
