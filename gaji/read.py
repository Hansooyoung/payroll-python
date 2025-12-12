# gaji/read.py
import sqlite3
from db import get_connection

def format_rupiah(value):
    """Format angka ke Rupiah (Rp1.000.000)"""
    return f"Rp{value:,.0f}".replace(",", ".")

def lihat_riwayat_gaji(page_size=10):
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== FILTER RIWAYAT GAJI ===")
    search = input("Cari (Nama/ID) [Kosong = Semua]: ").strip()

    # UPDATE QUERY: 
    # 1. Ambil k.is_active (untuk tahu status karyawan)
    # 2. Ambil g.status_transfer (untuk tahu status pembayaran)
    base_query = """
        SELECT 
            g.id, 
            k.nama, 
            k.is_active,
            g.periode, 
            g.total_gaji,
            g.status_transfer
        FROM gaji g
        JOIN karyawan k ON g.karyawan_id = k.id
    """
    
    params = ()
    where_clauses = []

    # Filter Search
    if search:
        if search.isdigit():
            where_clauses.append("k.id = ?")
            params = (int(search),)
        else:
            where_clauses.append("k.nama LIKE ?")
            params = (f"%{search}%",)

    # Gabungkan Where Clause
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)

    # Urutkan: Periode Terbaru -> ID Terbesar
    base_query += " ORDER BY g.periode DESC, g.id DESC"
    
    # Hitung Total Data
    count_query = f"SELECT COUNT(*) FROM ({base_query})"
    cur.execute(count_query, params)
    total_records = cur.fetchone()[0]

    if total_records == 0:
        print("\n[INFO] Riwayat gaji tidak ditemukan.")
        conn.close()
        return

    # Setup Paginasi
    total_page = (total_records // page_size) + (1 if total_records % page_size else 0)
    current_page = 1

    # Konfigurasi Lebar Kolom
    # ID(5) | Nama(25) | Periode(12) | Status(10) | Total(18)
    header_fmt = f"{'ID':<5} {'Nama Karyawan':<25} {'Periode':<12} {'Status':<10} {'Total Gaji':>18}"
    separator = "-" * len(header_fmt)

    while True:
        offset = (current_page - 1) * page_size
        query_paginate = base_query + " LIMIT ? OFFSET ?"
        cur.execute(query_paginate, params + (page_size, offset))
        data = cur.fetchall()

        print(f"\n=== RIWAYAT GAJI (Page {current_page}/{total_page} | Total: {total_records}) ===")
        print(separator)
        print(header_fmt)
        print(separator)

        for row in data:
            gid, knama, kactive, periode, total, status = row
            
            # Logic Tampilan Nama (Tambah [NA] jika non-aktif)
            nama_display = knama
            if kactive == 0:
                nama_display += " [NA]"
            
            # Logic Tampilan Nama & Truncate jika kepanjangan
            if len(nama_display) > 24:
                nama_display = nama_display[:21] + "..."

            # Formatting Baris
            print(
                f"{gid:<5} "
                f"{nama_display:<25} "
                f"{periode:<12} "
                f"{status:<10} "
                f"{format_rupiah(total):>18}"
            )
        
        print(separator)
        print("Ket: [NA] = Karyawan Non-Aktif/Resign")

        if total_page == 1:
            break

        action = input("\n[N]ext, [P]rev, [E]xit: ").strip().lower()
        if action == "n" and current_page < total_page:
            current_page += 1
        elif action == "p" and current_page > 1:
            current_page -= 1
        elif action == "e":
            break
        else:
            print("[!] Pilihan tidak valid.")

    conn.close()