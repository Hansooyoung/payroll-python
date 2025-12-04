import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# --- MODULE IMPORTS ---
from db import get_connection
from .email_sender import send_payslip_email
from .pdf_generator import generate_slip_pdf
from .payment_service import PaymentGateway

# --- KONFIGURASI CONSTANTS ---
JUMLAH_HARI_KERJA_STANDAR = 20  # 5 Hari kerja x 4 Minggu
PEMBAGI_UPAH_SEJAM = 173        # Standar Kepmen 102/2004

# 1. HELPER & UTILITIES

def format_rupiah(nominal: float) -> str:
    """Mengubah angka float menjadi string format Rupiah."""
    return f"Rp{nominal:,.0f}".replace(",", ".")

def get_input_number(prompt: str, min_val: float = 0, max_val: float = None) -> float:
    """Meminta input user berupa angka dengan validasi range."""
    while True:
        try:
            val = float(input(prompt))
            if val < min_val:
                print(f"[!] Nilai tidak boleh kurang dari {min_val}.")
                continue
            if max_val is not None and val > max_val:
                print(f"[!] Nilai tidak boleh lebih dari {max_val}.")
                continue
            return val
        except ValueError:
            print("[!] Input harus berupa angka!")

# 2. DATABASE REPOSITORY PATTERN

def fetch_employees(cur: sqlite3.Cursor) -> List[sqlite3.Row]:
    cur.execute("""
        SELECT k.id, k.nama, k.email, k.gaji_pokok, j.nama_jabatan, j.tunjangan_jabatan
        FROM karyawan k
        LEFT JOIN jabatan j ON k.jabatan_id = j.id
    """)
    return cur.fetchall()

def fetch_components(cur: sqlite3.Cursor, table: str, employee_id: int) -> List[sqlite3.Row]:
    """Mengambil data tunjangan atau potongan karyawan."""
    query = f"""
        SELECT m.id, m.nama_{table}, m.nominal_default, m.tipe
        FROM karyawan_{table} k
        JOIN {table} m ON k.{table}_id = m.id
        WHERE k.karyawan_id = ?
    """
    cur.execute(query, (employee_id,))
    return cur.fetchall()

def get_financial_data(cur: sqlite3.Cursor, employee_id: int) -> Tuple[Optional[sqlite3.Row], Optional[sqlite3.Row]]:
    """Mengambil data Rekening Perusahaan & Wallet Karyawan sekaligus."""
    # Ambil Rekening Perusahaan
    cur.execute("SELECT id, saldo FROM rekening_perusahaan LIMIT 1")
    comp_acc = cur.fetchone()
    
    # Ambil Wallet Karyawan Primary
    cur.execute("""
        SELECT kode_bank, nomor_rekening, atas_nama_rekening 
        FROM karyawan_wallet 
        WHERE karyawan_id = ? AND is_primary = 1
    """, (employee_id,))
    emp_wallet = cur.fetchone()
    
    return comp_acc, emp_wallet

def check_duplicate_payroll(cur: sqlite3.Cursor, employee_id: int) -> bool:
    """
    Mengecek apakah gaji untuk karyawan ini di BULAN INI sudah pernah dibuat.
    """
    bulan_ini = datetime.now().strftime("%Y-%m") + "%"
    cur.execute("SELECT id FROM gaji WHERE karyawan_id = ? AND periode LIKE ?", (employee_id, bulan_ini))
    return cur.fetchone() is not None

def save_salary_pending(conn: sqlite3.Connection, data: Dict[str, Any]) -> int:
    """Menyimpan data gaji dengan status awal PENDING. Mengembalikan ID Gaji."""
    cur = conn.cursor()
    
    # 1. Insert Header Gaji
    cur.execute(
        "INSERT INTO gaji (karyawan_id, periode, total_gaji, status_transfer) VALUES (?, ?, ?, 'PENDING')", 
        (data['meta']['id_karyawan'], data['meta']['periode'], data['final']['gaji_bersih'])
    )
    gaji_id = cur.lastrowid

    # 2. Insert Detail
    tunjangan_rows = [(gaji_id, item['id'], item['nominal']) for item in data['detail']['list_tunjangan']]
    potongan_rows = [(gaji_id, item['id'], item['nominal']) for item in data['detail']['list_potongan']]

    if tunjangan_rows:
        cur.executemany("INSERT INTO gaji_tunjangan (gaji_id, tunjangan_id, nominal) VALUES (?, ?, ?)", tunjangan_rows)
    if potongan_rows:
        cur.executemany("INSERT INTO gaji_potongan (gaji_id, potongan_id, nominal) VALUES (?, ?, ?)", potongan_rows)
    
    conn.commit()
    return gaji_id

