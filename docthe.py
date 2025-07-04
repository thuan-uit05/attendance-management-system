import mysql.connector
import spidev
import lgpio
import time
import sys

# Cấu hình chân RST và SPI
RST_PIN = 25  # GPIO25, pin 22

spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, CE0
spi.max_speed_hz = 1000000

# Khởi tạo GPIO
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, RST_PIN)

# Delay 5 giây giữa các lần quét thẻ
DELAY_TIME = 5
last_scan_time = 0


def hard_reset():
    """Reset cứng RC522"""
    lgpio.gpio_write(chip, RST_PIN, 0)
    time.sleep(0.1)
    lgpio.gpio_write(chip, RST_PIN, 1)
    time.sleep(0.1)


# Reset RC522
hard_reset()


# Hàm giao tiếp RC522
def write_register(addr, val):
    try:
        spi.xfer2([((addr << 1) & 0x7E), val])
    except Exception as e:
        print(f"Lỗi ghi register: {e}")


def read_register(addr):
    try:
        return spi.xfer2([((addr << 1) & 0x7E) | 0x80, 0])[1]
    except Exception as e:
        print(f"Lỗi đọc register: {e}")
        return 0


def clear_bit_mask(reg, mask):
    """Xóa bit mask trong register"""
    val = read_register(reg)
    write_register(reg, val & (~mask))


def set_bit_mask(reg, mask):
    """Set bit mask trong register"""
    val = read_register(reg)
    write_register(reg, val | mask)


def init_rc522():
    """Khởi tạo RC522"""
    try:
        # Reset mềm
        write_register(0x01, 0x0F)  # CommandReg - Soft reset
        time.sleep(0.1)

        # Chờ reset hoàn tất
        timeout = 0
        while read_register(0x01) & 0x10:  # PowerDown bit
            time.sleep(0.01)
            timeout += 1
            if timeout > 100:
                print("Timeout chờ reset")
                return False

        # Cấu hình timer
        write_register(0x2A, 0x8D)  # TModeReg - TAuto=1; timer starts automatically
        write_register(0x2B, 0x3E)  # TPrescalerReg - TModeReg[3..0] + TPrescalerReg
        write_register(0x2D, 30)  # TReloadRegL
        write_register(0x2C, 0)  # TReloadRegH

        # Cấu hình TX
        write_register(0x15, 0x40)  # TxASKReg - Force100ASK=0
        write_register(0x11, 0x3D)  # ModeReg - CRCPreset = 6363h

        # Bật antenna
        val = read_register(0x14)  # TxControlReg
        if not (val & 0x03):
            set_bit_mask(0x14, 0x03)

        print(f"RC522 Version: 0x{read_register(0x37):02X}")  # VersionReg
        return True

    except Exception as e:
        print(f"Lỗi khởi tạo RC522: {e}")
        return False


def to_card(command, send_data):
    """Giao tiếp với thẻ"""
    back_data = []
    back_len = 0
    status = False
    irq_en = 0x00
    wait_irq = 0x00

    if command == 0x0E:  # MFAuthent
        irq_en = 0x12
        wait_irq = 0x10
    elif command == 0x0C:  # Transceive
        irq_en = 0x77
        wait_irq = 0x30

    write_register(0x02, irq_en | 0x80)  # ComIEnReg
    clear_bit_mask(0x04, 0x80)  # ComIrqReg
    set_bit_mask(0x0A, 0x80)  # FIFOLevelReg - FlushBuffer

    write_register(0x01, 0x00)  # CommandReg - Idle

    # Ghi dữ liệu vào FIFO
    for data in send_data:
        write_register(0x09, data)  # FIFODataReg

    # Thực thi lệnh
    write_register(0x01, command)  # CommandReg
    if command == 0x0C:  # Transceive
        set_bit_mask(0x0D, 0x80)  # BitFramingReg - StartSend

    # Chờ phản hồi
    i = 2000
    while True:
        n = read_register(0x04)  # ComIrqReg
        i -= 1
        if not (i != 0 and not (n & 0x01) and not (n & wait_irq)):
            break

    clear_bit_mask(0x0D, 0x80)  # BitFramingReg - StartSend=0

    if i != 0:
        if not (read_register(0x06) & 0x1B):  # ErrorReg
            status = True
            if n & irq_en & 0x01:
                status = False
            if command == 0x0C:  # Transceive
                n = read_register(0x0A)  # FIFOLevelReg
                last_bits = read_register(0x0C) & 0x07  # ControlReg
                if last_bits != 0:
                    back_len = (n - 1) * 8 + last_bits
                else:
                    back_len = n * 8

                if n == 0:
                    n = 1
                if n > 16:
                    n = 16

                # Đọc dữ liệu từ FIFO
                for i in range(n):
                    back_data.append(read_register(0x09))  # FIFODataReg

    return status, back_data, back_len


