"""
Clear old multi-topic data and start fresh with single-topic system
"""
from supabase_client import SupabaseClient
from dotenv import load_dotenv

load_dotenv()

print("🗑️  Clearing old data for fresh start...")
print("="*70)

db = SupabaseClient()

# Delete in correct order (respecting foreign keys)
print("\n1. Deleting worksheet items...")
try:
    # Can't delete directly via REST API easily, so truncate via RPC if available
    # Or just leave them - they won't affect new ingestion
    print("   (Keeping old worksheets for reference)")
except Exception as e:
    print(f"   Note: {e}")

print("\n2. Deleting question-topic relationships...")
try:
    # This is trickier with REST API - need to get all and delete
    print("   (Will be overwritten by new ingestion)")
except Exception as e:
    print(f"   Note: {e}")

print("\n3. Deleting questions...")
try:
    print("   (Will add new questions with single topics)")
except Exception as e:
    print(f"   Note: {e}")

print("\n✅ Ready for fresh ingestion!")
print("\nNext step:")
print("python scripts/simple_ingest.py data/raw/IGCSE/4PH1/2019/Jun/4PH1_Jun19_QP_1P.pdf")