def update_salary_success(conn: sqlite3.Connection, gaji_id: int, trx_id: str, amount: float, comp_acc_id: int):
    """
    Update status gaji jadi SUCCESS dan potong saldo perusahaan (Atomic).
    """
    cur = conn.cursor()
    try:
        # 1. Atomic Update Saldo (Biarkan DB yang menghitung)
        cur.execute("UPDATE rekening_perusahaan SET saldo = saldo - ? WHERE id = ?", (amount, comp_acc_id))
        
        # 2. Update Status Gaji
        cur.execute("""
            UPDATE gaji SET status_transfer = 'SUCCESS', transfer_ref_id = ?, waktu_transfer = datetime('now')
            WHERE id = ?
        """, (trx_id, gaji_id))

        # 3. Ambil Saldo Terbaru untuk ditampilkan
        cur.execute("SELECT saldo FROM rekening_perusahaan WHERE id = ?", (comp_acc_id,))
        row = cur.fetchone()
        new_balance = row['saldo'] if row else 0
        
        conn.commit()
        return True, new_balance
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] Gagal update saldo: {e}")
        return False, 0

# 3. BUSINESS LOGIC (CALCULATION)

def calculate_nominal(tipe: str, nominal_default: float, gaji_pokok: float, hari_hadir: int) -> float:
    if tipe == 'tetap': return nominal_default
    elif tipe == 'persentase': return (nominal_default / 100) * gaji_pokok
    elif tipe == 'per_hari': return nominal_default * hari_hadir
    return 0.0

def calculate_payroll(karyawan: sqlite3.Row, input_data: Dict[str, float], tunjangan_list: list, potongan_list: list) -> Dict[str, Any]:
    """Inti perhitungan gaji (Gaji Pokok, Lembur, Tunjangan, Potongan)."""
    
    # A. Unpack Input
    hari_hadir = input_data['hari_hadir']
    wd_overtime = input_data['jam_lembur_weekday']
    we_overtime = input_data['jam_lembur_weekend']

    # B. Gaji Pokok (Prorata)
    faktor_kehadiran = min(hari_hadir, JUMLAH_HARI_KERJA_STANDAR) / JUMLAH_HARI_KERJA_STANDAR
    gaji_pokok_final = karyawan['gaji_pokok'] * faktor_kehadiran

    # C. Lembur (1/173 Rule)
    basis_lembur = karyawan['gaji_pokok'] + karyawan['tunjangan_jabatan']
    rate_per_jam = basis_lembur / PEMBAGI_UPAH_SEJAM
    
    uang_lembur_wd = wd_overtime * 1.5 * rate_per_jam
    uang_lembur_we = we_overtime * 2.0 * rate_per_jam
    total_lembur = uang_lembur_wd + uang_lembur_we

    # D. Tunjangan & Potongan Dinamis
    processed_tunjangan = []
    total_tunjangan_lain = 0
    for t in tunjangan_list:
        nom = calculate_nominal(t['tipe'], t['nominal_default'], karyawan['gaji_pokok'], hari_hadir)
        processed_tunjangan.append({'id': t['id'], 'nama': t['nama_tunjangan'], 'nominal': nom})
        total_tunjangan_lain += nom

    processed_potongan = []
    total_potongan_val = 0
    for p in potongan_list:
        nom = calculate_nominal(p['tipe'], p['nominal_default'], karyawan['gaji_pokok'], hari_hadir)
        processed_potongan.append({'id': p['id'], 'nama': p['nama_potongan'], 'nominal': nom})
        total_potongan_val += nom

    # E. Aggregasi
    total_pendapatan = gaji_pokok_final + karyawan['tunjangan_jabatan'] + total_lembur + total_tunjangan_lain
    gaji_bersih = max(0, total_pendapatan - total_potongan_val)
    tunggakan = abs(total_pendapatan - total_potongan_val) if (total_pendapatan - total_potongan_val) < 0 else 0

    return {
        'meta': {
            'id_karyawan': karyawan['id'],
            'nama': karyawan['nama'],
            'jabatan': karyawan['nama_jabatan'],
            'email': karyawan['email'],
            'periode': datetime.now().strftime("%Y-%m-%d"),
            'hari_hadir': hari_hadir,
            'jam_lembur': (wd_overtime + we_overtime)
        },
        'pendapatan': {
            'gaji_pokok': gaji_pokok_final,
            'tunjangan_jabatan': karyawan['tunjangan_jabatan'],
            'lembur_weekday': uang_lembur_wd,
            'lembur_weekend': uang_lembur_we,
            'total_lembur': total_lembur,
            'total_kotor': total_pendapatan
        },
        'detail': {
            'list_tunjangan': processed_tunjangan,
            'list_potongan': processed_potongan,
            'rincian_tunjangan_dict': {t['nama']: t['nominal'] for t in processed_tunjangan},
            'rincian_potongan_dict': {p['nama']: p['nominal'] for p in processed_potongan}
        },
        'final': {
            'total_potongan': total_potongan_val,
            'tunggakan': tunggakan,
            'gaji_bersih': gaji_bersih
        }
    }