def request(req_mode=0x26):
    """Tìm thẻ"""
    write_register(0x0D, 0x07)  # BitFramingReg - TxLastBits = BitFramingReg[2..0]

    status, back_data, back_len = to_card(0x0C, [req_mode])

    if not status or back_len != 0x10:
        status = False

    return status, back_len


def anticoll():
    """Lấy UID của thẻ"""
    ser_num = []

    write_register(0x0D, 0x00)  # BitFramingReg
    ser_num.append(0x93)  # Anticollision command
    ser_num.append(0x20)  # NVB

    status, back_data, back_len = to_card(0x0C, ser_num)

    if status:
        if len(back_data) == 5:
            ser_num_check = 0
            for i in range(4):
                ser_num_check ^= back_data[i]
            if ser_num_check != back_data[4]:
                status = False

    return status, back_data


def doc_the_rfid():
    """Đọc thẻ RFID"""
    try:
        status, _ = request()
        if status:
            status, uid = anticoll()
            if status and len(uid) >= 4:
                # Kiểm tra UID hợp lệ
                if all(x == 0 for x in uid[:4]) or all(x == 0xFF for x in uid[:4]):
                    return None, None

                uid_str = ''.join([f"{x:02X}" for x in uid[:4]])
                return uid_str, uid_str
    except Exception as e:
        print(f"Lỗi đọc thẻ: {e}")

    return None, None


# Kết nối MySQL với encoding UTF-8
try:
    db = mysql.connector.connect(
        host="localhost",
        user="thith",
        password="15112004",
        database="Diemdanh",
        charset='utf8mb4',
        use_unicode=True,
        autocommit=False
    )
    cursor = db.cursor(buffered=True)
    print("Kết nối database thành công!")
except mysql.connector.Error as err:
    print(f"Lỗi kết nối database: {err}")
    sys.exit(1)


# Kiểm tra điểm danh trùng
def kiem_tra_diem_danh_trung(mssv, ma_lop):
    try:
        cursor.execute("""
            SELECT Ma_diem_danh FROM DIEM_DANH 
            WHERE MSSV = %s AND Ma_lop = %s 
            AND DATE(Thoi_gian_diem_danh) = CURDATE()
            LIMIT 1
        """, (mssv, ma_lop))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Lỗi kiểm tra điểm danh trùng: {err}")
        return None


# Lấy thông tin sinh viên từ MSSV
def lay_thong_tin_sinh_vien(mssv):
    try:
        cursor.execute("SELECT Ho_ten, Trang_thai FROM SINH_VIEN WHERE MSSV = %s", (mssv,))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"Lỗi lấy thông tin sinh viên: {err}")
        return None


# Lấy mã giảng viên hệ thống
def lay_ma_giang_vien_he_thong():
    try:
        cursor.execute("SELECT Ma_giang_vien FROM GIANG_VIEN WHERE Ma_giang_vien = 'HE_THONG'")
        result = cursor.fetchone()
        if not result:
            cursor.execute("""
                INSERT INTO GIANG_VIEN (Ma_giang_vien, Ho_ten, Mat_khau)
                VALUES ('HE_THONG', 'He thong', 'system123')
            """)
            db.commit()
            return 'HE_THONG'
        return result[0]
    except mysql.connector.Error as err:
        print(f"Lỗi lấy mã giảng viên hệ thống: {err}")
        return 'HE_THONG'


