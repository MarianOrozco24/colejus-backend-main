import sys
import os

# Add current path to sys.path
sys.path.append(os.getcwd())

try:
    from app import app, db
    with app.app_context():
        # Query charset and collation for users table
        result = db.session.execute(db.text("""
            SELECT TABLE_NAME, TABLE_COLLATION 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'users';
        """)).fetchone()
        
        # Query charset and collation for users.uuid column
        col_result = db.session.execute(db.text("""
            SELECT COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'users' 
              AND COLUMN_NAME = 'uuid';
        """)).fetchone()
        
        # Query default database collation
        db_result = db.session.execute(db.text("""
            SELECT @@character_set_database, @@collation_database;
        """)).fetchone()
        
        print("\n=== DATABASE COLLATION INFORMATION ===")
        if db_result:
            print(f"Database Default: Charset={db_result[0]}, Collation={db_result[1]}")
        if result:
            print(f"Table 'users': Collation={result[1]}")
        else:
            print("Table 'users' not found in information_schema.")
        if col_result:
            print(f"Column 'users.uuid': Charset={col_result[1]}, Collation={col_result[2]}")
        else:
            print("Column 'users.uuid' not found in information_schema.")
        print("======================================\n")

except Exception as e:
    print(f"Error running diagnostics: {e}", file=sys.stderr)
