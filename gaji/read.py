from db import get_connection

def lihat_riwayat_gaji(page_size=10):
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== FILTER RIWAYAT GAJI ===")
    search = input("Cari riwayat berdasarkan Nama Karyawan atau ID (kosong = semua): ").strip()

    # Query dasar untuk mendapatkan riwayat gaji beserta nama karyawan
    base_query = """
        SELECT g.id, k.nama, g.periode, g.total_gaji
        FROM gaji g
        JOIN karyawan k ON g.karyawan_id = k.id
    """
    params = ()

    # Menambahkan kondisi WHERE berdasarkan input search
    if search:
        if search.isdigit():
            base_query += " WHERE k.id = ?"
            params = (int(search),)
        else:
            base_query += " WHERE k.nama LIKE ?"
            params = (f"%{search}%",)

    # Urutkan dari yang terbaru
    base_query += " ORDER BY g.periode DESC"
    
    # Hitung total hasil
    count_query = "SELECT COUNT(*) FROM (" + base_query + ")"
    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    if total == 0:
        print("Riwayat gaji tidak ditemukan.")
        conn.close()
        return

    total_page = (total // page_size) + (1 if total % page_size else 0)
    current_page = 1

    # --- Tampilan dengan Paginasi ---
    while True:
        offset = (current_page - 1) * page_size
        query_paginate = base_query + " LIMIT ? OFFSET ?"
        cur.execute(query_paginate, params + (page_size, offset))
        data = cur.fetchall()

        print(f"\n=== RIWAYAT GAJI KARYAWAN (Page {current_page}/{total_page}) ===")
        
        # Header Tabel
        header = f"{'ID Slip':<8} {'Nama Karyawan':<25} {'Periode':<15} {'Total Gaji Bersih':>20}"
        separator = "-" * len(header)
        print(separator)
        print(header)
        print(separator)

        for row in data:
            # Menggunakan f-string dengan padding yang benar
            gaji_bersih_str = f"Rp{row[3]:,.0f}" 
            
            print(
                f"{row[0]:<8} "
                f"{row[1]:<25} "
                f"{row[2]:<15} "
                f"{gaji_bersih_str:>20}" 
            )
        
        print(separator)

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
            print("Pilihan tidak valid atau halaman tidak tersedia.")

    conn.close()