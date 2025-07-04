import mysql.connector
from config import Config

class Database:
    @staticmethod
    def get_connection():
        try:
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                use_unicode=True
            )
            return conn
        except mysql.connector.Error as err:
            print(f"Database connection error: {err}")
            return None

    @staticmethod
    def execute_query(query, params=None, fetch_one=False):
        conn = Database.get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())
                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()
                conn.commit()
                return result
            except mysql.connector.Error as err:
                print(f"Database error: {err}")
                conn.rollback()
                return None
            finally:
                cursor.close()
                conn.close()
        return None