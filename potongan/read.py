# potongan/read.py
from db import get_connection

def lihat_semua_potongan():
    """Menampilkan semua data potongan master."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nama_potongan, nominal_default, tipe FROM potongan")
    data = cur.fetchall()
    conn.close()

    if not data:
        print("\n=== DAFTAR POTONGAN ===\nTidak ada data potongan master.")
        return

    print("\n=== DAFTAR POTONGAN MASTER ===")
    p_header = f"{'ID':<4} {'Nama Potongan':<25} {'Nominal Default':>18} {'Tipe':<10}"
    separator = "-" * len(p_header)
    print(separator)
    print(p_header)
    print(separator)
    for p in data:
        # Menampilkan format nominal sesuai tipe
        nominal_str = f"Rp{p[2]:,.0f}" if p[3] == 'tetap' else f"{p[2]}%"

        print(f"{p[0]:<4} {p[1]:<25} {nominal_str:>18} {p[3]:<10}")
    print(separator)
    return data # Mengembalikan data untuk digunakan di fungsi lain