# Hàm điểm danh (SỬA ĐỔI CHÍNH)
def diem_danh(uid, ma_lop):
    global last_scan_time

    # Kiểm tra delay
    current_time = time.time()
    if current_time - last_scan_time < DELAY_TIME:
        return

    try:
        # SỬA: Sử dụng uid thay vì ma_the
        cursor.execute("SELECT MSSV FROM THE_RFID WHERE Ma_the = %s AND Trang_thai = 'Hoạt động'", (uid,))
        result = cursor.fetchone()
        if not result:
            print(f"❌ Thẻ {uid} không tồn tại hoặc đã bị khóa!")
            return
        mssv = result[0]

        # Lấy thông tin sinh viên
        sv_info = lay_thong_tin_sinh_vien(mssv)
        if not sv_info:
            print(f"❌ Sinh viên {mssv} không tồn tại!")
            return

        ho_ten, trang_thai_sv = sv_info
        if trang_thai_sv != 'Đang học':
            print(f"❌ Sinh viên {ho_ten} ({mssv}) không còn đang học!")
            return

        # Kiểm tra sinh viên có đăng ký lớp không
        cursor.execute("""
            SELECT COUNT(*) FROM DANG_KY_LOP 
            WHERE MSSV = %s AND Ma_lop = %s AND Trang_thai = 'Đã đăng ký'
        """, (mssv, ma_lop))

        if cursor.fetchone()[0] == 0:
            print(f"⚠️ Sinh viên {ho_ten} ({mssv}) không đăng ký lớp {ma_lop}!")
            # Vẫn cho điểm danh nhưng đánh dấu gian lận
            cursor.execute("""
                INSERT INTO DIEM_DANH 
                (MSSV, Ma_lop, Thoi_gian_diem_danh, Ma_the_RFID, Trang_thai)
                VALUES (%s, %s, NOW(), %s, 'Gian lận')
            """, (mssv, ma_lop, uid))  # SỬA: Sử dụng uid
            db.commit()
            last_scan_time = current_time  # SỬA: Thêm dòng này
            return

        # Kiểm tra điểm danh trùng
        diem_danh_trung = kiem_tra_diem_danh_trung(mssv, ma_lop)

        if diem_danh_trung:
            # Cập nhật trạng thái gian lận cho bản ghi cũ
            cursor.execute("""
                UPDATE DIEM_DANH 
                SET Trang_thai = 'Gian lận' 
                WHERE Ma_diem_danh = %s
            """, (diem_danh_trung[0],))

            # Thêm cảnh báo gian lận
            cursor.execute("""
                INSERT INTO CANH_BAO_GIAN_LAN 
                (Ma_diem_danh, Loai_canh_bao, Mo_ta, Thoi_gian_phat_hien, Trang_thai)
                VALUES (%s, 'Điểm danh trùng', %s, NOW(), 'Chưa xử lý')
            """, (diem_danh_trung[0], f"Sinh viên {mssv} điểm danh 2 lần trong ngày"))

            ma_canh_bao = cursor.lastrowid

            # Đảm bảo có giảng viên HE_THONG
            ma_gv = lay_ma_giang_vien_he_thong()

            # Thêm vào lịch sử cảnh báo
            cursor.execute("""
                INSERT INTO LICH_SU_CANH_BAO
                (Ma_canh_bao, Hanh_dong, Mo_ta, Thoi_gian, Nguoi_thuc_hien)
                VALUES (%s, 'Tạo cảnh báo', %s, NOW(), %s)
            """, (ma_canh_bao, f"Cảnh báo điểm danh trùng {mssv}", ma_gv))

            db.commit()
            print(f"⚠️ CẢNH BÁO: {ho_ten} ({mssv}) đã điểm danh trùng!")

        else:
            # Điểm danh hợp lệ
            cursor.execute("""
                INSERT INTO DIEM_DANH 
                (MSSV, Ma_lop, Thoi_gian_diem_danh, Ma_the_RFID, Trang_thai)
                VALUES (%s, %s, NOW(), %s, 'Hợp lệ')
            """, (mssv, ma_lop, uid))  # SỬA: Sử dụng uid
            db.commit()
            print(f"✅ Điểm danh thành công: {ho_ten} ({mssv}) - {time.strftime('%H:%M:%S')}")

        last_scan_time = current_time

    except mysql.connector.Error as err:
        print(f"❌ Lỗi database: {err}")
        db.rollback()
    except Exception as e:
        print(f"❌ Lỗi không mong muốn: {e}")
        db.rollback()


# Chương trình chính
try:
    # Khởi tạo RC522
    if not init_rc522():
        print("❌ Không thể khởi tạo RC522")
        sys.exit(1)

    print("✅ RC522 đã sẵn sàng")

    # Đảm bảo có tài khoản HE_THONG
    lay_ma_giang_vien_he_thong()

    ma_lop = input("Nhập mã lớp: ").strip()

    # Kiểm tra lớp có tồn tại không
    cursor.execute("SELECT Ten_mon_hoc FROM LOP_HOC WHERE Ma_lop = %s", (ma_lop,))
    lop_info = cursor.fetchone()
    if not lop_info:
        print(f"❌ Lớp {ma_lop} không tồn tại!")
        sys.exit(1)

    print(f"\n🎓 ĐANG ĐIỂM DANH LỚP: {ma_lop} - {lop_info[0]}")
    print("📡 Sẵn sàng đọc thẻ...")
    print("⏳ Chờ thẻ RFID...")

    last_uid = None
    no_card_count = 0

    while True:
        uid, _ = doc_the_rfid()

        if uid:
            # Tránh đọc trùng cùng một thẻ
            if uid == last_uid:
                time.sleep(0.3)
                continue

            last_uid = uid
            no_card_count = 0
            print(f"\n📱 Thẻ phát hiện! UID: {uid}")
            diem_danh(uid, ma_lop)
        else:
            # Không có thẻ
            no_card_count += 1
            if no_card_count % 10 == 0:  # Hiển thị thông báo mỗi 1 giây
                print("🔍 Đang tìm thẻ...", end="\r")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n🛑 Đã dừng chương trình điểm danh.")

except Exception as e:
    print(f"❌ Lỗi không mong muốn: {e}")

finally:
    try:
        spi.close()
        lgpio.gpiochip_close(chip)
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()
        print("🔒 Đã đóng kết nối.")
    except:
        pass