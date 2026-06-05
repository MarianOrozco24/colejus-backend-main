import sys
import os
import pymysql
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

try:
    username = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASSWORD')
    host = os.environ.get('MYSQL_HOST')
    database = os.environ.get('MYSQL_DATABASE')
    
    # Establish direct connection using pymysql
    connection = pymysql.connect(
        host=host,
        user=username,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        # 1. Query default database collation
        cursor.execute("SELECT @@character_set_database, @@collation_database;")
        db_result = cursor.fetchone()
        
        # 2. Query charset and collation for users table
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_COLLATION 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'users';
        """)
        table_result = cursor.fetchone()
        
        # 3. Query charset and collation for users.uuid column
        cursor.execute("""
            SELECT COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'users' 
              AND COLUMN_NAME = 'uuid';
        """)
        col_result = cursor.fetchone()
        
        # 4. Check professionals table if it exists
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_COLLATION 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'professionals';
        """)
        prof_result = cursor.fetchone()
        
        # 5. Check professionals.uuid_user collation
        cursor.execute("""
            SELECT COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'professionals' 
              AND COLUMN_NAME = 'uuid_user';
        """)
        prof_col_result = cursor.fetchone()
        
        print("\n=== DATABASE COLLATION INFORMATION ===")
        if db_result:
            print(f"Database Default: Charset={db_result['@@character_set_database']}, Collation={db_result['@@collation_database']}")
        
        if table_result:
            print(f"Table 'users': Collation={table_result['TABLE_COLLATION']}")
        else:
            print("Table 'users' not found in database.")
            
        if col_result:
            print(f"Column 'users.uuid': Charset={col_result['CHARACTER_SET_NAME']}, Collation={col_result['COLLATION_NAME']}")
        else:
            print("Column 'users.uuid' not found.")
            
        if prof_result:
            print(f"Table 'professionals': Collation={prof_result['TABLE_COLLATION']}")
            
        if prof_col_result:
            print(f"Column 'professionals.uuid_user': Charset={prof_col_result['CHARACTER_SET_NAME']}, Collation={prof_col_result['COLLATION_NAME']}")
            
        print("======================================\n")
        
    connection.close()

except Exception as e:
    print(f"Error running direct diagnostics: {e}", file=sys.stderr)
