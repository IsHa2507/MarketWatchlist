"""Quick script to create/reset demo user with correct password"""
from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password
from datetime import datetime, timedelta

db = SessionLocal()

# Delete existing demo user
existing = db.query(User).filter(User.email == "demo@marketpulse.app").first()
if existing:
    db.delete(existing)
    db.commit()
    print("Deleted existing demo user")

# Create fresh demo user
demo_user = User(
    email="demo@marketpulse.app",
    password_hash=hash_password("demo123"),
    full_name="Demo User",
    last_seen_at=datetime.utcnow() - timedelta(days=3),
)
db.add(demo_user)
db.commit()
db.refresh(demo_user)

# Verify password works
from app.core.security import verify_password
works = verify_password("demo123", demo_user.password_hash)
print(f"✓ Demo user created: demo@marketpulse.app / demo123")
print(f"✓ Password verification: {works}")

db.close()
