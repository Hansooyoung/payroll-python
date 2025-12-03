# tunjangan/read.py
from db import get_connection

def lihat_semua_tunjangan():
    """Menampilkan semua data tunjangan master."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nama_tunjangan, nominal_default, tipe FROM tunjangan")
    data = cur.fetchall()
    conn.close()

    if not data:
        print("\n=== DAFTAR TUNJANGAN ===\nTidak ada data tunjangan master.")
        return

    print("\n=== DAFTAR TUNJANGAN MASTER ===")
    t_header = f"{'ID':<4} {'Nama Tunjangan':<25} {'Nominal Default':>18} {'Tipe':<10}"
    separator = "-" * len(t_header)
    print(separator)
    print(t_header)
    print(separator)
    for t in data:
        # Menampilkan format nominal sesuai tipe
        if t[3] == 'persentase':
            nominal_str = f"{t[2]}%"
        elif t[3] == 'per_hari':
            nominal_str = f"Rp{t[2]:,.0f} /hari"
        else:
            nominal_str = f"Rp{t[2]:,.0f}"

        print(f"{t[0]:<4} {t[1]:<25} {nominal_str:>18} {t[3]:<10}")
    print(separator)
    return data # Mengembalikan data untuk digunakan di fungsi lain