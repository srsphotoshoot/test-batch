import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import bcrypt
import jwt
from config import JWT_SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, SIGNUP_PASSKEY
from db_engine import SessionLocal, engine, Base

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

# -----------------
# MODELS
# -----------------

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    role = Column(String(50), default="user")
    batch_count = Column(Integer, default=0)
    batch_limit = Column(Integer, default=50)
    daily_uploads = Column(Integer, default=0)
    daily_upload_limit = Column(Integer, default=100)
    last_upload_date = Column(String(50))
    created_at = Column(String(50))
    
    batches = relationship("Batch", back_populates="user")

class Batch(Base):
    __tablename__ = "batches"
    id = Column(String(50), primary_key=True)
    output_name = Column(String(255), nullable=False)
    background = Column(String(100))
    pose = Column(String(100))
    resolution = Column(String(50))
    dress_type = Column(String(100), default="Normal Mode")
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(50), default="pending")
    error = Column(Text)
    created_at = Column(String(50))
    images_json = Column(Text)
    generated_image_b64 = Column(Text)
    
    # New columns for exact replication
    blouse_color = Column(String(50), default="#FFFFFF")
    lehenga_color = Column(String(50), default="#FFFFFF")
    dupatta_color = Column(String(50), default="#FFFFFF")
    aspect_ratio = Column(String(50), default="1:1")
    
    user = relationship("User", back_populates="batches")

class SignupCode(Base):
    __tablename__ = "signup_codes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(String(50))

# -----------------
# INITIALIZATION
# -----------------

def get_db():
    """Maintain old get_db interface for local sqlite3 if needed, but primary is SessionLocal"""
    return SessionLocal()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Ensure at least one active signup code exists
        active_code = db.query(SignupCode).filter(SignupCode.is_active == True).first()
        if not active_code:
            initial_code = SIGNUP_PASSKEY if SIGNUP_PASSKEY else "ADMIN123"
            db.add(SignupCode(code=initial_code, is_active=True, created_at=datetime.utcnow().isoformat()))
        elif SIGNUP_PASSKEY:
            existing = db.query(SignupCode).filter(SignupCode.code == SIGNUP_PASSKEY).first()
            if not existing:
                db.add(SignupCode(code=SIGNUP_PASSKEY, is_active=True, created_at=datetime.utcnow().isoformat()))

        # Ensure initial admin user exists
        admin_user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if not admin_user:
            hashed_pw = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            db.add(User(
                email=ADMIN_EMAIL,
                password=hashed_pw,
                first_name="Admin",
                last_name="User",
                role="admin",
                created_at=datetime.utcnow().isoformat()
            ))
            print(f"✅ Initial admin user created: {ADMIN_EMAIL}")
            
        db.commit()
    except Exception as e:
        print(f"⚠️ Database initial content warning: {str(e)}")
        db.rollback()
    finally:
        db.close()


# -----------------------
# USER FUNCTIONS
# -----------------------

