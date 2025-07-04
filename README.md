# attendance-management-system

RFID-based Attendance Management System for Smart Classrooms. 

---

## 🚀 Tính năng

- Quản lý điểm danh tự động qua thẻ RFID
- Hệ thống Web Flask giao diện đơn giản
- Phân quyền giảng viên, quản lý lớp học
- Ghi nhận lịch sử điểm danh, lọc thống kê
- Kết nối cơ sở dữ liệu MySQL
- Hỗ trợ upload qua Python script (docthe.py, ghithe.py)

---

## 📂 Cấu trúc dự án

```
.
├── Diemdanh.env             # File môi trường
├── DIemdanh.sql             # Cấu trúc CSDL MySQL
├── docthe.py, ghithe.py     # Script đọc/ghi thẻ
├── app/
│   ├── app.py               # Flask app chính
│   ├── config.py            # Config DB
│   └── requirements.txt     # Thư viện Python
├── helpers/
│   ├── attendance.py        # Xử lý điểm danh
│   ├── auth.py              # Xử lý đăng nhập
│   ├── database.py          # Kết nối CSDL
│   └── lecturer.py          # Quản lý giảng viên
├── templates/
│   ├── base.html, ...       # Giao diện HTML
```

---

## ⚙️ Hướng dẫn chạy

### 1️⃣ Cài đặt
```bash
pip install -r app/requirements.txt
```

Tạo CSDL MySQL:
```sql
SOURCE DIemdanh.sql;
```

Thêm cấu hình `.env` vào `Diemdanh.env` nếu cần.

---

### 2️⃣ Chạy server Flask
```bash
cd app
python app.py
```

---

### 3️⃣ Sử dụng scripts
```bash
python docthe.py
python ghithe.py
```

---

## 📜 License

MIT License.

---

🚀 **Enjoy & Star this repo if you like it!**
