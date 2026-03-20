
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import bcrypt
import jwt
from config import JWT_SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, SIGNUP_PASSKEY

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batches.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    try:
        # Batch Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                output_name TEXT NOT NULL,
                background TEXT,
                pose TEXT,
                resolution TEXT,
                dress_type TEXT,
                user_id INTEGER,
                status TEXT DEFAULT 'pending',
                error TEXT,
                created_at TEXT,
                images_json TEXT,
                generated_image_b64 TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Users Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT DEFAULT 'user',
                batch_count INTEGER DEFAULT 0,
                batch_limit INTEGER DEFAULT 50,
                created_at TEXT
            )
        """)

        # Signup Codes Table (for dynamic passkeys)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signup_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)

        conn.commit()

        # Migration: ensure required columns exist for older DBs
        try:
            existing = [r[1] for r in conn.execute("PRAGMA table_info('batches')").fetchall()]
            if 'user_id' not in existing:
                conn.execute("ALTER TABLE batches ADD COLUMN user_id INTEGER")
            if 'images_json' not in existing:
                conn.execute("ALTER TABLE batches ADD COLUMN images_json TEXT")
            if 'generated_image_b64' not in existing:
                conn.execute("ALTER TABLE batches ADD COLUMN generated_image_b64 TEXT")
            
            # Migration: add columns to users table
            user_cols = [r[1] for r in conn.execute("PRAGMA table_info('users')").fetchall()]
            if 'first_name' not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
            if 'last_name' not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
            if 'daily_uploads' not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN daily_uploads INTEGER DEFAULT 0")
            if 'daily_upload_limit' not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN daily_upload_limit INTEGER DEFAULT 100")
            if 'last_upload_date' not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN last_upload_date TEXT")
            
            # Ensure at least one active signup code exists
            active_code = conn.execute("SELECT code FROM signup_codes WHERE is_active = 1 LIMIT 1").fetchone()
            if not active_code:
                # Use environment SIGNUP_PASSKEY if available, otherwise random
                initial_code = SIGNUP_PASSKEY if SIGNUP_PASSKEY else ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                conn.execute(
                    "INSERT INTO signup_codes (code, is_active, created_at) VALUES (?, ?, ?)",
                    (initial_code, 1, datetime.utcnow().isoformat())
                )
            elif SIGNUP_PASSKEY:
                # If SIGNUP_PASSKEY is provided, ensure it's also an active code
                existing = conn.execute("SELECT id FROM signup_codes WHERE code = ?", (SIGNUP_PASSKEY,)).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO signup_codes (code, is_active, created_at) VALUES (?, ?, ?)",
                        (SIGNUP_PASSKEY, 1, datetime.utcnow().isoformat())
                    )

            # Ensure initial admin user exists
            admin_user = conn.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
            if not admin_user and ADMIN_EMAIL and ADMIN_PASSWORD:
                hashed_pw = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                conn.execute(
                    "INSERT INTO users (email, password, first_name, last_name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (ADMIN_EMAIL, hashed_pw, "Admin", "User", "admin", datetime.utcnow().isoformat())
                )
                print(f"✅ Initial admin user created: {ADMIN_EMAIL}")

            conn.commit()
        except Exception as e:
            # If pragma fails (e.g., empty DB), ignore and continue
            print(f"⚠️  Database migration/init warning: {str(e)}")
            pass
    finally:
        conn.close()


# -----------------------
# USER FUNCTIONS
# -----------------------

def create_user(email: str, password: str, first_name: str = None, last_name: str = None, role: str = "user"):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (email, password, first_name, last_name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (email, hashed_password, first_name, last_name, role, datetime.utcnow().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def get_user(email: str, password: str) -> Optional[Dict]:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        if row and bcrypt.checkpw(password.encode('utf-8'), row["password"].encode('utf-8')):
            return dict(row)
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_jwt_token(user: Dict) -> str:
    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=24)  # 24 hours
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def verify_jwt_token(token: str) -> Optional[Dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_all_users() -> List[Dict]:
    conn = get_db()
    try:
        rows = conn.execute("SELECT id, email, first_name, last_name, role, batch_count, batch_limit, created_at FROM users ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return []
    finally:
        conn.close()


def update_user_role(user_id: int, role: str):
    conn = get_db()
    try:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
    finally:
        conn.close()


def delete_user(user_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# -----------------------
# BATCH FUNCTIONS
# -----------------------

def save_batch(batch_data: Dict):
    conn = get_db()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO batches 
            (id, output_name, background, pose, resolution, dress_type, user_id, status, error, created_at, images_json, generated_image_b64)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_data["id"],
            batch_data["output_name"],
            batch_data.get("background"),
            batch_data.get("pose"),
            batch_data.get("resolution"),
            batch_data.get("dress_type", "Normal Mode"),
            batch_data.get("user_id"),
            batch_data["status"],
            batch_data.get("error"),
            batch_data["created_at"],
            json.dumps(batch_data.get("images", {})),
            batch_data.get("generated_image")
        ))
        conn.commit()
    finally:
        conn.close()


def get_batch(batch_id: str) -> Optional[Dict]:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM batches WHERE id = ?",
            (batch_id,)
        ).fetchone()
        if not row:
            return None
        batch = dict(row)
        batch["images"] = json.loads(batch["images_json"]) if batch["images_json"] else {
            "main": None,
            "ref1": None,
            "ref2": None
        }
        batch["generated_image"] = batch["generated_image_b64"]
        return batch
    finally:
        conn.close()


def list_batches() -> List[Dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM batches ORDER BY created_at DESC"
        ).fetchall()
        batches = []
        for row in rows:
            batch = dict(row)
            if "generated_image_b64" in batch:
                del batch["generated_image_b64"]
            if "images_json" in batch:
                del batch["images_json"]
            batches.append(batch)
        return batches
    finally:
        conn.close()


def list_user_batches(user_id: int) -> List[Dict]:
    """Get batches created by a specific user"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM batches WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        batches = []
        for row in rows:
            batch = dict(row)
            if "generated_image_b64" in batch:
                del batch["generated_image_b64"]
            if "images_json" in batch:
                del batch["images_json"]
            batches.append(batch)
        return batches
    finally:
        conn.close()


