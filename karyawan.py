from db import get_connection

def _display_karyawan_list(query, params, page_size=10):
    """Helper function untuk menampilkan hasil query karyawan dengan paginasi dan format tabel."""
    conn = get_connection()
    cur = conn.cursor()

    # Hitung total hasil
    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    if total == 0:
        print("Karyawan tidak ditemukan.")
        conn.close()
        return

    total_page = (total // page_size) + (1 if total % page_size else 0)
    current_page = 1

    # Definisikan lebar kolom
    COL_WIDTH = {
        'ID': 4,
        'Nama': 25,
        'Jabatan': 15,
        'Status': 12,
        'Gaji Pokok': 15,
        'Email': 30
    }
    
    # Header Tabel
    header = (
        f"{'ID':<{COL_WIDTH['ID']}} "
        f"{'NAMA':<{COL_WIDTH['Nama']}} "
        f"{'JABATAN':<{COL_WIDTH['Jabatan']}} "
        f"{'STATUS':<{COL_WIDTH['Status']}} "
        f"{'GAJI POKOK':>{COL_WIDTH['Gaji Pokok']}} "
        f"{'EMAIL':<{COL_WIDTH['Email']}}"
    )
    separator = "-" * len(header)


    while True:
        offset = (current_page - 1) * page_size
        query_paginate = query + " LIMIT ? OFFSET ?"
        cur.execute(query_paginate, params + (page_size, offset))
        data = cur.fetchall()

        print(f"\n=== DAFTAR KARYAWAN (Page {current_page}/{total_page}) ===")
        print(separator)
        print(header)
        print(separator)

        for row in data:
            # Format Gaji Pokok untuk output
            gaji_pokok_str = f"Rp{row[4]:,.0f}"

            # Baris Data
            print(
                f"{str(row[0]):<{COL_WIDTH['ID']}} "
                f"{row[1]:<{COL_WIDTH['Nama']}} "
                f"{row[2]:<{COL_WIDTH['Jabatan']}} "
                f"{row[3]:<{COL_WIDTH['Status']}} "
                f"{gaji_pokok_str:>{COL_WIDTH['Gaji Pokok']}} "
                f"{row[5] if row[5] else '-':<{COL_WIDTH['Email']}}"
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

def filter_karyawan(page_size=10):
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== FILTER KARYAWAN ===")
    print("1. Cari berdasarkan Nama/ID")
    print("2. Filter berdasarkan Jabatan")
    print("3. Lihat Semua Karyawan")
    
    pilih = input("Pilih filter (1/2/3): ").strip()

    base_query = """
        SELECT k.id, k.nama, j.nama_jabatan, s.nama_status, k.gaji_pokok, k.email
        FROM karyawan k
        LEFT JOIN jabatan j ON k.jabatan_id = j.id
        LEFT JOIN status_pegawai s ON k.status_pegawai_id = s.id
    """
    where_clause = ""
    params = ()

    if pilih == "1":
        search = input("Masukkan Nama/ID karyawan: ").strip()
        if search.isdigit():
            where_clause = " WHERE k.id = ?"
            params = (int(search),)
        elif search:
            where_clause = " WHERE k.nama LIKE ?"
            params = (f"%{search}%",)
    
    elif pilih == "2":
        # Tampilkan daftar jabatan
        cur.execute("SELECT id, nama_jabatan FROM jabatan")
        jabatan_data = cur.fetchall()
        
        if not jabatan_data:
            print("Data jabatan kosong!")
            conn.close()
            return
            
        print("\nPilih Jabatan:")
        for j in jabatan_data:
            print(f"{j[0]}. {j[1]}")
            
        while True:
            try:
                jabatan_id = int(input("Masukkan ID jabatan: "))
                if any(j[0] == jabatan_id for j in jabatan_data):
                    where_clause = " WHERE k.jabatan_id = ?"
                    params = (jabatan_id,)
                    break
                print("ID jabatan tidak ditemukan!\n")
            except ValueError:
                print("Input harus angka!\n")
        
    elif pilih == "3":
        # Lihat semua, where_clause dan params kosong
        pass
    else:
        print("Pilihan tidak valid!")
        conn.close()
        return

    # Gabungkan query
    final_query = base_query + where_clause
    conn.close() # Tutup koneksi sementara sebelum masuk ke helper function baru
    _display_karyawan_list(final_query, params, page_size)


def lihat_karyawan():
    """Menu utama untuk melihat/memfilter karyawan."""
    filter_karyawan()


def lihat_tunjangan_potongan(page_size=10):
    """Melihat tunjangan dan potongan yang dimiliki per karyawan (Tampilan diperbarui sedikit)."""
    conn = get_connection()
    cur = conn.cursor()

    search = input("\nCari karyawan untuk lihat rincian (nama/ID, kosong = semua): ").strip()

    # Query dasar karyawan
    query = """
        SELECT id, nama FROM karyawan
    """
    params = ()

    if search:
        if search.isdigit():
            query += " WHERE id = ?"
            params = (int(search),)
        else:
            query += " WHERE nama LIKE ?"
            params = (f"%{search}%",)

    # Hitung total hasil
    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    cur.execute(count_query, params)
    total = cur.fetchone()[0]

    if total == 0:
        print("Karyawan tidak ditemukan.")
        conn.close()
        return

    total_page = (total // page_size) + (1 if total % page_size else 0)
    current_page = 1

    while True:
        offset = (current_page - 1) * page_size
        query_paginate = query + " LIMIT ? OFFSET ?"
        cur.execute(query_paginate, params + (page_size, offset))
        data = cur.fetchall()

        for k in data:
            print(f"\n--- Rincian Karyawan: {k[1]} (ID: {k[0]}) ---")
            
            # Ambil tunjangan
            cur.execute("""
                SELECT t.nama_tunjangan, t.nominal_default, t.tipe
                FROM karyawan_tunjangan kt
                JOIN tunjangan t ON kt.tunjangan_id = t.id
                WHERE kt.karyawan_id = ?
            """, (k[0],))
            tunjangan = cur.fetchall()
            
            print("\n  **TUNJANGAN KHUSUS:**")
            if tunjangan:
                # Tunjangan dalam bentuk tabel mini
                tunj_header = f"  {'Nama Tunjangan':<20} {'Nominal Default':>18} {'Tipe':<10}"
                print("  " + "=" * len(tunj_header))
                print(tunj_header)
                print("  " + "=" * len(tunj_header))
                for row in tunjangan:
                    nominal_str = f"Rp{row[1]:,.0f}" if row[2] != 'persentase' else f"{row[1]}%"
                    print(f"  {row[0]:<20} {nominal_str:>18} {row[2]:<10}")
                print("  " + "=" * len(tunj_header))
            else:
                print("  - Tidak ada tunjangan khusus yang ditetapkan.")


            # Ambil potongan
            cur.execute("""
                SELECT p.nama_potongan, p.nominal_default, p.tipe
                FROM karyawan_potongan kp
                JOIN potongan p ON kp.potongan_id = p.id
                WHERE kp.karyawan_id = ?
            """, (k[0],))
            potongan = cur.fetchall()

            print("\n  **POTONGAN KHUSUS:**")
            if potongan:
                # Potongan dalam bentuk tabel mini
                pot_header = f"  {'Nama Potongan':<20} {'Nominal Default':>18} {'Tipe':<10}"
                print("  " + "=" * len(pot_header))
                print(pot_header)
                print("  " + "=" * len(pot_header))
                for row in potongan:
                    nominal_str = f"Rp{row[1]:,.0f}" if row[2] == 'tetap' else f"{row[1]}%"
                    print(f"  {row[0]:<20} {nominal_str:>18} {row[2]:<10}")
                print("  " + "=" * len(pot_header))
            else:
                print("  - Tidak ada potongan khusus yang ditetapkan.")

        # Navigasi halaman
        if total_page == 1:
            break

        print(f"\nPage {current_page}/{total_page}")
        action = input("[N]ext, [P]rev, [E]xit: ").strip().lower()
        if action == "n" and current_page < total_page:
            current_page += 1
        elif action == "p" and current_page > 1:
            current_page -= 1
        elif action == "e":
            break
        else:
            print("Pilihan tidak valid atau halaman tidak tersedia.")

    conn.close()


def tambah_karyawan():
    conn = get_connection()
    cur = conn.cursor()

    # === INPUT NAMA ===
    while True:
        nama = input("Nama karyawan: ").strip()
        if nama:
            break
        print("Nama tidak boleh kosong!\n")

    # === PILIH JABATAN ===
    print("\nPilih Jabatan:")
    cur.execute("SELECT * FROM jabatan")
    jabatan_data = cur.fetchall()

    if not jabatan_data:
        print("Data jabatan kosong!\n")
        conn.close()
        return

    # Tampilan daftar jabatan
    j_header = f"{'ID':<4} {'Jabatan':<15} {'Tunjangan Jabatan':>20}"
    j_separator = "-" * len(j_header)
    print(j_separator)
    print(j_header)
    print(j_separator)
    for j in jabatan_data:
        print(f"{j[0]:<4} {j[1]:<15} {f'Rp{j[2]:,.0f}':>20}")
    print(j_separator)

    while True:
        try:
            jabatan_id = int(input("Masukkan ID jabatan: "))
            if any(j[0] == jabatan_id for j in jabatan_data):
                break
            print("ID jabatan tidak ditemukan!\n")
        except ValueError:
            print("Input harus angka!\n")

    # === PILIH STATUS PEGAWAI ===
    print("\nPilih Status Pegawai:")
    cur.execute("SELECT * FROM status_pegawai")
    status_data = cur.fetchall()

    if not status_data:
        print("Data status pegawai kosong!\n")
        conn.close()
        return

    for s in status_data:
        print(f"{s[0]}. {s[1]}")

    while True:
        try:
            status_id = int(input("Masukkan ID status pegawai: "))
            if any(s[0] == status_id for s in status_data):
                break
            print("ID status tidak ditemukan!\n")
        except ValueError:
            print("Input harus angka!\n")

    # === INPUT GAJI POKOK ===
    while True:
        try:
            gaji_pokok = float(input("Gaji Pokok: "))
            if gaji_pokok >= 0:
                break
            print("Gaji pokok tidak boleh negatif!\n")
        except ValueError:
            print("Input harus angka!\n")

    # === INPUT EMAIL (boleh kosong) ===
    email = input("Email (kosong jika tidak ada): ").strip() or None

    # === INSERT KE DATABASE ===
    cur.execute(
        "INSERT INTO karyawan (nama, jabatan_id, status_pegawai_id, gaji_pokok, email) VALUES (?, ?, ?, ?, ?)",
        (nama, jabatan_id, status_id, gaji_pokok, email)
    )
    conn.commit()
    conn.close()

    print(f"\nKaryawan '{nama}' berhasil ditambahkan!\n")