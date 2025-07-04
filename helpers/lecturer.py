from helpers.database import Database

class Lecturer:
    @staticmethod
    def authenticate(ma_giang_vien, mat_khau):
        query = """
            SELECT * FROM GIANG_VIEN 
            WHERE Ma_giang_vien = %s AND Mat_khau = %s
        """
        return Database.execute_query(query, (ma_giang_vien, mat_khau), fetch_one=True)

    @staticmethod
    def get_classes(ma_giang_vien, date=None):
        query = """
            SELECT * FROM LOP_HOC 
            WHERE Ma_giang_vien = %s
            {}
            ORDER BY Thoi_gian_bat_dau
        """.format("AND DATE(Thoi_gian_bat_dau) = %s" if date else "")
        params = (ma_giang_vien, date) if date else (ma_giang_vien,)
        return Database.execute_query(query, params)