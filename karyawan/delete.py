# karyawan/delete.py
from db import get_connection

def delete_karyawan():
    """
    Menghapus karyawan dengan logika keamanan data (Hybrid Approach):
    1. Jika sudah ada riwayat gaji -> Ubah is_active = 0 (Soft Delete).
    2. Jika belum ada riwayat gaji -> Hapus permanen (Hard Delete).
    """
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== HAPUS / NON-AKTIFKAN KARYAWAN ===")

    # 1. Input ID
    karyawan_id = input("Masukkan ID karyawan: ").strip()
    if not karyawan_id.isdigit():
        print("[!] ID harus berupa angka.")
        conn.close()
        return

    # 2. Cek Data Karyawan
    # Kita ambil nama dan status aktif saat ini
    cur.execute("SELECT nama, is_active FROM karyawan WHERE id = ?", (karyawan_id,))
    karyawan_data = cur.fetchone()

    if not karyawan_data:
        print(f"[!] Karyawan dengan ID {karyawan_id} tidak ditemukan.")
        conn.close()
        return

    nama_karyawan = karyawan_data[0]
    is_active_now = karyawan_data[1]

    # Cek jika memang sudah non-aktif
    if is_active_now == 0:
        print(f"\n[INFO] Karyawan '{nama_karyawan}' sudah berstatus NON-AKTIF.")
        print("Tips: Gunakan menu Update jika ingin mengaktifkan kembali.")
        conn.close()
        return

    # 3. Cek Riwayat Transaksi Gaji (CRITICAL CHECK)
    cur.execute("SELECT COUNT(*) FROM gaji WHERE karyawan_id = ?", (karyawan_id,))
    jumlah_slip_gaji = cur.fetchone()[0]

    print(f"\nAnalisis Data '{nama_karyawan}':")
    print(f"- Riwayat Gaji: {jumlah_slip_gaji} slip ditemukan")

    # ==========================================
    # SKENARIO A: SUDAH PERNAH GAJIAN (SOFT DELETE)
    # ==========================================
    if jumlah_slip_gaji > 0:
        print("\n🔒 MODE PROTEKSI AKTIF")
        print("Karyawan ini memiliki data keuangan. TIDAK BISA dihapus permanen.")
        print("Sistem hanya akan menonaktifkan akun ini (Arsip).")
        
        konfirmasi = input(f"Non-aktifkan karyawan '{nama_karyawan}'? (Y/n): ").strip().lower()
        if konfirmasi == 'y':
            try:
                # Update kolom is_active menjadi 0
                cur.execute("UPDATE karyawan SET is_active = 0 WHERE id = ?", (karyawan_id,))
                conn.commit()
                print(f"\n✅ Sukses! Karyawan '{nama_karyawan}' kini NON-AKTIF.")
                print("Data gaji dan profil tetap tersimpan aman.")
            except Exception as e:
                conn.rollback()
                print(f"Gagal update: {e}")
        else:
            print("Proses dibatalkan.")

    # ==========================================
    # SKENARIO B: DATA BARU / BELUM GAJIAN (HARD DELETE)
    # ==========================================
    else:
        print("\n🗑️  MODE BERSIH-BERSIH")
        print("Karyawan ini belum punya riwayat gaji. Aman untuk dihapus permanen.")
        
        konfirmasi = input(f"Yakin HAPUS PERMANEN '{nama_karyawan}'? (Y/n): ").strip().lower()
        if konfirmasi == 'y':
            try:
                # Hapus bersih semua relasi anak
                cur.execute("DELETE FROM karyawan_tunjangan WHERE karyawan_id = ?", (karyawan_id,))
                cur.execute("DELETE FROM karyawan_potongan WHERE karyawan_id = ?", (karyawan_id,))
                cur.execute("DELETE FROM karyawan_wallet WHERE karyawan_id = ?", (karyawan_id,))
                
                # Hapus induk
                cur.execute("DELETE FROM karyawan WHERE id = ?", (karyawan_id,))
                conn.commit()
                print(f"\n✅ Sukses! Data karyawan '{nama_karyawan}' telah dihapus permanen.")
            except Exception as e:
                conn.rollback()
                print(f"Gagal menghapus: {e}")
        else:
            print("Proses dibatalkan.")

    conn.close()

if __name__ == "__main__":
    delete_karyawan()