# tunjangan/delete.py
from db import get_connection
# Import fungsi lihat untuk membantu proses pemilihan ID
from .read import lihat_semua_tunjangan

def delete_tunjangan():
    """Menghapus data tunjangan master."""
    
    # 1. Tampilkan data dan minta ID
    lihat_semua_tunjangan()
    tunjangan_id = input("\nMasukkan ID tunjangan yang ingin dihapus: ").strip()
    if not tunjangan_id.isdigit():
        print("ID harus berupa angka.")
        return
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nama_tunjangan FROM tunjangan WHERE id = ?", (tunjangan_id,))
    data = cur.fetchone()

    if not data:
        print(f"ID tunjangan {tunjangan_id} tidak ditemukan.")
        conn.close()
        return
        
    nama_tunjangan = data[0]

    # 2. Cek relasi dan konfirmasi
    cur.execute("SELECT COUNT(*) FROM karyawan_tunjangan WHERE tunjangan_id = ?", (tunjangan_id,))
    relasi_count = cur.fetchone()[0]

    if relasi_count > 0:
        print(f"\n Peringatan: Tunjangan '{nama_tunjangan}' terikat dengan {relasi_count} karyawan.")
        konfirmasi = input("Yakin ingin menghapus? (Semua relasi di karyawan_tunjangan akan hilang) (Y/n): ").strip().lower()
        if konfirmasi != 'y':
            print("Penghapusan dibatalkan.")
            conn.close()
            return
    
    # 3. Eksekusi DELETE
    try:
        # Hapus relasi di tabel pivot
        cur.execute("DELETE FROM karyawan_tunjangan WHERE tunjangan_id = ?", (tunjangan_id,))
        # Hapus dari tabel master
        cur.execute("DELETE FROM tunjangan WHERE id = ?", (tunjangan_id,))
        conn.commit()
        print(f"\nTunjangan '{nama_tunjangan}' berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print(f"\nTerjadi kesalahan saat menghapus: {e}")
    finally:
        conn.close()