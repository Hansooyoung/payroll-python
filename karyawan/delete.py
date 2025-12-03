# karyawan/delete.py
from db import get_connection

def delete_karyawan():
    conn = get_connection()
    cur = conn.cursor()

    karyawan_id = input("Masukkan ID karyawan yang ingin dihapus: ").strip()
    if not karyawan_id.isdigit():
        print("ID harus berupa angka.")
        conn.close()
        return

    cur.execute("SELECT nama FROM karyawan WHERE id = ?", (karyawan_id,))
    karyawan_data = cur.fetchone()

    if not karyawan_data:
        print(f"Karyawan dengan ID {karyawan_id} tidak ditemukan.")
        conn.close()
        return

    konfirmasi = input(f"Yakin ingin menghapus karyawan '{karyawan_data[0]}' (ID: {karyawan_id})? (Y/n): ").strip().lower()

    if konfirmasi == 'y':
        try:
            # Hapus data terkait di tabel pivot/relasi terlebih dahulu (penting!)
            cur.execute("DELETE FROM karyawan_tunjangan WHERE karyawan_id = ?", (karyawan_id,))
            cur.execute("DELETE FROM karyawan_potongan WHERE karyawan_id = ?", (karyawan_id,))
            cur.execute("DELETE FROM gaji WHERE karyawan_id = ?", (karyawan_id,)) # Hapus riwayat gaji

            # Hapus data karyawan utama
            cur.execute("DELETE FROM karyawan WHERE id = ?", (karyawan_id,))
            conn.commit()
            print(f"\nKaryawan '{karyawan_data[0]}' berhasil dihapus sepenuhnya.\n")
        except Exception as e:
            conn.rollback()
            print(f"\nTerjadi kesalahan saat menghapus: {e}\n")
        finally:
            conn.close()
    else:
        print("Penghapusan dibatalkan.")
        conn.close()