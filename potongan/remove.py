# potongan/remove.py
from db import get_connection

def remove_potongan(karyawan_id):
    """Menghapus (remove) relasi potongan dari seorang karyawan."""
    conn = get_connection()
    cur = conn.cursor()

    # --- 0. VALIDASI STATUS KARYAWAN (NEW) ---
    # Cek dulu: Karyawannya ada? Masih aktif?
    cur.execute("SELECT nama, is_active FROM karyawan WHERE id = ?", (karyawan_id,))
    karyawan = cur.fetchone()

    if not karyawan:
        print(f"[!] Karyawan ID {karyawan_id} tidak ditemukan.")
        conn.close()
        return

    nama_karyawan = karyawan[0]
    is_active = karyawan[1]

    if is_active == 0:
        print(f"\n⚠️  INFO: Karyawan '{nama_karyawan}' berstatus NON-AKTIF.")
        print("Data potongan tidak dapat diubah karena karyawan sudah diarsipkan.")
        conn.close()
        return
    # -----------------------------------------

    # --- 1. Ambil Data Potongan ---
    cur.execute("""
        SELECT kp.id, p.nama_potongan, p.nominal_default, p.tipe
        FROM karyawan_potongan kp
        JOIN potongan p ON kp.potongan_id = p.id
        WHERE kp.karyawan_id = ?
    """, (karyawan_id,))
    data = cur.fetchall()

    if not data:
        print(f"\nTidak ada potongan ter-assign untuk '{nama_karyawan}'.")
        conn.close()
        return

    # --- 2. Tampilkan List ---
    print(f"\n--- HAPUS POTONGAN DARI: {nama_karyawan.upper()} ---")
    print(f"{'ID PIVOT':<10} | {'NAMA POTONGAN'}")
    print("-" * 40)
    
    valid_pivot_ids = []
    for d in data:
        print(f"{d[0]:<10} | {d[1]}")
        valid_pivot_ids.append(d[0])
    
    print("-" * 40)
    print("Catatan: Masukkan ID PIVOT (angka di kolom kiri), bukan ID Master.")

    # --- 3. Eksekusi Hapus ---
    while True:
        try:
            kp_id = int(input("Masukkan ID Pivot yang ingin dihapus (0 untuk selesai): "))
            if kp_id == 0:
                break
            
            if kp_id in valid_pivot_ids:
                cur.execute("DELETE FROM karyawan_potongan WHERE id = ?", (kp_id,))
                conn.commit()
                print("✅ Potongan berhasil dihapus dari karyawan!")
                
                # Update list valid_ids agar tidak bisa dihapus dua kali
                valid_pivot_ids.remove(kp_id)
            else:
                print("[!] ID Pivot tidak ditemukan di daftar atas.")
        except ValueError:
            print("[!] Input harus angka.")

    conn.close()