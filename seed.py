# seed.py
from datetime import datetime
from db import get_connection, setup_database

# Pastikan tabel sudah dibuat
setup_database()

conn = get_connection()
cur = conn.cursor()

print("--- Memulai Seeding Data ---")

# 1. SEED MASTER BANK
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

# 2. SEED REKENING PERUSAHAAN
cur.execute("SELECT COUNT(*) FROM rekening_perusahaan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Rekening Perusahaan...")
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
    cur.executemany("""
    INSERT INTO karyawan (nama, email, jabatan_id, status_pegawai_id, gaji_pokok, is_active)
    VALUES (?, ?, ?, ?, ?, ?)""", [
        ("Dani Pratama", "dani@example.com", 1, 3, 5000000.0, 1), # 1. Staff, Tetap, AKTIF
        ("Siti Aminah", "siti@example.com", 2, 3, 7000000.0, 1),  # 2. SPV, Tetap, AKTIF
        ("Budi Santoso", "budi@example.com", 3, 2, 12000000.0, 1), # 3. Manager, Kontrak, AKTIF
        ("Eko Purnomo", "eko@example.com", 1, 1, 3500000.0, 0)    # 4. Staff, Intern, NON-AKTIF (Resign)
    ])

# 8. SEED WALLET KARYAWAN
cur.execute("SELECT COUNT(*) FROM karyawan_wallet")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Data Rekening Karyawan (Wallet)...")
    cur.executemany("""
    INSERT INTO karyawan_wallet (karyawan_id, kode_bank, nomor_rekening, atas_nama_rekening)
    VALUES (?, ?, ?, ?)""", [
        (1, 'BCA', '111-222-3333', 'DANI PRATAMA'),
        (2, 'MANDIRI', '900-00-123456', 'SITI AMINAH'),
        (3, 'GOPAY', '08123456789', 'BUDI SANTOSO'),
        (4, 'BRI', '5555-01-000001', 'EKO PURNOMO')
    ])

# 9. SEED PIVOT TUNJANGAN
cur.execute("SELECT COUNT(*) FROM karyawan_tunjangan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Setting Tunjangan Karyawan...")
    cur.executemany("INSERT INTO karyawan_tunjangan (karyawan_id, tunjangan_id) VALUES (?, ?)", [
        (1, 1), (1, 2), (1, 3), # Dani
        (2, 1), (2, 4),         # Siti
        (3, 1), (3, 2), (3, 3), # Budi
        (4, 1)                  # Eko
    ])

# 10. SEED PIVOT POTONGAN
cur.execute("SELECT COUNT(*) FROM karyawan_potongan")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Setting Potongan Karyawan...")
    cur.executemany("INSERT INTO karyawan_potongan (karyawan_id, potongan_id) VALUES (?, ?)", [
        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), # Dani
        (2, 1), (2, 2), (2, 4),                 # Siti
        (3, 1), (3, 2), (3, 3)                  # Budi
    ])

# 11. SEED RIWAYAT GAJI
cur.execute("SELECT COUNT(*) FROM gaji")
if cur.fetchone()[0] == 0:
    print("[SEED] Mengisi Data Dummy Transaksi Gaji (Riwayat)...")
    
    # FORMAT WAKTU MANUAL (Untuk menghindari DeprecationWarning di Python 3.12+)
    waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # A. Gaji DANI (Bulan Lalu - SUDAH DITRANSFER)
    cur.execute("""
        INSERT INTO gaji (karyawan_id, periode, total_gaji, status_transfer, transfer_ref_id, waktu_transfer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (1, '2025-09-01', 5450000.0, 'SUCCESS', 'TRX-SEED-001', waktu_sekarang))
    gaji_dani_id = cur.lastrowid
    
    cur.executemany("INSERT INTO gaji_tunjangan (gaji_id, tunjangan_id, nominal) VALUES (?, ?, ?)", [
        (gaji_dani_id, 1, 400000.0), 
        (gaji_dani_id, 2, 300000.0), 
    ])
    cur.executemany("INSERT INTO gaji_potongan (gaji_id, potongan_id, nominal) VALUES (?, ?, ?)", [
        (gaji_dani_id, 1, 150000.0), 
        (gaji_dani_id, 3, 100000.0), 
    ])

    # B. Gaji EKO (Non-Aktif - Bulan Lalu)
    cur.execute("""
        INSERT INTO gaji (karyawan_id, periode, total_gaji, status_transfer, transfer_ref_id, waktu_transfer)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (4, '2025-09-01', 3700000.0, 'SUCCESS', 'TRX-SEED-002', waktu_sekarang))
    gaji_eko_id = cur.lastrowid
    
    cur.executemany("INSERT INTO gaji_tunjangan (gaji_id, tunjangan_id, nominal) VALUES (?, ?, ?)", [
        (gaji_eko_id, 1, 200000.0) 
    ])

    # C. Gaji BUDI (Bulan Ini - PENDING)
    cur.execute("""
        INSERT INTO gaji (karyawan_id, periode, total_gaji, status_transfer)
        VALUES (?, ?, ?, ?)
    """, (3, '2025-10-01', 13500000.0, 'PENDING'))
    gaji_budi_id = cur.lastrowid
    
    cur.executemany("INSERT INTO gaji_tunjangan (gaji_id, tunjangan_id, nominal) VALUES (?, ?, ?)", [
        (gaji_budi_id, 1, 400000.0), 
        (gaji_budi_id, 3, 500000.0), 
    ])
    cur.executemany("INSERT INTO gaji_potongan (gaji_id, potongan_id, nominal) VALUES (?, ?, ?)", [
        (gaji_budi_id, 1, 150000.0), 
        (gaji_budi_id, 4, 250000.0), 
    ])

conn.commit()
conn.close()

print("\n✅ Seed data BERHASIL (Tanpa Warning)!")