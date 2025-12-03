# tunjangan/create.py
from db import get_connection

def tambah_tunjangan():
    """Menambahkan data tunjangan baru ke tabel master dengan validasi lengkap."""
    conn = get_connection()
    cur = conn.cursor()

    # 1. Validasi Nama
    while True:
        nama = input("Nama tunjangan: ").strip()
        if nama:
            break
        print("Nama tunjangan tidak boleh kosong!\n")
    
    # 2. Validasi Nominal
    while True:
        try:
            # Nominal bisa berupa nilai tetap (Rp) atau persentase (%)
            nominal = float(input("Nominal default (contoh: 50000 atau 2.5 untuk persentase): "))
            if nominal < 0:
                print("Nominal tidak boleh negatif!")
                continue
            break
        except ValueError:
            print("Input nominal harus angka!")
            
    # 3. Validasi Tipe (Sesuai CHECK Constraint Database)
    while True:
        tipe = input("Tipe (tetap/persentase/per_hari): ").strip().lower()
        if tipe in ['tetap', 'persentase', 'per_hari']:
            break
        print("Tipe tidak valid! Pilih: tetap, persentase, atau per_hari.")

    # 4. Eksekusi dan Error Handling (Database)
    try:
        cur.execute("""
            INSERT INTO tunjangan (nama_tunjangan, nominal_default, tipe)
            VALUES (?, ?, ?)
        """, (nama, nominal, tipe))
        conn.commit()
        print(f"\nTunjangan '{nama}' berhasil ditambahkan!")

    except conn.IntegrityError as e:
        # Error handling untuk kemungkinan integrity check (mis. jika nama dibuat UNIQUE)
        # Atau jika ada error lain dari database (meskipun CHECK constraint sudah ditangani oleh validasi di atas)
        print(f"\nGagal menambahkan tunjangan: {e}")
        conn.rollback()

    except Exception as e:
        print(f"\nTerjadi kesalahan tak terduga: {e}")
        conn.rollback()
        
    finally:
        conn.close()