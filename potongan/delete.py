# potongan/delete.py
from db import get_connection
# Import fungsi lihat untuk membantu proses pemilihan ID
from .read import lihat_semua_potongan

def delete_potongan():
    """Menghapus data potongan master."""
    
    # 1. Tampilkan data dan minta ID
    lihat_semua_potongan()
    potongan_id = input("\nMasukkan ID potongan yang ingin dihapus: ").strip()
    if not potongan_id.isdigit():
        print("ID harus berupa angka.")
        return
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nama_potongan FROM potongan WHERE id = ?", (potongan_id,))
    data = cur.fetchone()

    if not data:
        print(f"ID potongan {potongan_id} tidak ditemukan.")
        conn.close()
        return
        
    nama_potongan = data[0]

    # 2. Cek relasi dan konfirmasi
    cur.execute("SELECT COUNT(*) FROM karyawan_potongan WHERE potongan_id = ?", (potongan_id,))
    relasi_count = cur.fetchone()[0]

    if relasi_count > 0:
        print(f"\n⚠️ Peringatan: Potongan '{nama_potongan}' terikat dengan {relasi_count} karyawan.")
        konfirmasi = input("Yakin ingin menghapus? (Semua relasi di karyawan_potongan akan hilang) (Y/n): ").strip().lower()
        if konfirmasi != 'y':
            print("Penghapusan dibatalkan.")
            conn.close()
            return
    
    # 3. Eksekusi DELETE
    try:
        # Hapus relasi di tabel pivot
        cur.execute("DELETE FROM karyawan_potongan WHERE potongan_id = ?", (potongan_id,))
        # Hapus dari tabel master
        cur.execute("DELETE FROM potongan WHERE id = ?", (potongan_id,))
        conn.commit()
        print(f"\nPotongan '{nama_potongan}' berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print(f"\nTerjadi kesalahan saat menghapus: {e}")
    finally:
        conn.close()