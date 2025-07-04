# 📚 Attendance Management System

🎯 **RFID-based Attendance Management System for Smart Classrooms**  

---

## 📌 Table of Contents
- [Giới thiệu](#giới-thiệu)
- [Tính năng chính](#tính-năng-chính)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Cài đặt & chạy](#cài-đặt--chạy)
- [Sử dụng scripts](#sử-dụng-scripts)
- [License](#license)

---

## 📖 Giới thiệu
Hệ thống quản lý điểm danh thông minh sử dụng **thẻ RFID** và **Flask Web App**.  
Dữ liệu được lưu trữ trên **MySQL**, hỗ trợ quản lý giảng viên, lớp học, ghi nhận & thống kê điểm danh.

---

## 🚀 Tính năng chính
✅ Quản lý điểm danh tự động qua RFID  
✅ Giao diện web Flask đơn giản, dễ sử dụng  
✅ Phân quyền giảng viên, quản lý lớp  
✅ Ghi nhận lịch sử điểm danh, lọc thống kê  
✅ Kết nối MySQL, dễ triển khai trên server  
✅ Scripts Python để đọc/ghi thẻ RFID

---

## 📂 Cấu trúc dự án
```
.
├── Diemdanh.env            # File cấu hình môi trường
├── DIemdanh.sql            # Script tạo CSDL MySQL
├── docthe.py, ghithe.py    # Scripts đọc/ghi thẻ RFID
├── app/
│   ├── app.py              # Flask app
│   ├── config.py           # Thông tin kết nối DB
│   └── requirements.txt    # Thư viện Python
├── helpers/
│   ├── attendance.py
│   ├── auth.py
│   ├── database.py
│   └── lecturer.py
├── templates/
│   ├── base.html ...
```

---

## ⚙️ Cài đặt & chạy
### 1️⃣ Cài thư viện Python
```bash
pip install -r app/requirements.txt
```

### 2️⃣ Tạo database
```sql
SOURCE DIemdanh.sql;
```

Thêm file `.env` theo mẫu `Diemdanh.env` để khai báo biến môi trường.

### 3️⃣ Chạy server Flask
```bash
cd app
python app.py
```
Ứng dụng sẽ chạy tại `http://localhost:5000`.

---

## 🖥 Sử dụng scripts
- **Ghi thẻ RFID:**
  ```bash
  python ghithe.py
  ```
- **Đọc thẻ RFID:**
  ```bash
  python docthe.py
  ```

---

## 📜 License
MIT License.

---

🚀 **Star repo nếu bạn thấy hữu ích!**
