import mysql.connector
import spidev
import lgpio
import time
import sys
from datetime import datetime

# Cấu hình chân RST và SPI
RST_PIN = 25  # GPIO25, pin 22

spi = spidev.SpiDev()
spi.open(0, 0)  # Bus 0, CE0
spi.max_speed_hz = 1000000

# Khởi tạo GPIO
chip = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(chip, RST_PIN)


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
    print("✅ Kết nối database thành công!")
except mysql.connector.Error as err:
    print(f"❌ Lỗi kết nối database: {err}")
    sys.exit(1)


def hien_thi_thong_tin_sinh_vien(mssv):
    """Hiển thị thông tin sinh viên"""
    try:
        cursor.execute("SELECT MSSV, Ho_ten, Trang_thai FROM SINH_VIEN WHERE MSSV = %s", (mssv,))
        row = cursor.fetchone()
        if row:
            print(f"📋 Thông tin sinh viên:")
            print(f"   - MSSV: {row[0]}")
            print(f"   - Họ tên: {row[1]}")
            print(f"   - Trạng thái: {row[2]}")
            return row[2] == 'Đang học'
        else:
            print(f"❌ Không tìm thấy sinh viên với MSSV: {mssv}")
            return False
    except mysql.connector.Error as err:
        print(f"❌ Lỗi kiểm tra MSSV: {err}")
        return False


def kiem_tra_the_da_co(mssv):
    """Kiểm tra sinh viên đã có thẻ chưa"""
    try:
        cursor.execute("""
            SELECT Ma_the, Ngay_kich_hoat, Trang_thai 
            FROM THE_RFID 
            WHERE MSSV = %s AND Trang_thai = 'Hoạt động'
        """, (mssv,))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"❌ Lỗi kiểm tra thẻ: {err}")
        return None


def kiem_tra_the_ton_tai(uid):
    """Kiểm tra thẻ đã tồn tại trong hệ thống chưa"""
    try:
        cursor.execute("""
            SELECT Ma_the, MSSV, Trang_thai 
            FROM THE_RFID 
            WHERE Ma_the = %s
        """, (uid,))
        return cursor.fetchone()
    except mysql.connector.Error as err:
        print(f"❌ Lỗi kiểm tra thẻ tồn tại: {err}")
        return None