def create_user(email: str, password: str, first_name: str = None, last_name: str = None, role: str = "user"):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db = SessionLocal()
    try:
        new_user = User(
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            created_at=datetime.utcnow().isoformat()
        )
        db.add(new_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_user(email: str, password: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            # Convert to dict for compatibility with existing caller logic
            user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
            return user_dict
        return None
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return {c.name: getattr(user, c.name) for c in user.__table__.columns}
        return None
    finally:
        db.close()


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
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        return [{
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role,
            "batch_count": u.batch_count,
            "batch_limit": u.batch_limit,
            "created_at": u.created_at
        } for u in users]
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        return []
    finally:
        db.close()


def update_user_role(user_id: int, role: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = role
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def delete_user(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# -----------------------
# BATCH FUNCTIONS
# -----------------------

def save_batch(batch_data: Dict):
    db = SessionLocal()
    try:
        existing = db.query(Batch).filter(Batch.id == batch_data["id"]).first()
        if existing:
            # Update existing
            existing.output_name = batch_data["output_name"]
            existing.background = batch_data.get("background")
            existing.pose = batch_data.get("pose")
            existing.resolution = batch_data.get("resolution")
            existing.dress_type = batch_data.get("dress_type", "Normal Mode")
            existing.aspect_ratio = batch_data.get("aspect_ratio", "1:1")
            existing.blouse_color = batch_data.get("blouse_color", "#FFFFFF")
            existing.lehenga_color = batch_data.get("lehenga_color", "#FFFFFF")
            existing.dupatta_color = batch_data.get("dupatta_color", "#FFFFFF")
            existing.user_id = batch_data.get("user_id")
            existing.status = batch_data["status"]
            existing.error = batch_data.get("error")
            existing.images_json = json.dumps(batch_data.get("images", {}))
            existing.generated_image_b64 = batch_data.get("generated_image")
        else:
            # Create new
            new_batch = Batch(
                id=batch_data["id"],
                output_name=batch_data["output_name"],
                background=batch_data.get("background"),
                pose=batch_data.get("pose"),
                resolution=batch_data.get("resolution"),
                dress_type=batch_data.get("dress_type", "Normal Mode"),
                aspect_ratio=batch_data.get("aspect_ratio", "1:1"),
                blouse_color=batch_data.get("blouse_color", "#FFFFFF"),
                lehenga_color=batch_data.get("lehenga_color", "#FFFFFF"),
                dupatta_color=batch_data.get("dupatta_color", "#FFFFFF"),
                user_id=batch_data.get("user_id"),
                status=batch_data["status"],
                error=batch_data.get("error"),
                created_at=batch_data["created_at"],
                images_json=json.dumps(batch_data.get("images", {})),
                generated_image_b64=batch_data.get("generated_image")
            )
            db.add(new_batch)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_batch(batch_id: str) -> Optional[Dict]:
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return None
        
        batch_dict = {c.name: getattr(batch, c.name) for c in batch.__table__.columns}
        batch_dict["images"] = json.loads(batch.images_json) if batch.images_json else {
            "main": None,
            "ref1": None,
            "ref2": None
        }
        batch_dict["generated_image"] = batch.generated_image_b64
        return batch_dict
    finally:
        db.close()


def list_batches() -> List[Dict]:
    db = SessionLocal()
    try:
        batches = db.query(Batch).order_by(Batch.created_at.desc()).all()
        result = []
        for b in batches:
            b_dict = {c.name: getattr(b, c.name) for c in b.__table__.columns}
            # Remove large strings for list view
            if "generated_image_b64" in b_dict: del b_dict["generated_image_b64"]
            if "images_json" in b_dict: del b_dict["images_json"]
            result.append(b_dict)
        return result
    finally:
        db.close()


def list_user_batches(user_id: int) -> List[Dict]:
    """Get batches created by a specific user"""
    db = SessionLocal()
    try:
        batches = db.query(Batch).filter(Batch.user_id == user_id).order_by(Batch.created_at.desc()).all()
        result = []
        for b in batches:
            b_dict = {c.name: getattr(b, c.name) for c in b.__table__.columns}
            if "generated_image_b64" in b_dict: del b_dict["generated_image_b64"]
            if "images_json" in b_dict: del b_dict["images_json"]
            result.append(b_dict)
        return result
    finally:
        db.close()


def delete_batch(batch_id: str):
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            db.delete(batch)
            db.commit()
    finally:
        db.close()


# -----------------------
# QUEUE SYSTEM
# -----------------------

def get_next_queued_batch() -> Optional[str]:
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.status == 'queued').order_by(Batch.created_at.asc()).first()
        return batch.id if batch else None
    finally:
        db.close()


def get_queue_position(batch_id: str) -> int:
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return -1
        count = db.query(Batch).filter(Batch.status == 'queued', Batch.created_at < batch.created_at).count()
        return count + 1
    finally:
        db.close()


def get_queue_status() -> Dict:
    db = SessionLocal()
    try:
        queued = db.query(Batch).filter(Batch.status.in_(['pending', 'queued'])).count()
        generating = db.query(Batch).filter(Batch.status == 'generating').count()
        return {
            "queued": queued,
            "generating": generating
        }
    finally:
        db.close()


# -----------------------
# USER LIMITS & QUOTAS
# -----------------------

def get_batch_count(user_id: int) -> int:
    """Get current batch count for user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user.batch_count if user else 0
    finally:
        db.close()


def get_batch_limit(user_id: int) -> int:
    """Get batch limit for user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user.batch_limit if user else 50
    finally:
        db.close()


def increment_batch_count(user_id: int):
    """Increment batch count for user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.batch_count += 1
            db.commit()
    finally:
        db.close()


def check_daily_upload_limit(user_id: int) -> Dict:
    """Check if user has remaining daily uploads"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"allowed": False, "reason": "User not found"}
        
        today = datetime.utcnow().date().isoformat()
        if user.last_upload_date != today:
            user.daily_uploads = 0
            user.last_upload_date = today
            db.commit()
            
        if (user.daily_uploads or 0) >= (user.daily_upload_limit or 100):
            return {
                "allowed": False,
                "reason": f"Daily upload limit reached ({user.daily_upload_limit} uploads)",
                "current": user.daily_uploads,
                "limit": user.daily_upload_limit
            }
        
        return {
            "allowed": True,
            "current": user.daily_uploads,
            "limit": user.daily_upload_limit,
            "remaining": (user.daily_upload_limit or 100) - (user.daily_uploads or 0)
        }
    finally:
        db.close()


def increment_daily_uploads(user_id: int):
    """Increment daily upload count"""
    db = SessionLocal()
    try:
        today = datetime.utcnow().date().isoformat()
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.daily_uploads += 1
            user.last_upload_date = today
            db.commit()
    finally:
        db.close()


def set_user_limits(user_id: int, batch_limit: int = None, daily_upload_limit: int = None):
    """Admin: Set user limits"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if batch_limit is not None: user.batch_limit = batch_limit
            if daily_upload_limit is not None: user.daily_upload_limit = daily_upload_limit
            db.commit()
    finally:
        db.close()


# -----------------------
# SIGNUP CODE FUNCTIONS
# -----------------------

def get_active_signup_code() -> Optional[str]:
    """Get the currently active signup code"""
    db = SessionLocal()
    try:
        scode = db.query(SignupCode).filter(SignupCode.is_active == True).order_by(SignupCode.created_at.desc()).first()
        return scode.code if scode else None
    finally:
        db.close()


def rotate_signup_code() -> str:
    """Deactivate current code and generate a new one"""
    import random
    import string
    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    db = SessionLocal()
    try:
        db.query(SignupCode).update({SignupCode.is_active: False})
        db.add(SignupCode(code=new_code, is_active=True, created_at=datetime.utcnow().isoformat()))
        db.commit()
        return new_code
    finally:
        db.close()


def verify_signup_code(code: str) -> bool:
    """Verify if a code is currently active"""
    db = SessionLocal()
    try:
        scode = db.query(SignupCode).filter(SignupCode.code == code, SignupCode.is_active == True).first()
        return scode is not None
    finally:
        db.close()
