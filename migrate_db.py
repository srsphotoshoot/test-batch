import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import create_engine, text

# Direct connection for migration (to avoid FATAL: Tenant or user not found on pooler 6543)
DIRECT_URL = "postgresql://postgres:7462879206%40Sonu@db.gsfgfscssagyifnwjuad.supabase.co:5432/postgres"
engine = create_engine(DIRECT_URL)

def run_migration():
    print("🚀 Running Database Migration...")
    try:
        with engine.connect() as conn:
            # 1. Add LargeBinary columns
            print("Adding BYTEA columns for binary performance...")
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS main_image_bin BYTEA;"))
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS ref1_image_bin BYTEA;"))
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS ref2_image_bin BYTEA;"))
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS generated_image_bin BYTEA;"))
            
            # 2. Add other missing columns (just in case they were missed in previous migrations)
            print("Ensuring replication columns exist...")
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS blouse_color VARCHAR(50) DEFAULT '#FFFFFF';"))
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS lehenga_color VARCHAR(50) DEFAULT '#FFFFFF';"))
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS dupatta_color VARCHAR(50) DEFAULT '#FFFFFF';"))
            conn.execute(text("ALTER TABLE batches ADD COLUMN IF NOT EXISTS aspect_ratio VARCHAR(50) DEFAULT '1:1';"))
            
            # 3. Add Indices for faster lookups (Optimizing Login & Dashboard)
            print("Creating performance indices...")
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_batch_status ON batches(status);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_batch_user_id ON batches(user_id);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_batch_created_at ON batches(created_at DESC);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);"))
            
            conn.commit()
            print("✅ Migration Successful!")
    except Exception as e:
        print(f"❌ Migration Failed: {str(e)}")
        # If it failed due to 'column already exists' on a DB that doesn't support IF NOT EXISTS, we handle it
        pass

if __name__ == "__main__":
    run_migration()
