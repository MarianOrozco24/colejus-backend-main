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
        database=database
    )
    
    with connection.cursor() as cursor:
        print(f"Altering database '{database}' default collation...")
        # Run alter database to set default collation to utf8mb4_0900_ai_ci
        sql = f"ALTER DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
        cursor.execute(sql)
        print("Database default collation altered successfully!")
        
        # Verify the change
        cursor.execute("SELECT @@character_set_database, @@collation_database;")
        db_result = cursor.fetchone()
        if db_result:
            print(f"New Database Default: Charset={db_result[0]}, Collation={db_result[1]}")
            
    connection.close()
    print("\n[SUCCESS] The database collation has been fixed. You can now run 'flask db upgrade' again.")

except Exception as e:
    print(f"\n[ERROR] Failed to alter database: {e}", file=sys.stderr)
