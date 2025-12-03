from db import get_connection, setup_database

# Pastikan tabel sudah dibuat
setup_database()

conn = get_connection()
cur = conn.cursor()

print("--- Memulai Seeding Data ---")

# 1. SEED MASTER BANK (Wajib ada duluan sebelum Wallet)
cur.execute("SELECT COUNT(*) FROM master_bank")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Master Bank...")
    banks = [
        ('BCA', 'Bank Central Asia', 'BANK'),
        ('MANDIRI', 'Bank Mandiri', 'BANK'),
        ('BRI', 'Bank Rakyat Indonesia', 'BANK'),
        ('BNI', 'Bank Negara Indonesia', 'BANK'),
        ('GOPAY', 'GoPay', 'EWALLET'),
        ('OVO', 'OVO', 'EWALLET'),
        ('DANA', 'DANA', 'EWALLET'),
        ('SHOPEEPAY', 'ShopeePay', 'EWALLET')
    ]
    cur.executemany("INSERT OR IGNORE INTO master_bank (kode_bank, nama_bank, kategori) VALUES (?, ?, ?)", banks)

# 2. SEED REKENING PERUSAHAAN (Modal Awal)
cur.execute("SELECT COUNT(*) FROM rekening_perusahaan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Rekening Perusahaan...")
    # Ceritanya perusahaan punya saldo 5 Milyar di Bank Mandiri Corporate
    cur.execute("""
        INSERT INTO rekening_perusahaan (nama_bank, nomor_rekening, saldo) 
        VALUES ('MANDIRI CORP', '123-000-999-888', 5000000000)
    """)

# 3. SEED JABATAN
cur.execute("SELECT COUNT(*) FROM jabatan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Jabatan...")
    cur.executemany("INSERT INTO jabatan (nama_jabatan, tunjangan_jabatan) VALUES (?, ?)", [
        ("Staff", 200000.0),
        ("Supervisor", 500000.0),
        ("Manager", 1000000.0)
    ])

# 4. SEED STATUS PEGAWAI
cur.execute("SELECT COUNT(*) FROM status_pegawai")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Status Pegawai...")
    cur.executemany("INSERT INTO status_pegawai (nama_status) VALUES (?)", [
        ("Internship",),
        ("Kontrak",),
        ("Tetap",)
    ])

# 5. SEED TUNJANGAN
cur.execute("SELECT COUNT(*) FROM tunjangan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Master Tunjangan...")
    cur.executemany("INSERT INTO tunjangan (nama_tunjangan, nominal_default, tipe) VALUES (?, ?, ?)", [
        ("Makan", 20000.0, "per_hari"),
        ("Transport", 15000.0, "per_hari"),
        ("Tunjangan Natal", 500000.0, "tetap"),
        ("Bonus Kinerja", 5.0, "persentase"),
    ])

# 6. SEED POTONGAN
cur.execute("SELECT COUNT(*) FROM potongan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Master Potongan...")
    cur.executemany("INSERT INTO potongan (nama_potongan, nominal_default, tipe) VALUES (?, ?, ?)", [
        ("BPJS Kesehatan", 150000.0, "tetap"),
        ("BPJS Ketenagakerjaan", 2.0, "persentase"),
        ("Potongan Koperasi", 100000.0, "tetap"),
        ("Pajak PPh 21", 1.5, "persentase"),
        ("Potongan Hutang", 1000000.0, "tetap"),
    ])

# 7. SEED KARYAWAN
cur.execute("SELECT COUNT(*) FROM karyawan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Data Karyawan...")
    # ID akan otomatis: Dani=1, Siti=2, Budi=3
    cur.executemany("""
    INSERT INTO karyawan (nama, email, jabatan_id, status_pegawai_id, gaji_pokok)
    VALUES (?, ?, ?, ?, ?)""", [
        ("Dani Pratama", "satehajironi@gmail.com", 1, 3, 5000000.0), # Staff, Tetap
        ("Siti Aminah", "aditiasakti01@gmail.com", 2, 3, 7000000.0),  # Supervisor, Tetap
        ("Budi Santoso", "gleenradarsreal@gmail.com", 3, 2, 12000000.0) # Manager, Kontrak
    ])

# 8. SEED WALLET KARYAWAN (Baru!)
cur.execute("SELECT COUNT(*) FROM karyawan_wallet")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Data Rekening Karyawan (Wallet)...")
    cur.executemany("""
    INSERT INTO karyawan_wallet (karyawan_id, kode_bank, nomor_rekening, atas_nama_rekening)
    VALUES (?, ?, ?, ?)""", [
        (1, 'BCA', '111-222-3333', 'DANI PRATAMA'),       # Dani pakai BCA
        (2, 'MANDIRI', '900-00-123456', 'SITI AMINAH'),   # Siti pakai Mandiri
        (3, 'GOPAY', '08123456789', 'BUDI SANTOSO')       # Budi gajinya masuk GoPay
    ])

# 9. SEED PIVOT TUNJANGAN
cur.execute("SELECT COUNT(*) FROM karyawan_tunjangan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Setting Tunjangan Karyawan...")
    cur.executemany("INSERT INTO karyawan_tunjangan (karyawan_id, tunjangan_id) VALUES (?, ?)", [
        (1, 1), (1, 2), (1, 3), # Dani: Makan, Transport, Natal
        (2, 1), (2, 4),         # Siti: Makan, Bonus Kinerja
        (3, 1), (3, 2), (3, 3)  # Budi: Makan, Transport, Natal
    ])

# 10. SEED PIVOT POTONGAN
cur.execute("SELECT COUNT(*) FROM karyawan_potongan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Setting Potongan Karyawan...")
    cur.executemany("INSERT INTO karyawan_potongan (karyawan_id, potongan_id) VALUES (?, ?)", [
        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), # Dani kena banyak potongan (termasuk hutang)
        (2, 1), (2, 2), (2, 4),                 # Siti standar
        (3, 1), (3, 2), (3, 3)                  # Budi
    ])

conn.commit()
conn.close()

print("\n✅ Seed data dummy berhasil diinsert lengkap dengan Wallet & Saldo Perusahaan!")