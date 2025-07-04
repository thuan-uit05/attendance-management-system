CREATE DATABASE IF NOT EXISTS Diemdanh CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE Diemdanh;
CREATE TABLE SINH_VIEN (
    MSSV VARCHAR(10) PRIMARY KEY,
    Ho_ten VARCHAR(100) NOT NULL,
    Lop VARCHAR(20),
    Email VARCHAR(100),
    So_dien_thoai VARCHAR(15),
    Ngay_sinh DATE,
    Gioi_tinh ENUM('Nam', 'Nữ', 'Khác'),
    Khoa_hoc VARCHAR(10), 
    Khoa VARCHAR(100),    
    Nganh_hoc VARCHAR(100), 
    Trang_thai ENUM('Đang học', 'Đã nghỉ', 'Bảo lưu') DEFAULT 'Đang học'
);

CREATE TABLE GIANG_VIEN (
    Ma_giang_vien VARCHAR(10) PRIMARY KEY,
    Ho_ten VARCHAR(100) NOT NULL,
    Email VARCHAR(100) UNIQUE,
    So_dien_thoai VARCHAR(15),
    Mat_khau VARCHAR(255) NOT NULL
);
CREATE TABLE LOP_HOC (
    Ma_lop VARCHAR(10) PRIMARY KEY,
    Ten_mon_hoc VARCHAR(100) NOT NULL,
    Phong_hoc VARCHAR(20),
    Thoi_gian_bat_dau DATETIME,
    Thoi_gian_ket_thuc DATETIME,
    Ma_giang_vien VARCHAR(10),
    FOREIGN KEY (Ma_giang_vien) REFERENCES GIANG_VIEN(Ma_giang_vien)
);
CREATE TABLE THE_RFID (
    Ma_the VARCHAR(20) PRIMARY KEY,
    MSSV VARCHAR(10) UNIQUE,
    Ngay_kich_hoat DATE NOT NULL,
    Ngay_het_han DATE,
    Trang_thai ENUM('Hoạt động', 'Khóa', 'Mất') DEFAULT 'Hoạt động',
    FOREIGN KEY (MSSV) REFERENCES SINH_VIEN(MSSV)
);
CREATE TABLE DIEM_DANH (
    Ma_diem_danh INT AUTO_INCREMENT PRIMARY KEY,
    MSSV VARCHAR(10) NOT NULL,
    Ma_lop VARCHAR(10) NOT NULL,
    Thoi_gian_diem_danh DATETIME NOT NULL,
    Ma_the_RFID VARCHAR(20) NOT NULL,
    Trang_thai ENUM('Hợp lệ', 'Gian lận', 'Vắng mặt') DEFAULT 'Hợp lệ',
    FOREIGN KEY (MSSV) REFERENCES SINH_VIEN(MSSV),
    FOREIGN KEY (Ma_lop) REFERENCES LOP_HOC(Ma_lop),
    FOREIGN KEY (Ma_the_RFID) REFERENCES THE_RFID(Ma_the)
);
CREATE TABLE CANH_BAO_GIAN_LAN (
    Ma_canh_bao INT AUTO_INCREMENT PRIMARY KEY,
    Ma_diem_danh INT NOT NULL,
    Loai_canh_bao ENUM('Thẻ không hợp lệ', 'Điểm danh trùng', 'Sinh viên không có trong lớp') NOT NULL,
    Mo_ta TEXT,
    Thoi_gian_phat_hien DATETIME DEFAULT CURRENT_TIMESTAMP,
    Trang_thai ENUM('Chưa xử lý', 'Đã xác minh', 'Đã xử lý') DEFAULT 'Chưa xử lý',
    Nguoi_xu_ly VARCHAR(10),
    FOREIGN KEY (Ma_diem_danh) REFERENCES DIEM_DANH(Ma_diem_danh),
    FOREIGN KEY (Nguoi_xu_ly) REFERENCES GIANG_VIEN(Ma_giang_vien)
);
CREATE TABLE LICH_SU_CANH_BAO (
    Ma_lich_su INT AUTO_INCREMENT PRIMARY KEY,
    Ma_canh_bao INT NOT NULL,
    Hanh_dong ENUM('Tạo cảnh báo', 'Xác minh', 'Xử lý', 'Bỏ qua') NOT NULL,
    Mo_ta TEXT,
    Thoi_gian DATETIME DEFAULT CURRENT_TIMESTAMP,
    Nguoi_thuc_hien VARCHAR(10) NOT NULL,
    FOREIGN KEY (Ma_canh_bao) REFERENCES CANH_BAO_GIAN_LAN(Ma_canh_bao),
    FOREIGN KEY (Nguoi_thuc_hien) REFERENCES GIANG_VIEN(Ma_giang_vien)
);
CREATE TABLE DANG_KY_LOP (
    Ma_dang_ky INT AUTO_INCREMENT PRIMARY KEY,
    MSSV VARCHAR(10) NOT NULL,
    Ma_lop VARCHAR(10) NOT NULL,
    Ngay_dang_ky DATETIME DEFAULT CURRENT_TIMESTAMP,
    Trang_thai ENUM('Đã đăng ký', 'Đã hủy') DEFAULT 'Đã đăng ký',
    UNIQUE KEY (MSSV, Ma_lop),
    FOREIGN KEY (MSSV) REFERENCES SINH_VIEN(MSSV),
    FOREIGN KEY (Ma_lop) REFERENCES LOP_HOC(Ma_lop)
);
CREATE TABLE THIET_BI_RFID (
    Ma_thiet_bi VARCHAR(20) PRIMARY KEY,
    Ma_lop VARCHAR(10),
    Vi_tri VARCHAR(100),
    Trang_thai ENUM('Hoạt động', 'Bảo trì', 'Hỏng') DEFAULT 'Hoạt động',
    FOREIGN KEY (Ma_lop) REFERENCES LOP_HOC(Ma_lop)
);
DELIMITER //
CREATE TRIGGER kiem_tra_gian_lan
AFTER INSERT ON DIEM_DANH
FOR EACH ROW
BEGIN
    DECLARE sinh_vien_trong_lop INT;
    DECLARE diem_danh_trung INT;
    
    -- Kiểm tra sinh viên có trong lớp không
    SELECT COUNT(*) INTO sinh_vien_trong_lop
    FROM DANG_KY_LOP
    WHERE MSSV = NEW.MSSV AND Ma_lop = NEW.Ma_lop AND Trang_thai = 'Đã đăng ký';
    
    -- Kiểm tra điểm danh trùng
    SELECT COUNT(*) INTO diem_danh_trung
    FROM DIEM_DANH
    WHERE MSSV = NEW.MSSV AND Ma_lop = NEW.Ma_lop
    AND DATE(Thoi_gian_diem_danh) = DATE(NEW.Thoi_gian_diem_danh)
    AND Ma_diem_danh != NEW.Ma_diem_danh;
    
    -- Nếu có gian lận
    IF sinh_vien_trong_lop = 0 OR diem_danh_trung > 0 THEN
        -- Cập nhật trạng thái điểm danh
        UPDATE DIEM_DANH SET Trang_thai = 'Gian lận' WHERE Ma_diem_danh = NEW.Ma_diem_danh;
        
        -- Thêm cảnh báo
        IF sinh_vien_trong_lop = 0 THEN
            INSERT INTO CANH_BAO_GIAN_LAN (Ma_diem_danh, Loai_canh_bao, Mo_ta)
            VALUES (NEW.Ma_diem_danh, 'Sinh viên không có trong lớp', 
                   CONCAT('Sinh viên ', NEW.MSSV, ' điểm danh lớp ', NEW.Ma_lop, ' nhưng không đăng ký'));
        ELSE
            INSERT INTO CANH_BAO_GIAN_LAN (Ma_diem_danh, Loai_canh_bao, Mo_ta)
            VALUES (NEW.Ma_diem_danh, 'Điểm danh trùng', 
                   CONCAT('Sinh viên ', NEW.MSSV, ' đã điểm danh nhiều lần trong ngày'));
        END IF;
    END IF;