def delete_batch(batch_id: str):
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM batches WHERE id = ?",
            (batch_id,)
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------
# QUEUE SYSTEM
# -----------------------

def get_next_queued_batch() -> Optional[str]:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM batches WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_queue_position(batch_id: str) -> int:
    conn = get_db()
    try:
        batch = conn.execute(
            "SELECT created_at FROM batches WHERE id = ?",
            (batch_id,)
        ).fetchone()
        if not batch:
            return -1
        count = conn.execute(
            "SELECT COUNT(*) FROM batches WHERE status = 'queued' AND created_at < ?",
            (batch["created_at"],)
        ).fetchone()[0]
        return count + 1
    finally:
        conn.close()


def get_queue_status() -> Dict:
    conn = get_db()
    try:
        # count pending + queued as queue
        queued = conn.execute(
            "SELECT COUNT(*) FROM batches WHERE status IN ('pending','queued')"
        ).fetchone()[0]
        generating = conn.execute(
            "SELECT COUNT(*) FROM batches WHERE status = 'generating'"
        ).fetchone()[0]
        return {
            "queued": queued,
            "generating": generating
        }
    finally:
        conn.close()


# -----------------------
# USER LIMITS & QUOTAS
# -----------------------

def get_batch_count(user_id: int) -> int:
    """Get current batch count for user"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT batch_count FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return row["batch_count"] if row else 0
    finally:
        conn.close()


def get_batch_limit(user_id: int) -> int:
    """Get batch limit for user"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT batch_limit FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        return row["batch_limit"] if row else 50
    finally:
        conn.close()


def increment_batch_count(user_id: int):
    """Increment batch count for user"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET batch_count = batch_count + 1 WHERE id = ?",
            (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


def check_daily_upload_limit(user_id: int) -> Dict:
    """Check if user has remaining daily uploads"""
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT daily_uploads, daily_upload_limit, last_upload_date FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        
        if not user:
            return {"allowed": False, "reason": "User not found"}
        
        today = datetime.utcnow().date().isoformat()
        last_upload = user["last_upload_date"]
        
        # Reset daily counter if it's a new day
        if last_upload != today:
            conn.execute(
                "UPDATE users SET daily_uploads = 0, last_upload_date = ? WHERE id = ?",
                (today, user_id)
            )
            conn.commit()
            daily_uploads = 0
        else:
            daily_uploads = user["daily_uploads"] or 0
        
        daily_limit = user["daily_upload_limit"] or 100
        
        if daily_uploads >= daily_limit:
            return {
                "allowed": False,
                "reason": f"Daily upload limit reached ({daily_limit} uploads)",
                "current": daily_uploads,
                "limit": daily_limit
            }
        
        return {
            "allowed": True,
            "current": daily_uploads,
            "limit": daily_limit,
            "remaining": daily_limit - daily_uploads
        }
    finally:
        conn.close()


def increment_daily_uploads(user_id: int):
    """Increment daily upload count"""
    conn = get_db()
    try:
        today = datetime.utcnow().date().isoformat()
        conn.execute(
            "UPDATE users SET daily_uploads = daily_uploads + 1, last_upload_date = ? WHERE id = ?",
            (today, user_id)
        )
        conn.commit()
    finally:
        conn.close()


def set_user_limits(user_id: int, batch_limit: int = None, daily_upload_limit: int = None):
    """Admin: Set user limits"""
    conn = get_db()
    try:
        if batch_limit is not None:
            conn.execute(
                "UPDATE users SET batch_limit = ? WHERE id = ?",
                (batch_limit, user_id)
            )
        if daily_upload_limit is not None:
            conn.execute(
                "UPDATE users SET daily_upload_limit = ? WHERE id = ?",
                (daily_upload_limit, user_id)
            )
        conn.commit()
    finally:
        conn.close()


# -----------------------
# SIGNUP CODE FUNCTIONS
# -----------------------

def get_active_signup_code() -> Optional[str]:
    """Get the currently active signup code"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT code FROM signup_codes WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return row["code"] if row else None
    finally:
        conn.close()


def rotate_signup_code() -> str:
    """Deactivate current code and generate a new one"""
    import random
    import string
    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    conn = get_db()
    try:
        # Deactivate all current codes
        conn.execute("UPDATE signup_codes SET is_active = 0")
        # Insert new code
        conn.execute(
            "INSERT INTO signup_codes (code, is_active, created_at) VALUES (?, 1, ?)",
            (new_code, datetime.utcnow().isoformat())
        )
        conn.commit()
        return new_code
    finally:
        conn.close()


def verify_signup_code(code: str) -> bool:
    """Verify if a code is currently active"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM signup_codes WHERE code = ? AND is_active = 1",
            (code,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()
