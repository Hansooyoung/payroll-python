# tunjangan/remove.py
from db import get_connection

def remove_tunjangan(karyawan_id):
    """Menghapus (remove) relasi tunjangan dari seorang karyawan."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT kt.id, t.nama_tunjangan
        FROM karyawan_tunjangan kt
        JOIN tunjangan t ON kt.tunjangan_id = t.id
        WHERE kt.karyawan_id = ?
    """, (karyawan_id,))
    data = cur.fetchall()

    if not data:
        print(f"Tidak ada tunjangan ter-assign untuk karyawan ID {karyawan_id}.")
        conn.close()
        return

    print(f"\n--- Tunjangan yang bisa dihapus dari Karyawan ID {karyawan_id} ---")
    for d in data:
        print(f"ID Pivot: {d[0]}. Tunjangan: {d[1]}")

    while True:
        try:
            kt_id = int(input("Masukkan ID pivot tunjangan yang ingin dihapus (0 untuk selesai): "))
            if kt_id == 0:
                break
            
            if any(d[0] == kt_id for d in data):
                cur.execute("DELETE FROM karyawan_tunjangan WHERE id = ?", (kt_id,))
                conn.commit()
                print("Tunjangan berhasil dihapus dari karyawan!")
                break
            else:
                print("ID pivot tidak ditemukan.")
        except ValueError:
            print("Input harus angka.")

    conn.close()