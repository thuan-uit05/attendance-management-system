import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Cấu hình Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Cấu hình database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'thith')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '15112004')
    DB_NAME = os.getenv('DB_NAME', 'Diemdanh')
    
    # Cấu hình khác
    RFID_READER_ENABLED = os.getenv('RFID_READER_ENABLED', 'False') == 'True'