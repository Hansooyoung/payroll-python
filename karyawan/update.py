# karyawan/update.py
import sqlite3
import re
from db import get_connection

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def get_input_or_default(label: str, current_val: any) -> str:
    """
    Meminta input user. Jika user langsung Enter (kosong), 
    kembalikan nilai lama (current_val).
    """
    # Handle None value display
    display_val = current_val if current_val is not None else "[KOSONG]"
    
    user_input = input(f"{label:<20} (Saat ini: {display_val}): ").strip()
    return user_input if user_input else current_val

def select_id_with_default(cur, table, col_name, title, current_id):
    """
    Menampilkan daftar pilihan, menandai yang aktif saat ini.
    User bisa tekan Enter untuk tidak mengubah pilihan.
    """
    print(f"\n--- GANTI {title.upper()} (Enter untuk tetap) ---")
    
    query = f"SELECT id, {col_name}"
    if table == 'jabatan': query += ", tunjangan_jabatan"
    
    cur.execute(f"{query} FROM {table}")
    rows = cur.fetchall()
    
    valid_ids = []
    for row in rows:
        valid_ids.append(row[0])
        marker = " <--- SAAT INI" if row[0] == current_id else ""
        
        info = ""
        if table == 'jabatan': info = f"| Rp{row[2]:,.0f}"
        
        print(f"{row[0]}. {row[1]} {info} {marker}")

    while True:
        inp = input(f"Pilih ID {title} baru: ").strip()
        if not inp: 
            return current_id # Keep old value
        
        if inp.isdigit() and int(inp) in valid_ids:
            return int(inp)
        print("[!] ID tidak valid.")

def select_bank_with_default(cur, current_code):
    """Sama seperti select ID, tapi untuk Kode Bank (String)"""
    print(f"\n--- GANTI BANK (Enter untuk tetap) ---")
    cur.execute("SELECT kode_bank, nama_bank FROM master_bank")
    rows = cur.fetchall()
    
    bank_map = {} # Mapping urutan ke Kode Bank
    for i, row in enumerate(rows, 1):
        bank_map[i] = row[0]
        marker = " <--- SAAT INI" if row[0] == current_code else ""
        print(f"{i}. {row[1]} ({row[0]}) {marker}")
        
    while True:
        inp = input(f"Pilih Nomor Bank baru: ").strip()
        if not inp:
            return current_code
        
        if inp.isdigit() and int(inp) in bank_map:
            return bank_map[int(inp)]
        print("[!] Pilihan tidak valid.")

# ==========================================
# 2. MAIN LOGIC
# ==========================================

def update_karyawan():
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== FORM UPDATE DATA KARYAWAN ===")
    
    # 1. Cari Karyawan (Termasuk yang Non-Aktif agar bisa di-Restore)
    keyword = input("Masukkan ID atau Nama Karyawan: ").strip()
    if not keyword: return

    # Query gabungan (Join) ambil Profile + Wallet + Status Aktif
    query = """
        SELECT k.id, k.nama, k.email, k.jabatan_id, k.status_pegawai_id, k.gaji_pokok, k.is_active,
               w.id, w.kode_bank, w.nomor_rekening, w.atas_nama_rekening
        FROM karyawan k
        LEFT JOIN karyawan_wallet w ON k.id = w.karyawan_id AND w.is_primary = 1
        WHERE k.id = ? OR k.nama LIKE ?
    """
    
    # Handle search params
    if keyword.isdigit():
        cur.execute(query, (int(keyword), f"%{keyword}%"))
    else:
        cur.execute(query, (-1, f"%{keyword}%"))
        
    data = cur.fetchone()

    if not data:
        print("❌ Karyawan tidak ditemukan.")
        conn.close(); return

    # Unpacking Data
    k_id, k_nama, k_email, k_jab, k_stat, k_gaji, k_active = data[0:7]
    w_id, w_bank, w_rek, w_an = data[7:11]

    # --- FITUR RESTORE (NEW) ---
    status_label = "" if k_active == 1 else "[NON-AKTIF]"
    print(f"\n[EDIT DATA] Karyawan: {k_nama} (ID: {k_id}) {status_label}")
    
    if k_active == 0:
        print("\n⚠️  Karyawan ini sedang dinonaktifkan.")
        restore = input("Apakah Anda ingin MENGAKTIFKAN KEMBALI karyawan ini? (y/n): ").strip().lower()
        if restore == 'y':
            try:
                cur.execute("UPDATE karyawan SET is_active = 1 WHERE id = ?", (k_id,))
                conn.commit()
                print(f"✅ Sukses! Karyawan '{k_nama}' telah aktif kembali.")
                k_active = 1 # Update variabel lokal biar lanjut edit normal
            except Exception as e:
                print(f"Gagal restore: {e}")
    
    print("-" * 50)

    try:
        # --- PHASE 1: Update Profile ---
        new_nama = get_input_or_default("Nama Lengkap", k_nama)
        new_email = get_input_or_default("Email", k_email)
        
        # Validasi Email sederhana
        if new_email != k_email and not re.match(r"[^@]+@[^@]+\.[^@]+", new_email):
            print("Format email salah! Menggunakan email lama.")
            new_email = k_email

        # Gaji
        gaji_str = get_input_or_default("Gaji Pokok", str(int(k_gaji)))
        new_gaji = float(gaji_str) if gaji_str.replace(".","").isdigit() else k_gaji

        # Selectors
        new_jab_id = select_id_with_default(cur, 'jabatan', 'nama_jabatan', 'Jabatan', k_jab)
        new_stat_id = select_id_with_default(cur, 'status_pegawai', 'nama_status', 'Status', k_stat)

        # --- PHASE 2: Update Wallet ---
        print("-" * 50)
        print("[UPDATE REKENING BANK]")
        
        new_bank = select_bank_with_default(cur, w_bank)
        new_rek = get_input_or_default("Nomor Rekening", w_rek)
        new_an = get_input_or_default("Atas Nama", w_an if w_an else new_nama)

        # --- PHASE 3: Eksekusi Database ---
        print("\n[PROSES] Menyimpan perubahan...")

        # 1. Update Tabel Karyawan
        cur.execute("""
            UPDATE karyawan 
            SET nama=?, email=?, jabatan_id=?, status_pegawai_id=?, gaji_pokok=?
            WHERE id=?
        """, (new_nama, new_email, new_jab_id, new_stat_id, new_gaji, k_id))

        # 2. Upsert Tabel Wallet
        if w_id:
            cur.execute("""
                UPDATE karyawan_wallet 
                SET kode_bank=?, nomor_rekening=?, atas_nama_rekening=?
                WHERE id=?
            """, (new_bank, new_rek, new_an, w_id))
        else:
            if new_bank:
                cur.execute("""
                    INSERT INTO karyawan_wallet (karyawan_id, kode_bank, nomor_rekening, atas_nama_rekening, is_primary)
                    VALUES (?, ?, ?, ?, 1)
                """, (k_id, new_bank, new_rek, new_an))

        conn.commit()
        print(f"✅ Data Karyawan & Wallet berhasil diperbarui!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Terjadi kesalahan: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    update_karyawan()