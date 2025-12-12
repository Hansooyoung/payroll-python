# tunjangan/remove.py
from db import get_connection

def remove_tunjangan(karyawan_id):
    """Menghapus (remove) relasi tunjangan dari seorang karyawan."""
    conn = get_connection()
    cur = conn.cursor()

    # --- 0. VALIDASI STATUS KARYAWAN (NEW) ---
    # Cek apakah karyawan ada dan masih aktif
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
        print("Data tunjangan tidak dapat diubah karena karyawan sudah diarsipkan.")
        conn.close()
        return
    # -----------------------------------------

    # --- 1. Ambil Data Tunjangan Karyawan ---
    cur.execute("""
        SELECT kt.id, t.nama_tunjangan
        FROM karyawan_tunjangan kt
        JOIN tunjangan t ON kt.tunjangan_id = t.id
        WHERE kt.karyawan_id = ?
    """, (karyawan_id,))
    data = cur.fetchall()

    if not data:
        print(f"\nTidak ada tunjangan ter-assign untuk '{nama_karyawan}'.")
        conn.close()
        return

    # --- 2. Tampilkan List ---
    print(f"\n--- HAPUS TUNJANGAN DARI: {nama_karyawan.upper()} ---")
    print(f"{'ID PIVOT':<10} | {'NAMA TUNJANGAN'}")
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
            kt_id = int(input("Masukkan ID Pivot yang ingin dihapus (0 untuk selesai): "))
            if kt_id == 0:
                break
            
            if kt_id in valid_pivot_ids:
                cur.execute("DELETE FROM karyawan_tunjangan WHERE id = ?", (kt_id,))
                conn.commit()
                print("✅ Tunjangan berhasil dihapus dari karyawan!")
                
                # Update list agar tidak bisa dihapus lagi
                valid_pivot_ids.remove(kt_id)
            else:
                print("[!] ID Pivot tidak valid atau sudah dihapus.")
        except ValueError:
            print("[!] Input harus angka.")

    conn.close()