from functools import wraps
from flask import session, redirect, url_for, flash, request
from helpers.database import Database


def lecturer_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'lecturer_logged_in' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('lecturer_login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'lecturer_logged_in' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('lecturer_login'))

        # Kiểm tra nếu là admin (hoặc giảng viên có quyền quản lý dữ liệu)
        query = "SELECT Quyen FROM GIANG_VIEN WHERE Ma_giang_vien = %s"
        result = Database.execute_query(query, (session['ma_giang_vien'],), fetch_one=True)

        if not result or result.get('Quyen') != 'admin':
            flash('Bạn không có quyền truy cập trang này', 'danger')
            return redirect(url_for('lecturer_dashboard'))

        return f(*args, **kwargs)

    return decorated_function


def verify_lecturer_class(ma_lop):
    """Xác minh giảng viên có quyền với lớp học"""
    from helpers.database import Database
    query = """
        SELECT 1 FROM LOP_HOC 
        WHERE Ma_lop = %s AND Ma_giang_vien = %s
    """
    result = Database.execute_query(query, (ma_lop, session['ma_giang_vien']), fetch_one=True)
    return result is not None


def check_data_permission(table_name):
    """Kiểm tra quyền truy cập bảng dữ liệu"""
    allowed_tables = {
        'SINH_VIEN': ['admin', 'manager'],
        'GIANG_VIEN': ['admin'],
        'LOP_HOC': ['admin', 'manager'],
        'THE_RFID': ['admin', 'manager'],
        'DANG_KY_LOP': ['admin', 'manager']
    }

    if table_name not in allowed_tables:
        return False

    # Lấy thông tin quyền của giảng viên
    query = "SELECT Quyen FROM GIANG_VIEN WHERE Ma_giang_vien = %s"
    result = Database.execute_query(query, (session['ma_giang_vien'],), fetch_one=True)

    if not result:
        return False

    user_permission = result.get('Quyen', '')
    return user_permission in allowed_tables[table_name]