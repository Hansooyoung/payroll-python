# tunjangan/assign.py
from db import get_connection

def assign_tunjangan(karyawan_id):
    conn = get_connection()
    cur = conn.cursor()

    # --- 0. VALIDASI STATUS KARYAWAN (NEW LOGIC) ---
    # Cek apakah karyawan ada dan MASIH AKTIF
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
        print("Anda tidak dapat menetapkan tunjangan baru untuk karyawan yang sudah dinonaktifkan.")
        conn.close()
        return
    # ------------------------------------------------

    # --- 1. Ambil Tunjangan yang BELUM Dimiliki Karyawan (Anti-Duplicate View) ---
    cur.execute("""
        SELECT t.id, t.nama_tunjangan, t.nominal_default, t.tipe
        FROM tunjangan t
        LEFT JOIN karyawan_tunjangan kt
            ON t.id = kt.tunjangan_id AND kt.karyawan_id = ?
        WHERE kt.tunjangan_id IS NULL 
    """, (karyawan_id,))
    
    tunjangan_data_tersedia = cur.fetchall()
    
    if not tunjangan_data_tersedia:
        print(f"\nKaryawan '{nama_karyawan}' SUDAH memiliki semua jenis tunjangan master yang ada.")
        conn.close()
        return

    # --- 2. Tampilkan Daftar Tunjangan yang Tersedia ---
    print(f"\n=== TUNJANGAN TERSEDIA UNTUK: {nama_karyawan.upper()} ===")
    t_header = f"{'ID':<4} {'Nama Tunjangan':<25} {'Nominal Default':>18} {'Tipe':<10}"
    separator = "-" * len(t_header)
    print(separator)
    print(t_header)
    print(separator)
    
    tunjangan_ids_tersedia = []
    
    for t in tunjangan_data_tersedia:
        # Format nominal rupiah atau persen
        nominal_str = f"Rp{t[2]:,.0f}" if t[3] in ['tetap', 'per_hari'] else f"{t[2]}%"
        
        print(f"{t[0]:<4} {t[1]:<25} {nominal_str:>18} {t[3]:<10}")
        tunjangan_ids_tersedia.append(t[0])
    print(separator)

    # --- 3. Proses Penetapan ---
    print(f"\n--- Kelola Tunjangan Karyawan ID {karyawan_id} ---")
    
    while True:
        try:
            tunjangan_id = int(input("Masukkan ID tunjangan yang ingin ditetapkan (0 untuk selesai): "))
            if tunjangan_id == 0:
                break
            
            if tunjangan_id in tunjangan_ids_tersedia:
                cur.execute("""
                    INSERT INTO karyawan_tunjangan (karyawan_id, tunjangan_id)
                    VALUES (?, ?)
                """, (karyawan_id, tunjangan_id))
                conn.commit()
                print(f"✅ Tunjangan ID {tunjangan_id} berhasil ditetapkan!")
                
                # Hapus dari list agar tidak dipilih ulang
                tunjangan_ids_tersedia.remove(tunjangan_id)
            else:
                print("[!] ID tidak valid, sudah dimiliki, atau tidak ditemukan.")
        except ValueError:
            print("[!] Input harus angka.")

    conn.close()