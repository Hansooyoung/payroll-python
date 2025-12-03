# potongan/create.py
import sqlite3
from db import get_connection

def tambah_potongan():
    """Menambahkan data potongan baru ke tabel master dengan validasi lengkap."""
    conn = get_connection()
    cur = conn.cursor()

    # 1. Validasi Nama
    while True:
        nama = input("Nama potongan: ").strip()
        if nama:
            break
        print("Nama potongan tidak boleh kosong!\n")
    
    # 2. Validasi Nominal
    while True:
        try:
            # Nominal bisa berupa nilai tetap (Rp) atau persentase (%)
            nominal = float(input("Nominal default (cth: 150000 atau 2.0 untuk persentase): "))
            if nominal < 0:
                print("Nominal tidak boleh negatif!")
                continue
            break
        except ValueError:
            print("Input nominal harus angka!")
            
    # 3. Validasi Tipe (Sesuai CHECK Constraint Database)
    while True:
        tipe = input("Tipe (tetap/persentase): ").strip().lower()
        if tipe in ['tetap', 'persentase']:
            break
        print("Tipe tidak valid! Pilih: tetap atau persentase.")

    # 4. Eksekusi dan Error Handling (Database)
    try:
        cur.execute("""
            INSERT INTO potongan (nama_potongan, nominal_default, tipe)
            VALUES (?, ?, ?)
        """, (nama, nominal, tipe))
        conn.commit()
        print(f"\nPotongan '{nama}' berhasil ditambahkan!")

    except sqlite3.IntegrityError as e:
        # Menangkap error integrity, termasuk potensi CHECK constraint jika validasi di atas gagal
        print(f"\n Gagal menambahkan potongan: {e}")
        conn.rollback()

    except Exception as e:
        print(f"\n Terjadi kesalahan tak terduga: {e}")
        conn.rollback()
        
    finally:
        conn.close()