# 4. VIEW / PRESENTATION

def get_user_input_data(employee_name: str) -> Dict[str, float]:
    """Menangani interaksi input user."""
    print(f"\n--- Input Data Periode Ini ({employee_name}) ---")
    
    # 1. Input Hari Hadir
    hari_hadir = get_input_number(f"Jumlah Hari Hadir (Maks {JUMLAH_HARI_KERJA_STANDAR}): ", 0, JUMLAH_HARI_KERJA_STANDAR)
    
    # 2. Input Lembur
    ada_lembur = input("Apakah ada lembur bulan ini? (y/n): ").strip().lower()
    
    if ada_lembur == 'y':
        print(">> Masukkan Detail Lembur:")
        jam_wd = get_input_number("   - Jam Lembur Biasa (Weekday): ", 0)
        jam_we = get_input_number("   - Jam Lembur Libur (Weekend): ", 0)
    else:
        jam_wd, jam_we = 0, 0

    return {
        'hari_hadir': hari_hadir,
        'jam_lembur_weekday': jam_wd,
        'jam_lembur_weekend': jam_we
    }

def preview_salary_slip(data: Dict[str, Any]):
    """Menampilkan preview sederhana di console."""
    inc = data['pendapatan']
    fin = data['final']
    
    print("\n" + "="*40)
    print(f"PREVIEW SLIP GAJI: {data['meta']['nama']}")
    print("-" * 40)
    print(f"Gaji Pokok          : {format_rupiah(inc['gaji_pokok'])}")
    print(f"Tunjangan Jabatan   : {format_rupiah(inc['tunjangan_jabatan'])}")
    if inc['total_lembur'] > 0:
        print(f"Total Lembur        : {format_rupiah(inc['total_lembur'])}")
    print(f"Total Tunjangan Lain: {format_rupiah(sum(t['nominal'] for t in data['detail']['list_tunjangan']))}")
    print("-" * 40)
    print(f"TOTAL PENDAPATAN    : {format_rupiah(inc['total_kotor'])}")
    print(f"TOTAL POTONGAN      : -{format_rupiah(fin['total_potongan'])}")
    print("=" * 40)
    print(f"GAJI BERSIH (THP)   : {format_rupiah(fin['gaji_bersih'])}")
    print("=" * 40)

# 5. MAIN CONTROLLER

def execute_transfer(conn: sqlite3.Connection, salary_data: Dict, gaji_id: int, emp_wallet: sqlite3.Row, comp_acc: sqlite3.Row):
    """Menangani proses transfer API, Update DB, dan Kirim Email."""
    
    gaji_bersih = salary_data['final']['gaji_bersih']
    desc = f"Gaji {salary_data['meta']['nama']} {salary_data['meta']['periode']}"

    res = PaymentGateway.transfer_gaji(
        bank_code=emp_wallet['kode_bank'],
        account_number=emp_wallet['nomor_rekening'],
        amount=gaji_bersih,
        description=desc,
        ref_id=str(gaji_id) # Idempotency Key
    )

    if res['success']:
        print(f"[SUCCESS] TRANSFER BERHASIL: {res['message']}")
        
        success, new_saldo = update_salary_success(
            conn, gaji_id, res['trx_id'], gaji_bersih, comp_acc['id']
        )
        
        if success:
            print(f"[INFO] Saldo Perusahaan Sisa: {format_rupiah(new_saldo)}")

            email_addr = salary_data['meta']['email']
            if email_addr:
                pdf_payload = {
                    'nama_karyawan': salary_data['meta']['nama'],
                    'nama_jabatan': salary_data['meta']['jabatan'],
                    'gaji_pokok': salary_data['pendapatan']['gaji_pokok'],
                    'tunjangan_jabatan': salary_data['pendapatan']['tunjangan_jabatan'],
                    'uang_lembur': salary_data['pendapatan']['total_lembur'], 
                    'lembur_weekday': salary_data['pendapatan']['lembur_weekday'],
                    'lembur_weekend': salary_data['pendapatan']['lembur_weekend'],
                    'rincian_tunjangan': salary_data['detail']['rincian_tunjangan_dict'],
                    'rincian_potongan': salary_data['detail']['rincian_potongan_dict'],
                    'total_gaji_bersih': salary_data['final']['gaji_bersih'],
                    'status_transfer': 'LUNAS (TRANSFER)'
                }
                try:
                    pdf_path = generate_slip_pdf(pdf_payload, salary_data['meta']['periode'])
                    send_payslip_email(email_addr, salary_data['meta']['nama'], salary_data['meta']['periode'], pdf_path)
                    print("[INFO] Email Slip Gaji Terkirim!")
                    if os.path.exists(pdf_path): os.remove(pdf_path)
                except Exception as e:
                    print(f"[WARN] Gagal kirim email: {e}")
        else:
            print("[ERROR] Saldo Gagal Diupdate di DB (Cek Log).")
    else:
        print(f"[FAILED] TRANSFER GAGAL: {res['message']}")

