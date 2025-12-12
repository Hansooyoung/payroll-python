# potongan/assign.py
from db import get_connection

def assign_potongan(karyawan_id):
    conn = get_connection()
    cur = conn.cursor()

    # --- 0. VALIDASI STATUS KARYAWAN (NEW LOGIC) ---
    # Kita harus cek dulu, jangan sampai assign potongan ke karyawan yang sudah resign/dihapus
    cur.execute("SELECT nama, is_active FROM karyawan WHERE id = ?", (karyawan_id,))
    karyawan = cur.fetchone()

    if not karyawan:
        print(f"[!] Karyawan ID {karyawan_id} tidak ditemukan.")
        conn.close()
        return

    nama_karyawan = karyawan[0]
    is_active = karyawan[1]

    if is_active == 0:
        print(f"\n⚠️  GAGAL: Karyawan '{nama_karyawan}' berstatus NON-AKTIF.")
        print("Anda tidak dapat menetapkan potongan baru untuk karyawan yang sudah dinonaktifkan.")
        conn.close()
        return
    # ------------------------------------------------

    # --- 1. Ambil Potongan yang BELUM Dimiliki Karyawan (Anti-Duplicate View) ---
    cur.execute("""
        SELECT p.id, p.nama_potongan, p.nominal_default, p.tipe
        FROM potongan p
        LEFT JOIN karyawan_potongan kp 
            ON p.id = kp.potongan_id AND kp.karyawan_id = ?
        WHERE kp.potongan_id IS NULL 
    """, (karyawan_id,))
    
    potongan_data_tersedia = cur.fetchall()
    
    if not potongan_data_tersedia:
        print(f"\nKaryawan '{nama_karyawan}' SUDAH memiliki semua jenis potongan master yang ada.")
        conn.close()
        return

    # --- 2. Tampilkan Daftar Potongan yang Tersedia untuk Ditetapkan ---
    print(f"\n=== POTONGAN TERSEDIA UNTUK: {nama_karyawan.upper()} ===")
    p_header = f"{'ID':<4} {'Nama Potongan':<25} {'Nominal Default':>18} {'Tipe':<10}"
    separator = "-" * len(p_header)
    print(separator)
    print(p_header)
    print(separator)
    
    potongan_ids_tersedia = []
    
    for p in potongan_data_tersedia:
        nominal_str = f"Rp{p[2]:,.0f}" if p[3] == 'tetap' else f"{p[2]}%"
        print(f"{p[0]:<4} {p[1]:<25} {nominal_str:>18} {p[3]:<10}")
        potongan_ids_tersedia.append(p[0])
    print(separator)

    # --- 3. Proses Penetapan ---
    print(f"\n--- Kelola Potongan Karyawan ID {karyawan_id} ---")
    
    while True:
        try:
            potongan_id = int(input("Masukkan ID potongan yang ingin ditetapkan (0 untuk selesai): "))
            if potongan_id == 0:
                break
            
            if potongan_id in potongan_ids_tersedia:
                cur.execute("""
                    INSERT INTO karyawan_potongan (karyawan_id, potongan_id)
                    VALUES (?, ?)
                """, (karyawan_id, potongan_id))
                conn.commit()
                print(f"✅ Potongan ID {potongan_id} berhasil ditetapkan!")
                
                # Hapus dari daftar tersedia agar tidak bisa diinput ulang
                potongan_ids_tersedia.remove(potongan_id) 
            else:
                print("[!] ID tidak valid, sudah dimiliki, atau tidak ditemukan.")
        except ValueError:
            print("[!] Input harus angka.")

    conn.close()