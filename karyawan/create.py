import sqlite3
import re
from db import get_connection

# ==========================================
# 1. HELPER FUNCTIONS (Input Validator)
# ==========================================

def get_valid_string(prompt: str, min_len: int = 1) -> str:
    """Meminta input string, memastikan tidak kosong/hanya spasi."""
    while True:
        data = input(prompt).strip()
        if len(data) >= min_len:
            return data
        print(f"[!] Input terlalu pendek (min {min_len} karakter).")

def get_valid_email(cur: sqlite3.Cursor) -> str:
    """
    Meminta input email dengan validasi:
    1. Format Regex (nama@domain.com)
    2. Cek Duplikasi di Database (Uniqueness)
    """
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    
    while True:
        email = input("Email Karyawan   : ").strip()
        if not email:
            print("[!] Email wajib diisi.")
            continue
            
        if not re.match(email_regex, email):
            print("[!] Format email salah. Contoh: user@email.com")
            continue
            
        # Cek Duplikasi
        cur.execute("SELECT id FROM karyawan WHERE email = ?", (email,))
        if cur.fetchone():
            print(f"[!] Email '{email}' sudah digunakan karyawan lain.")
        else:
            return email

def get_valid_currency(prompt: str) -> float:
    """Meminta input angka positif (uang)."""
    while True:
        try:
            val = float(input(prompt))
            if val < 0:
                print("[!] Nominal tidak boleh negatif.")
            else:
                return val
        except ValueError:
            print("[!] Harap masukkan angka saja (tanpa Rp/Titik).")

# ==========================================
# 2. HELPER FUNCTIONS (Database Selector)
# ==========================================

def select_option_from_db(cur: sqlite3.Cursor, table: str, col_name: str, title: str) -> int:
    """Memilih ID dari tabel referensi (Jabatan/Status)."""
    print(f"\n--- PILIH {title.upper()} ---")
    
    query = f"SELECT id, {col_name}"
    if table == 'jabatan':
        query += ", tunjangan_jabatan"
        
    cur.execute(f"{query} FROM {table}")
    rows = cur.fetchall()

    if not rows:
        print(f"[ERROR] Data {table} kosong. Hubungi Admin.")
        return None

    # Header Tabel
    print(f"{'No':<4} | {title:<20} | {'Info'}")
    print("-" * 45)
    
    # Mapping pilihan user (1, 2, 3...) ke ID database (bisa acak)
    options = {} 
    for idx, row in enumerate(rows, 1):
        info = f"Rp{row[2]:,.0f}" if table == 'jabatan' else "-"
        print(f"{idx:<4} | {row[1]:<20} | {info}")
        options[idx] = row[0] # Key=Urutan, Value=ID Database

    print("-" * 45)
    while True:
        try:
            choice = int(input(f"Pilih Nomor (1-{len(options)}): "))
            if choice in options:
                return options[choice]
            print("[!] Pilihan tidak tersedia.")
        except ValueError:
            print("[!] Masukkan angka urutan.")

def select_bank_from_db(cur: sqlite3.Cursor) -> str:
    """Memilih Kode Bank dari master_bank (Return string kode, misal 'BCA')."""
    print("\n--- PILIH BANK TRANSFER ---")
    cur.execute("SELECT kode_bank, nama_bank FROM master_bank")
    rows = cur.fetchall()
    
    if not rows:
        print("[ERROR] Master Bank kosong. Jalankan seed.py dulu.")
        return None

    # Tampilkan List
    options = {}
    for idx, row in enumerate(rows, 1):
        print(f"{idx}. {row[1]} ({row[0]})")
        options[idx] = row[0] # Key=Urutan, Value=Kode Bank (string)

    while True:
        try:
            choice = int(input("Pilih Bank Tujuan: "))
            if choice in options:
                return options[choice]
            print("[!] Bank tidak ditemukan.")
        except ValueError:
            print("[!] Masukkan angka urutan.")

# ==========================================
# 3. FUNGSI UTAMA (Main Logic)
# ==========================================

def tambah_karyawan():
    conn = get_connection()
    cur = conn.cursor()
    
    print("\n" + "="*40)
    print("   FORM TAMBAH KARYAWAN & WALLET")
    print("="*40)

    try:
        # --- PHASE 1: Data Pribadi ---
        nama = get_valid_string("Nama Lengkap     : ", min_len=3)
        email = get_valid_email(cur) # Pass cursor untuk cek duplikat

        # --- PHASE 2: Data Pekerjaan ---
        jabatan_id = select_option_from_db(cur, 'jabatan', 'nama_jabatan', 'Jabatan')
        if not jabatan_id: return

        # Sesuaikan 'nama_status' dengan schema db.py kamu
        status_id = select_option_from_db(cur, 'status_pegawai', 'nama_status', 'Status Pegawai')
        if not status_id: return
        
        gaji_pokok = get_valid_currency("\nGaji Pokok (Rp)  : ")

        # --- PHASE 3: Data Wallet (Rekening) ---
        kode_bank = select_bank_from_db(cur)
        if not kode_bank: return

        no_rekening = get_valid_string("Nomor Rekening   : ", min_len=5)
        
        # UX: Default nama pemilik rekening sama dengan nama karyawan
        an_input = input(f"Atas Nama (Enter jika '{nama}'): ").strip()
        atas_nama = an_input if an_input else nama

        # --- PHASE 4: Simpan ke Database (Atomic) ---
        print("\n[PROSES] Menyimpan data...")
        
        # 1. Insert Karyawan
        cur.execute("""
            INSERT INTO karyawan (nama, email, jabatan_id, status_pegawai_id, gaji_pokok)
            VALUES (?, ?, ?, ?, ?)
        """, (nama, email, jabatan_id, status_id, gaji_pokok))
        
        new_karyawan_id = cur.lastrowid # Ambil ID yang baru dibuat
        
        # 2. Insert Wallet (Pakai ID karyawan tadi)
        cur.execute("""
            INSERT INTO karyawan_wallet (karyawan_id, kode_bank, nomor_rekening, atas_nama_rekening)
            VALUES (?, ?, ?, ?)
        """, (new_karyawan_id, kode_bank, no_rekening, atas_nama))

        # Commit jika kedua query di atas sukses
        conn.commit()
        print(f"\n✅ SUKSES! Karyawan '{nama}' dan rekening {kode_bank} berhasil disimpan.")

    except sqlite3.Error as e:
        conn.rollback() # Batalkan semua jika ada error
        print(f"\n❌ DATABASE ERROR: {e}")
        print("Data tidak disimpan (Rollback).")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ SYSTEM ERROR: {e}")

    finally:
        conn.close()

# Biar bisa dites langsung kalau file ini dijalankan
if __name__ == "__main__":
    tambah_karyawan()