def ghi_the_moi(uid, mssv):
    """Ghi thẻ mới vào database"""
    try:
        # Vô hiệu hóa thẻ cũ nếu có
        cursor.execute("""
            UPDATE THE_RFID 
            SET Trang_thai = 'Khóa', 
                Ngay_het_han = CURDATE()
            WHERE MSSV = %s AND Ma_the != %s AND Trang_thai = 'Hoạt động'
        """, (mssv, uid))

        vo_hieu_old = cursor.rowcount
        if vo_hieu_old > 0:
            print(f"⚠️  Đã vô hiệu hóa {vo_hieu_old} thẻ cũ")

        # Thêm/cập nhật thẻ mới
        cursor.execute("""
            INSERT INTO THE_RFID (Ma_the, MSSV, Ngay_kich_hoat, Trang_thai)
            VALUES (%s, %s, CURDATE(), 'Hoạt động')
            ON DUPLICATE KEY UPDATE 
                MSSV = VALUES(MSSV),
                Ngay_kich_hoat = VALUES(Ngay_kich_hoat),
                Trang_thai = 'Hoạt động',
                Ngay_het_han = NULL
        """, (uid, mssv))

        db.commit()
        print(f"✅ Thành công! Thẻ {uid} đã được gán cho sinh viên {mssv}")
        print(f"📅 Ngày kích hoạt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True

    except mysql.connector.Error as err:
        print(f"❌ Lỗi ghi thẻ vào database: {err}")
        db.rollback()
        return False


def che_do_ghi_don_le():
    """Chế độ ghi thẻ đơn lẻ"""
    mssv = input("📝 Nhập mã số sinh viên: ").strip().upper()

    if not hien_thi_thong_tin_sinh_vien(mssv):
        return False

    # Kiểm tra thẻ đã có
    the_da_co = kiem_tra_the_da_co(mssv)
    if the_da_co:
        print(f"⚠️  Sinh viên đã có thẻ RFID:")
        print(f"   - UID: {the_da_co[0]}")
        print(f"   - Ngày kích hoạt: {the_da_co[1]}")
        print(f"   - Trạng thái: {the_da_co[2]}")

        if input("🔄 Bạn muốn ghi đè thẻ mới? (y/n): ").lower() != 'y':
            return False

    print(f"\n🔄 Sẵn sàng ghi thẻ cho sinh viên {mssv}")
    print("📡 Vui lòng đưa thẻ vào đầu đọc...")

    return xu_ly_ghi_the(mssv)


def che_do_ghi_nhanh():
    """Chế độ ghi thẻ nhanh - chỉ cần quét thẻ"""
    print("🚀 Chế độ ghi thẻ nhanh")
    print("📡 Đưa thẻ vào đầu đọc, sau đó nhập MSSV...")

    while True:
        uid, _ = doc_the_rfid()
        if uid:
            print(f"\n📱 Phát hiện thẻ: {uid}")

            # Kiểm tra thẻ đã tồn tại
            the_ton_tai = kiem_tra_the_ton_tai(uid)
            if the_ton_tai:
                print(f"⚠️  Thẻ này đã được gán cho: {the_ton_tai[1]} (Trạng thái: {the_ton_tai[2]})")
                if input("🔄 Tiếp tục ghi đè? (y/n): ").lower() != 'y':
                    continue

            mssv = input("📝 Nhập MSSV cho thẻ này: ").strip().upper()

            if hien_thi_thong_tin_sinh_vien(mssv):
                if ghi_the_moi(uid, mssv):
                    if input("\n✅ Tiếp tục ghi thẻ khác? (y/n): ").lower() != 'y':
                        break

        time.sleep(0.1)


def xu_ly_ghi_the(mssv):
    """Xử lý ghi thẻ cho một sinh viên cụ thể"""
    last_uid = None
    no_card_count = 0

    while True:
        uid, _ = doc_the_rfid()

        if uid:
            # Tránh đọc trùng
            if uid == last_uid:
                time.sleep(0.3)
                continue

            last_uid = uid
            no_card_count = 0
            print(f"\n📱 Phát hiện thẻ! UID: {uid}")

            # Kiểm tra thẻ đã tồn tại
            the_ton_tai = kiem_tra_the_ton_tai(uid)
            if the_ton_tai and the_ton_tai[1] != mssv:
                print(f"⚠️  Thẻ này đã được gán cho sinh viên khác: {the_ton_tai[1]}")
                if input("🔄 Tiếp tục ghi đè? (y/n): ").lower() != 'y':
                    last_uid = None
                    continue

            # Xác nhận ghi thẻ
            confirm = input("✅ Xác nhận ghi thẻ này? (y/n): ").lower()
            if confirm == 'y':
                if ghi_the_moi(uid, mssv):
                    return True
                else:
                    return False
            else:
                print("❌ Hủy ghi thẻ. Tiếp tục chờ thẻ khác...")
                last_uid = None
                continue

        else:
            no_card_count += 1
            if no_card_count % 10 == 0:  # Hiển thị mỗi giây
                print("🔍 Đang chờ thẻ...", end="\r")

        time.sleep(0.1)


# Chương trình chính
try:
    # Khởi tạo RC522
    if not init_rc522():
        print("❌ Không thể khởi tạo RC522")
        sys.exit(1)

    print("🎯 CHƯƠNG TRÌNH GHI THẺ RFID")
    print("=" * 40)

    while True:
        print("\n📋 CHỌN CHỨC NĂNG:")
        print("1. Ghi thẻ đơn lẻ (nhập MSSV trước)")
        print("2. Ghi thẻ nhanh (quét thẻ trước)")
        print("3. Thoát")

        lua_chon = input("\n👆 Chọn chức năng (1-3): ").strip()

        if lua_chon == '1':
            che_do_ghi_don_le()
        elif lua_chon == '2':
            che_do_ghi_nhanh()
        elif lua_chon == '3':
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ!")

except KeyboardInterrupt:
    print("\n🛑 Đã thoát chương trình.")

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