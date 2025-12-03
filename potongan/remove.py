# potongan/remove.py
from db import get_connection

def remove_potongan(karyawan_id):
    """Menghapus (remove) relasi potongan dari seorang karyawan."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT kp.id, p.nama_potongan
        FROM karyawan_potongan kp
        JOIN potongan p ON kp.potongan_id = p.id
        WHERE kp.karyawan_id = ?
    """, (karyawan_id,))
    data = cur.fetchall()

    if not data:
        print(f"Tidak ada potongan ter-assign untuk karyawan ID {karyawan_id}.")
        conn.close()
        return

    print(f"\n--- Potongan yang bisa dihapus dari Karyawan ID {karyawan_id} ---")
    for d in data:
        print(f"ID Pivot: {d[0]}. Potongan: {d[1]}")

    while True:
        try:
            kp_id = int(input("Masukkan ID pivot potongan yang ingin dihapus (0 untuk selesai): "))
            if kp_id == 0:
                break
            
            if any(d[0] == kp_id for d in data):
                cur.execute("DELETE FROM karyawan_potongan WHERE id = ?", (kp_id,))
                conn.commit()
                print("Potongan berhasil dihapus dari karyawan!")
                break
            else:
                print("ID pivot tidak ditemukan.")
        except ValueError:
            print("Input harus angka.")

    conn.close()