import os
import sys
import subprocess
from typing import Callable

# --- IMPOR MODUL LOKAL ---
from db import setup_database, DB_NAME
from karyawan import (
    filter_karyawan, lihat_tunjangan_potongan, tambah_karyawan, 
    update_karyawan, delete_karyawan
)
from tunjangan import (
    lihat_semua_tunjangan, tambah_tunjangan, update_tunjangan, delete_tunjangan,
    assign_tunjangan, remove_tunjangan
)
from potongan import (
    lihat_semua_potongan, tambah_potongan, update_potongan, delete_potongan,
    assign_potongan, remove_potongan
)
# Update Import Gaji (Tambah process_pending_transfers)
from gaji import create_gaji, lihat_riwayat_gaji, process_pending_transfers

# --- UTILITIES / FUNGSI BANTUAN ---

def clear_screen():
    """Membersihkan layar terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_valid_int(prompt: str) -> int:
    """Meminta input angka, loop terus sampai valid."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("[!] Input harus berupa angka. Silakan coba lagi.")

def pause():
    input("\nTekan Enter untuk melanjutkan...")

def handle_assignment_menu(title: str, func_assign: Callable, func_remove: Callable):
    """
    Helper untuk menangani logika Assign/Remove agar tidak duplikasi kode.
    """
    print(f"\n--- {title} ---")
    karyawan_id = get_valid_int("Masukkan ID Karyawan: ")
    
    print("1. Tetapkan (ASSIGN)")
    print("2. Hapus (REMOVE)")
    aksi = input("Pilih aksi (1/2): ").strip()
    
    if aksi == "1":
        func_assign(karyawan_id)
    elif aksi == "2":
        func_remove(karyawan_id)
    else:
        print("[!] Pilihan tidak valid.")

def run_seeder():
    """Menjalankan script seed.py untuk mengisi data awal."""
    print("[INFO] Menjalankan seeding data (seed.py)...")
    if os.path.exists("seed.py"):
        try:
            # Menjalankan seed.py sebagai subprocess agar bersih
            subprocess.run([sys.executable, "seed.py"], check=True)
            print("[SUCCESS] Seeding selesai.")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Gagal menjalankan seed.py: {e}")
    else:
        print("[WARN] File 'seed.py' tidak ditemukan. Database kosong.")

def initialize_system():
    """Cek apakah database ada saat startup. Jika tidak, buat dan seed."""
    if not os.path.exists(DB_NAME):
        print("\n[INIT] Database belum ditemukan. Memulai inisialisasi awal...")
        setup_database()
        run_seeder()
        print("[INIT] Sistem siap digunakan!\n")
        pause()

def reset_application_database():
    """Menghapus database lama, membuat ulang, dan mengisi data dummy secara opsional."""
    print("\n⚠️  PERINGATAN KERAS ⚠️")
    print("Anda akan menghapus SELURUH DATA (Karyawan, Gaji, History, dll).")
    
    konfirmasi = input("Ketik 'RESET' untuk melanjutkan: ").strip()
    if konfirmasi != 'RESET':
        print("Reset dibatalkan.")
        return

    # 1. Hapus File DB
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"\n[INFO] Database lama '{DB_NAME}' berhasil dihapus.")
        except PermissionError:
            print(f"[ERROR] Database sedang digunakan oleh proses lain. Tutup aplikasi lain dulu.")
            return
        except Exception as e:
            print(f"[ERROR] Gagal menghapus database: {e}")
            return

    # 2. Setup Ulang Schema
    print("[INFO] Membuat struktur tabel baru...")
    setup_database()

    # 3. Opsi Isi Data Dummy (UPDATE DISINI)
    print("-" * 30)
    print("Database berhasil dikosongkan.")
    tanya_seed = input("Apakah Anda ingin mengisi database dengan Data Dummy (Contoh)? (y/n): ").strip().lower()
    
    if tanya_seed == 'y':
        run_seeder()
        print("\n[SUCCESS] Reset Database Berhasil! Aplikasi kembali baru dengan data dummy.")
    else:
        print("\n[SUCCESS] Reset Database Berhasil! Database sekarang bersih.")
    
    pause()

def menu_karyawan():
    while True:
        print("\n" + "="*30)
        print("   MANAJEMEN KARYAWAN")
        print("="*30)
        print("1. Lihat & Filter Karyawan")
        print("2. Tambah Karyawan Baru")
        print("3. Ubah Data Karyawan")
        print("4. Hapus Karyawan")
        print("5. Lihat Rincian Komponen Gaji")
        print("6. Kelola Tunjangan Karyawan")
        print("7. Kelola Potongan Karyawan")
        print("0. Kembali")
        
        pilih = input(">>> Pilih menu: ").strip()
        
        if pilih == "1": filter_karyawan()
        elif pilih == "2": tambah_karyawan()
        elif pilih == "3": update_karyawan()
        elif pilih == "4": delete_karyawan()
        elif pilih == "5": lihat_tunjangan_potongan()
        elif pilih == "6": 
            handle_assignment_menu("KELOLA TUNJANGAN", assign_tunjangan, remove_tunjangan)
        elif pilih == "7": 
            handle_assignment_menu("KELOLA POTONGAN", assign_potongan, remove_potongan)
        elif pilih == "0": break
        else: print("[!] Pilihan tidak valid.")

def menu_master(judul: str, func_read, func_create, func_update, func_delete):
    while True:
        print("\n" + "="*30)
        print(f"   MANAJEMEN MASTER {judul}")
        print("="*30)
        print("1. Lihat Semua Data")
        print("2. Tambah Data Baru")
        print("3. Ubah Data")
        print("4. Hapus Data")
        print("0. Kembali")
        
        pilih = input(">>> Pilih menu: ").strip()

        if pilih == "1": func_read()
        elif pilih == "2": func_create()
        elif pilih == "3": func_update()
        elif pilih == "4": func_delete()
        elif pilih == "0": break
        else: print("[!] Pilihan tidak valid.")

def main_menu():
    # Cek Startup: Apakah DB sudah ada? Kalau belum, buat & seed.
    initialize_system()
    
    while True:    
        print(f"{'\n=== MENU UTAMA APLIKASI GAJI ===':^40}") 
        print("1. Manajemen Karyawan")
        print("2. Master Data Tunjangan")
        print("3. Master Data Potongan")
        print("-" * 30)
        print("4. Hitung Gaji (Payroll Run)")
        print("5. Proses Transfer Pending (Retry Transfer)")
        print("6. Laporan Riwayat Gaji")
        print("-" * 30)
        print("9. Reset Database (Danger Zone)")
        print("0. Keluar")
        
        pilih = input(">>> Pilih menu utama: ").strip()

        if pilih == "1":
            menu_karyawan()
        elif pilih == "2":
            menu_master("TUNJANGAN", lihat_semua_tunjangan, tambah_tunjangan, update_tunjangan, delete_tunjangan)
        elif pilih == "3":
            menu_master("POTONGAN", lihat_semua_potongan, tambah_potongan, update_potongan, delete_potongan)
        elif pilih == "4":
            create_gaji()
            pause()
        elif pilih == "5":
            process_pending_transfers() # Fitur Baru
            pause()
        elif pilih == "6":
            lihat_riwayat_gaji()
            pause()
        elif pilih == "9":
            reset_application_database()
        elif pilih == "0":
            print("\nTerima kasih. Sampai jumpa! 👋")
            break
        else:
            print("[!] Pilihan tidak valid.")

# --- ENTRY POINT ---
if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n[INFO] Aplikasi dihentikan pengguna.")
        sys.exit(0)