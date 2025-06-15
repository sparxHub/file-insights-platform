import bcrypt, json
from pathlib import Path

def run():
    demo_user = {
        "id": "demo-user-id",
        "email": "demo@example.com",
        "username": "demo",
        "full_name": "Demo User",
        "password_hash": bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode(),
        "is_active": True,
    }
    Path("seed_user.json").write_text(json.dumps(demo_user, indent=2))
    print("Seed user written to seed_user.json")

if __name__ == "__main__":
    run()