END//
DELIMITER ;
DELIMITER //
CREATE PROCEDURE diem_danh_sinh_vien(
    IN p_ma_the VARCHAR(20),
    IN p_ma_lop VARCHAR(10)
)
BEGIN
    DECLARE v_mssv VARCHAR(10);
    DECLARE v_ma_diem_danh INT;
    
    -- Lấy MSSV từ thẻ RFID
    SELECT MSSV INTO v_mssv FROM THE_RFID WHERE Ma_the = p_ma_the;
    
    -- Thêm bản ghi điểm danh
    INSERT INTO DIEM_DANH (MSSV, Ma_lop, Thoi_gian_diem_danh, Ma_the_RFID)
    VALUES (v_mssv, p_ma_lop, NOW(), p_ma_the);
    
    SET v_ma_diem_danh = LAST_INSERT_ID();
    
    -- Trả về kết quả điểm danh
    SELECT 
        d.Ma_diem_danh,
        s.Ho_ten,
        d.Trang_thai,
        CASE 
            WHEN d.Trang_thai = 'Hợp lệ' THEN 'Điểm danh thành công'
            ELSE CONCAT('Cảnh báo: ', c.Loai_canh_bao)
        END AS Thong_bao
    FROM DIEM_DANH d
    JOIN SINH_VIEN s ON d.MSSV = s.MSSV
    LEFT JOIN CANH_BAO_GIAN_LAN c ON d.Ma_diem_danh = c.Ma_diem_danh
    WHERE d.Ma_diem_danh = v_ma_diem_danh;
