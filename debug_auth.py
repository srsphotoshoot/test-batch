import database as db
import os
import jwt
from datetime import datetime, timedelta
from config import JWT_SECRET_KEY

def debug_auth():
    print(f"JWT_SECRET_KEY: {JWT_SECRET_KEY}")
    
    # Initialize DB
    db.init_db()
    
    email = "admin@test.com"
    password = "adminpass"
    
    print(f"Attempting login for {email}...")
    user = db.get_user(email, password)
    
    if user:
        print("Login successful!")
        print(f"User data: {user}")
        
        token = db.create_jwt_token(user)
        print(f"Generated token: {token}")
        
        payload = db.verify_jwt_token(token)
        if payload:
            print("Token verification successful!")
            print(f"Payload: {payload}")
        else:
            print("Token verification FAILED!")
            
            # Manual decode to see what's wrong
            try:
                decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
                print(f"Manual decode worked: {decoded}")
            except Exception as e:
                print(f"Manual decode failed: {str(e)}")
    else:
        print("Login FAILED! Check credentials or DB.")
        users = db.get_all_users()
        print(f"Available users: {[u['email'] for u in users]}")

if __name__ == "__main__":
    debug_auth()
