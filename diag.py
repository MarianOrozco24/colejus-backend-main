import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from app import app, db
from models.ip_manager import IPRegistry

def check():
    with app.app_context():
        print("Checking database tables...")
        try:
            # Check if table exists
            count = IPRegistry.query.count()
            print(f"IPRegistry table exists. Current count: {count}")
        except Exception as e:
            print(f"Error accessing IPRegistry table: {e}")
            print("Attempting to create tables...")
            try:
                db.create_all()
                print("db.create_all() executed.")
            except Exception as e2:
                print(f"Failed to create tables: {e2}")

        print("\nTesting developer endpoints internally...")
        with app.test_client() as client:
            endpoints = ['/api/dev/stats', '/api/dev/logs/recent', '/api/dev/ips']
            for ep in endpoints:
                print(f"Testing {ep}...")
                try:
                    resp = client.get(ep)
                    print(f"Status: {resp.status_code}")
                    if resp.status_code == 500:
                        print(f"Response data: {resp.data[:200]}...")
                except Exception as e:
                    print(f"Exception hitting {ep}: {e}")

if __name__ == "__main__":
    check()