def create_gaji():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        employees = fetch_employees(cur)
        if not employees: 
            print("[!] Data karyawan kosong.")
            return

        print("\n=== FORMULIR PENGGAJIAN ===")
        for k in employees: print(f"{k['id']}. {k['nama']} - {k['nama_jabatan']}")

        try:
            karyawan_id = int(get_input_number("\nPilih ID Karyawan: "))
            selected_emp = next((k for k in employees if k['id'] == karyawan_id), None)
            if not selected_emp: raise ValueError
        except (ValueError, StopIteration):
            print("[!] ID Karyawan tidak ditemukan.")
            return

        if check_duplicate_payroll(cur, karyawan_id):
            bulan_ini_str = datetime.now().strftime("%B %Y")
            print(f"\n[!] PERINGATAN: Gaji untuk {selected_emp['nama']} bulan {bulan_ini_str} SUDAH ADA.")
            print("    Mohon cek menu 'Riwayat Gaji' atau 'Transfer Pending'.")
            return

        tunjangan_db = fetch_components(cur, "tunjangan", karyawan_id)
        potongan_db = fetch_components(cur, "potongan", karyawan_id)

        #  LOOP VALIDASI UTAMA
        while True:
            # 1. Input Data
            input_data = get_user_input_data(selected_emp['nama'])
            
            # 2. Hitung
            salary_data = calculate_payroll(selected_emp, input_data, tunjangan_db, potongan_db)
            
            # 3. Preview
            preview_salary_slip(salary_data)
            
            # 4. Konfirmasi Final
            validasi = input("\n[?] Apakah data sudah benar? (Y/N): ").strip().upper()
            
            if validasi == 'Y':
                break 
            elif validasi == 'N':
                print("\n[INFO] Mengulangi input data...\n")
                continue 
            else:
                print("[!] Pilihan tidak valid.")

        gaji_bersih = salary_data['final']['gaji_bersih']

        # D. SIMPAN DATA (PENDING)
        print("\n[PROCESS] Menyimpan data gaji ke database...")
        gaji_id = save_salary_pending(conn, salary_data)
        print(f"[SUCCESS] Data tersimpan! (ID Gaji: {gaji_id}, Status: SUCCESS)")

        # E. Cek Kelayakan Transfer
        comp_acc, emp_wallet = get_financial_data(cur, karyawan_id)
        
        can_transfer = True
        error_msg = ""

        if not comp_acc:
            can_transfer = False; error_msg = "Rekening Perusahaan belum disetting."
        elif not emp_wallet:
            can_transfer = False; error_msg = "Karyawan belum punya rekening wallet."
        elif comp_acc['saldo'] < gaji_bersih:
            can_transfer = False; error_msg = f"Saldo Perusahaan Kurang (Butuh: {format_rupiah(gaji_bersih)})."
        elif gaji_bersih <= 0:
            can_transfer = False; error_msg = "Gaji Bersih 0 atau Minus."

        if not can_transfer:
            print(f"\n[WARN] Tidak bisa transfer otomatis: {error_msg}")
            print("[INFO] Data tetap aman di database (Pending).")
            return

        # F. Konfirmasi Transfer
        print(f"\n[INFO] Saldo Perusahaan: {format_rupiah(comp_acc['saldo'])}")
        confirm = input(f"Transfer {format_rupiah(gaji_bersih)} sekarang? (Y/N): ").strip().upper()
        
        if confirm == 'Y':
            execute_transfer(conn, salary_data, gaji_id, emp_wallet, comp_acc)
        else:
            print("[INFO] Transfer ditunda. Data tersimpan di 'Transfer Pending'.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_gaji()