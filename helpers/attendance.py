from helpers.database import Database

class Attendance:
    @staticmethod
    def record_attendance(mssv, ma_lop, ma_the, status='Hợp lệ'):
        query = """
            INSERT INTO DIEM_DANH
            (MSSV, Ma_lop, Thoi_gian_diem_danh, Ma_the_RFID, Trang_thai)
            VALUES (%s, %s, NOW(), %s, %s)
        """
        return Database.execute_query(query, (mssv, ma_lop, ma_the, status)) is not None

    @staticmethod
    def get_class_attendance(ma_lop):
        query = """
            SELECT dd.*, sv.Ho_ten, sv.Lop 
            FROM DIEM_DANH dd
            JOIN SINH_VIEN sv ON dd.MSSV = sv.MSSV
            WHERE dd.Ma_lop = %s
            ORDER BY dd.Thoi_gian_diem_danh DESC
        """
        return Database.execute_query(query, (ma_lop,))