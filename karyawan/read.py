# karyawan/read.py
import sqlite3
from db import get_connection

# --- HELPER: FORMATTING ---
def format_rupiah(value):
    """Format angka ke Rupiah (Rp1.000.000)"""
    return f"Rp{value:,.0f}".replace(",", ".")

def truncate_string(text, max_len):
    """Memotong string jika terlalu panjang agar tabel rapi"""
    if not text: return "-"
    text = str(text)
    return text[:max_len-3] + "..." if len(text) > max_len else text

# --- CORE FUNCTION: DISPLAY TABLE ---
def _display_karyawan_list(query, params, page_size=10):
    """
    Menampilkan tabel karyawan dengan data lengkap termasuk Wallet/Bank.
    Ekspektasi urutan kolom Query: 
    [0]ID, [1]Nama, [2]Jabatan, [3]StatusPegawai, [4]Gaji, [5]Email, [6]Bank, [7]NoRek, [8]IsActive
    """
    conn = get_connection()
    cur = conn.cursor()

    # 1. Hitung Total Data
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cur.execute(count_query, params)
    total_records = cur.fetchone()[0]

    if total_records == 0:
        print("\n[INFO] Data karyawan tidak ditemukan.")
        conn.close()
        return

    # 2. Setup Paginasi
    total_page = (total_records // page_size) + (1 if total_records % page_size else 0)
    current_page = 1

    # 3. Konfigurasi Lebar Kolom
    W = {
        'ID': 4, 'Nama': 20, 'Jabatan': 12, 'Status': 14, # Lebarkan dikit buat label non-aktif
        'Gaji': 14, 'Bank': 8, 'Rekening': 16
    }
    
    header_fmt = (
        f"{'ID':<{W['ID']}} | {'NAMA':<{W['Nama']}} | {'JABATAN':<{W['Jabatan']}} | "
        f"{'STATUS':<{W['Status']}} | {'BANK':<{W['Bank']}} | {'NO. REKENING':<{W['Rekening']}} | "
        f"{'GAJI POKOK':>{W['Gaji']}}"
    )
    separator = "-" * len(header_fmt)

    while True:
        # Fetch Data per Halaman
        offset = (current_page - 1) * page_size
        query_paginate = query + " LIMIT ? OFFSET ?"
        cur.execute(query_paginate, params + (page_size, offset))
        rows = cur.fetchall()

        print(f"\n=== DAFTAR KARYAWAN (Page {current_page}/{total_page} | Total: {total_records}) ===")
        print(separator)
        print(header_fmt)
        print(separator)

        for row in rows:
            # Unpacking data (Pastikan query SELECT-nya sesuai urutan)
            k_id, nama, jab, stat_peg, gaji, email, bank, rek, is_active = row

            # Logic Tampilan Status
            if is_active == 0:
                # Jika non-aktif, tambahkan label visual
                status_display = f"[NA] {stat_peg}" 
            else:
                status_display = stat_peg

            bank_str = bank if bank else "-"
            rek_str  = rek if rek else "-"
            
            print(
                f"{str(k_id):<{W['ID']}} | "
                f"{truncate_string(nama, W['Nama']):<{W['Nama']}} | "
                f"{truncate_string(jab, W['Jabatan']):<{W['Jabatan']}} | "
                f"{truncate_string(status_display, W['Status']):<{W['Status']}} | "
                f"{bank_str:<{W['Bank']}} | "
                f"{rek_str:<{W['Rekening']}} | "
                f"{format_rupiah(gaji):>{W['Gaji']}}"
            )
        
        print(separator)

        # Navigasi
        if total_page == 1: break
        
        action = input("\n[N]ext, [P]rev, [E]xit: ").strip().lower()
        if action == 'n' and current_page < total_page: current_page += 1
        elif action == 'p' and current_page > 1: current_page -= 1
        elif action == 'e': break
        else: print("[!] Input salah / halaman habis.")

    conn.close()

# --- MAIN MENU FUNCTIONS ---

def filter_karyawan(page_size=10):
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== LIHAT DATA KARYAWAN ===")
    print("1. Karyawan Aktif (Default)")
    print("2. Semua Data (Termasuk Non-Aktif)")
    print("3. Cari Nama / ID")
    print("4. Filter per Jabatan")
    
    pilih = input("Pilih (1-4): ").strip()

    # Query Utama: Tambahkan kolom k.is_active di akhir select
    base_query = """
        SELECT 
            k.id, k.nama, j.nama_jabatan, s.nama_status, k.gaji_pokok, k.email,
            w.kode_bank, w.nomor_rekening, k.is_active
        FROM karyawan k
        LEFT JOIN jabatan j ON k.jabatan_id = j.id
        LEFT JOIN status_pegawai s ON k.status_pegawai_id = s.id
        LEFT JOIN karyawan_wallet w ON k.id = w.karyawan_id AND w.is_primary = 1
    """
    
    where_clause = ""
    params = ()

    if pilih == "1": # Default: Hanya Aktif
        where_clause = " WHERE k.is_active = 1"

    elif pilih == "2": # Semua Data
        where_clause = "" # Tidak ada filter, tampil semua

    elif pilih == "3": # Cari (Bisa cari yg non-aktif juga)
        search = input("Masukkan Nama atau ID: ").strip()
        if search.isdigit():
            where_clause = " WHERE k.id = ?"
            params = (int(search),)
        else:
            where_clause = " WHERE k.nama LIKE ?"
            params = (f"%{search}%",)
            
    elif pilih == "4": # Filter Jabatan (Hanya yg aktif saja biar rapi)
        cur.execute("SELECT id, nama_jabatan FROM jabatan")
        jabs = cur.fetchall()
        for j in jabs: print(f"{j[0]}. {j[1]}")
        
        try:
            jid = int(input("Pilih ID Jabatan: "))
            where_clause = " WHERE k.jabatan_id = ? AND k.is_active = 1"
            params = (jid,)
        except:
            print("[!] Input error.")
            conn.close(); return

    conn.close() 
    
    final_query = base_query + where_clause
    _display_karyawan_list(final_query, params, page_size)


def lihat_tunjangan_potongan():
    """Melihat detail rincian per karyawan (One-by-One View)"""
    conn = get_connection()
    cur = conn.cursor()

    keyword = input("\nCari Karyawan (Nama/ID): ").strip()
    if not keyword: return

    # Tambahkan is_active di select
    query_search = "SELECT id, nama, email, is_active FROM karyawan WHERE "
    if keyword.isdigit():
        query_search += "id = ?"
        params = (int(keyword),)
    else:
        query_search += "nama LIKE ?"
        params = (f"%{keyword}%",)
    
    cur.execute(query_search, params)
    karyawan_list = cur.fetchall()

    if not karyawan_list:
        print("[!] Karyawan tidak ditemukan.")
        conn.close(); return

    for k in karyawan_list:
        kid, knama, kemail, kactive = k
        
        # Label Status di Detail View
        status_label = "" if kactive == 1 else " [NON-AKTIF / RESIGN]"

        print("\n" + "="*50)
        print(f"DETAIL KARYAWAN: {knama.upper()} (ID: {kid}){status_label}")
        print("="*50)
        print(f"Email: {kemail}")

        # 1. Info Wallet
        cur.execute("SELECT kode_bank, nomor_rekening, atas_nama_rekening FROM karyawan_wallet WHERE karyawan_id = ? AND is_primary=1", (kid,))
        wallet = cur.fetchone()
        if wallet:
            print(f"Rekening: {wallet[0]} - {wallet[1]} (a.n {wallet[2]})")
        else:
            print("Rekening: [BELUM DISETTING]")
        
        print("-" * 50)

        # 2. Tunjangan
        cur.execute("""
            SELECT t.nama_tunjangan, t.nominal_default, t.tipe 
            FROM karyawan_tunjangan kt JOIN tunjangan t ON kt.tunjangan_id = t.id 
            WHERE kt.karyawan_id = ?
        """, (kid,))
        tunj = cur.fetchall()
        
        print(f"[+] TUNJANGAN TERDAFTAR ({len(tunj)} item):")
        for t in tunj:
            val = f"{t[1]}%" if t[2] == 'persentase' else format_rupiah(t[1])
            print(f"    - {t[0]:<20} : {val:>15} ({t[2]})")

        print("-" * 50)

        # 3. Potongan
        cur.execute("""
            SELECT p.nama_potongan, p.nominal_default, p.tipe 
            FROM karyawan_potongan kp JOIN potongan p ON kp.potongan_id = p.id 
            WHERE kp.karyawan_id = ?
        """, (kid,))
        pot = cur.fetchall()
        
        print(f"[-] POTONGAN TERDAFTAR ({len(pot)} item):")
        for p in pot:
            val = f"{p[1]}%" if p[2] == 'persentase' else format_rupiah(p[1])
            print(f"    - {p[0]:<20} : {val:>15} ({p[2]})")
            
        print("="*50 + "\n")

    conn.close()