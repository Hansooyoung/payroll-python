import sqlite3

DB_NAME = "gaji.db"

def get_connection():
    """Koneksi ke SQLite dengan Foreign Key aktif"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = 1") 
    return conn

def setup_database():
    """Hanya membuat struktur tabel (Schema)"""
    conn = get_connection()
    cur = conn.cursor()

    # --- 1. Master Data ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS master_bank (
        kode_bank TEXT PRIMARY KEY, 
        nama_bank TEXT NOT NULL,
        kategori TEXT DEFAULT 'BANK' CHECK(kategori IN ('BANK', 'EWALLET'))
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rekening_perusahaan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_bank TEXT NOT NULL,
        nomor_rekening TEXT NOT NULL,
        saldo REAL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jabatan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_jabatan TEXT NOT NULL,
        tunjangan_jabatan REAL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS status_pegawai (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_status TEXT NOT NULL
    )
    """)

    # --- 2. Karyawan & Wallet ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS karyawan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT NOT NULL,
        email TEXT,
        jabatan_id INTEGER,
        status_pegawai_id INTEGER,
        gaji_pokok REAL DEFAULT 0,
        FOREIGN KEY (jabatan_id) REFERENCES jabatan(id),
        FOREIGN KEY (status_pegawai_id) REFERENCES status_pegawai(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS karyawan_wallet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL,
        kode_bank TEXT NOT NULL,
        nomor_rekening TEXT NOT NULL,
        atas_nama_rekening TEXT NOT NULL,
        is_primary INTEGER DEFAULT 1, 
        FOREIGN KEY (karyawan_id) REFERENCES karyawan(id),
        FOREIGN KEY (kode_bank) REFERENCES master_bank(kode_bank)
    )
    """)

    # --- 3. Komponen Gaji ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tunjangan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_tunjangan TEXT NOT NULL,
        nominal_default REAL,
        tipe TEXT DEFAULT 'tetap',
        CHECK(tipe IN ('tetap', 'persentase', 'per_hari'))
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS potongan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_potongan TEXT NOT NULL,
        nominal_default REAL,
        tipe TEXT DEFAULT 'tetap',
        CHECK(tipe IN ('tetap', 'persentase'))
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS karyawan_tunjangan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL,
        tunjangan_id INTEGER NOT NULL,
        FOREIGN KEY (karyawan_id) REFERENCES karyawan(id),
        FOREIGN KEY (tunjangan_id) REFERENCES tunjangan(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS karyawan_potongan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL,
        potongan_id INTEGER NOT NULL,
        FOREIGN KEY (karyawan_id) REFERENCES karyawan(id),
        FOREIGN KEY (potongan_id) REFERENCES potongan(id)
    )
    """)

    # --- 4. Transaksi Penggajian ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gaji (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        karyawan_id INTEGER NOT NULL,
        periode TEXT NOT NULL,
        total_gaji REAL NOT NULL,
        status_transfer TEXT DEFAULT 'PENDING',
        transfer_ref_id TEXT,
        waktu_transfer TIMESTAMP,
        CHECK(status_transfer IN ('PENDING', 'SUCCESS', 'FAILED')),
        FOREIGN KEY (karyawan_id) REFERENCES karyawan(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gaji_tunjangan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gaji_id INTEGER NOT NULL,
        tunjangan_id INTEGER NOT NULL,
        nominal REAL NOT NULL,
        FOREIGN KEY (gaji_id) REFERENCES gaji(id),
        FOREIGN KEY (tunjangan_id) REFERENCES tunjangan(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS gaji_potongan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gaji_id INTEGER NOT NULL,
        potongan_id INTEGER NOT NULL,
        nominal REAL NOT NULL,
        FOREIGN KEY (gaji_id) REFERENCES gaji(id),
        FOREIGN KEY (potongan_id) REFERENCES potongan(id)
    )
    """)

    conn.commit()
    conn.close()
    print("[DB] Setup database selesai.")

if __name__ == "__main__":
    setup_database()