END//
DELIMITER ;
ALTER TABLE THIET_BI_RFID
ADD CONSTRAINT fk_thiet_bi_phong_hoc 
FOREIGN KEY (Ma_lop) REFERENCES LOP_HOC(Ma_lop);

-- Đồng thời kiểm tra tính nhất quán giữa Phong_hoc (LOP_HOC) và Vi_tri (THIET_BI_RFID)
DELIMITER //
CREATE TRIGGER kiem_tra_phong_rfid
BEFORE INSERT ON THIET_BI_RFID
FOR EACH ROW
BEGIN
    DECLARE phong_hoc_lop VARCHAR(20);
    SELECT Phong_hoc INTO phong_hoc_lop FROM LOP_HOC WHERE Ma_lop = NEW.Ma_lop;
    IF NEW.Vi_tri NOT LIKE CONCAT('%', phong_hoc_lop, '%') THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Vị trí thiết bị RFID phải khớp với phòng học của lớp';
    END IF;
END//
DELIMITER ;

CREATE TABLE LICH_SU_DIEM_DANH (
    Ma_lich_su INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Thông tin sinh viên
    MSSV VARCHAR(10) NOT NULL,
    Ho_ten VARCHAR(100) NOT NULL,
    Lop VARCHAR(20),
    So_dien_thoai VARCHAR(15),
    Ngay_sinh DATE,
    Gioi_tinh ENUM('Nam', 'Nu', 'Khac'),
    
    -- Thông tin điểm danh
    Thoi_gian_diem_danh DATETIME NOT NULL,
    Ma_lop VARCHAR(10) NOT NULL,
    Ma_the_RFID VARCHAR(20) NOT NULL,
    Trang_thai_diem_danh ENUM('Hop le', 'Gian lan', 'Vang mat') DEFAULT 'Hop le',
    
    -- Khóa ngoại
    FOREIGN KEY (MSSV) REFERENCES SINH_VIEN(MSSV),
    FOREIGN KEY (Ma_lop) REFERENCES LOP_HOC(Ma_lop),
    FOREIGN KEY (Ma_the_RFID) REFERENCES THE_RFID(Ma_the),
    
     -- Chỉ mục tối ưu
    INDEX idx_mssv (MSSV),
    INDEX idx_thoi_gian (Thoi_gian_diem_danh)
);


DELIMITER //
CREATE TRIGGER trigger_dong_bo_lich_su
AFTER INSERT ON DIEM_DANH
FOR EACH ROW
BEGIN
    INSERT INTO LICH_SU_DIEM_DANH (
        MSSV, Ho_ten, Lop, So_dien_thoai, Ngay_sinh, Gioi_tinh,
        Thoi_gian_diem_danh, Ma_lop, Ma_the_RFID, Trang_thai_diem_danh
    )
    SELECT 
        s.MSSV, s.Ho_ten, s.Lop, s.So_dien_thoai, s.Ngay_sinh, s.Gioi_tinh,
        NEW.Thoi_gian_diem_danh, NEW.Ma_lop, NEW.Ma_the_RFID, NEW.Trang_thai
    FROM SINH_VIEN s
    WHERE s.MSSV = NEW.MSSV;
END//
DELIMITER ;


CREATE INDEX idx_licsu_malop ON LICH_SU_DIEM_DANH(Ma_lop);
CREATE INDEX idx_licsu_mathetag ON LICH_SU_DIEM_DANH(Ma_the_RFID);
-- Thêm chỉ mục để tăng tốc truy vấn
CREATE INDEX idx_diem_danh_mssv ON DIEM_DANH(MSSV);
CREATE INDEX idx_diem_danh_ma_lop ON DIEM_DANH(Ma_lop);
CREATE INDEX idx_diem_danh_thoi_gian ON DIEM_DANH(Thoi_gian_diem_danh);
CREATE INDEX idx_canh_bao_trang_thai ON CANH_BAO_GIAN_LAN(Trang_thai);

-- Ràng buộc thời gian lớp học
ALTER TABLE LOP_HOC 
ADD CONSTRAINT chk_thoi_gian_lop 
CHECK (Thoi_gian_ket_thuc > Thoi_gian_bat_dau);

-- Ràng buộc thẻ RFID còn hạn sử dụng
ALTER TABLE THE_RFID
ADD CONSTRAINT chk_ngay_het_han
CHECK (Ngay_het_han IS NULL OR Ngay_het_han >= Ngay_kich_hoat);


