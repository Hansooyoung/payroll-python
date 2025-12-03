import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List

# Load modul yang sudah ada
from db import get_connection
from .payment_service import PaymentGateway
from .email_sender import send_payslip_email
from .pdf_generator import generate_slip_pdf # Kita coba generate ulang PDF jika data cukup

# Helper Formatter
def format_rupiah(nominal: float) -> str:
    return f"Rp{nominal:,.0f}".replace(",", ".")

def fetch_pending_salaries(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Mengambil semua gaji yang statusnya masih PENDING beserta data walletnya."""
    query = """
        SELECT 
            g.id AS gaji_id,
            g.periode,
            g.total_gaji,
            k.id AS karyawan_id,
            k.nama,
            k.email,
            k.gaji_pokok, -- Diperlukan untuk re-generate PDF (estimasi)
            j.nama_jabatan,
            j.tunjangan_jabatan,
            w.kode_bank,
            w.nomor_rekening
        FROM gaji g
        JOIN karyawan k ON g.karyawan_id = k.id
        LEFT JOIN jabatan j ON k.jabatan_id = j.id
        LEFT JOIN karyawan_wallet w ON k.id = w.karyawan_id AND w.is_primary = 1
        WHERE g.status_transfer = 'PENDING'
    """
    return conn.execute(query).fetchall()

def reconstruct_pdf_data(conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
    """
    Mencoba menyusun ulang data untuk PDF dari database.
    NOTE: Karena detail lembur weekday/weekend tidak disimpan terpisah di DB (hanya total),
    kita akan menampilkannya sebagai total lembur saja di PDF reprint.
    """
    gaji_id = row['gaji_id']
    
    # Ambil detail tunjangan dari DB
    tunjangan_rows = conn.execute("""
        SELECT t.nama_tunjangan, gt.nominal 
        FROM gaji_tunjangan gt 
        JOIN tunjangan t ON gt.tunjangan_id = t.id 
        WHERE gt.gaji_id = ?
    """, (gaji_id,)).fetchall()
    
    # Ambil detail potongan dari DB
    potongan_rows = conn.execute("""
        SELECT p.nama_potongan, gp.nominal 
        FROM gaji_potongan gp 
        JOIN potongan p ON gp.potongan_id = p.id 
        WHERE gp.gaji_id = ?
    """, (gaji_id,)).fetchall()

    # Susun Dictionary
    rincian_tunjangan = {t['nama_tunjangan']: t['nominal'] for t in tunjangan_rows}
    rincian_potongan = {p['nama_potongan']: p['nominal'] for p in potongan_rows}
    
    # Hitung total potongan
    total_potongan = sum(item['nominal'] for item in potongan_rows)
    
    # Estimasi Uang Lembur (Total Gaji - Gaji Pokok - Tunjangan Jabatan - Tunjangan Lain)
    # Ini "Reverse Engineering" karena kita tidak simpan kolom lembur di tabel gaji
    total_tunjangan_lain = sum(item['nominal'] for item in tunjangan_rows)
    # Asumsi: Selisihnya adalah lembur + penyesuaian kehadiran
    # Untuk keamanan reprint, kita set lembur sebagai sisa perhitungan atau 0 jika tidak pasti
    # Agar aman, kita gunakan data seadanya untuk notifikasi
    
    return {
        'nama_karyawan': row['nama'],
        'nama_jabatan': row['nama_jabatan'],
        'gaji_pokok': row['gaji_pokok'], # Ini gaji pokok master, bukan prorata (limitasi reprint)
        'tunjangan_jabatan': row['tunjangan_jabatan'],
        
        # Di reprint, kita kosongkan detail lembur spesifik karena tidak ada di DB header
        'lembur_weekday': 0, 
        'lembur_weekend': 0,
        'uang_lembur': 0, # Atau bisa dihitung selisih jika mau kompleks
        
        'rincian_tunjangan': rincian_tunjangan,
        'rincian_potongan': rincian_potongan,
        'total_potongan': total_potongan,
        'total_gaji_bersih': row['total_gaji'],
        'status_transfer': 'LUNAS (SUSULAN)'
    }

def process_pending_transfers():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        print("\n=== PEMROSESAN TRANSFER PENDING ===")
        
        # 1. Ambil Data Pending
        pending_list = fetch_pending_salaries(conn)
        
        if not pending_list:
            print("✅ Tidak ada gaji yang statusnya PENDING.")
            return

        # 2. Tampilkan Ringkasan
        total_needed = 0
        print(f"\nDitemukan {len(pending_list)} data pending:")
        print("-" * 60)
        print(f"{'ID':<5} {'Nama':<20} {'Periode':<12} {'Bank':<5} {'Nominal':<15}")
        print("-" * 60)
        
        valid_items = []
        
        for item in pending_list:
            # Validasi Wallet
            if not item['kode_bank'] or not item['nomor_rekening']:
                print(f"⚠️  SKIP ID {item['gaji_id']} ({item['nama']}): Data Bank tidak lengkap.")
                continue
                
            print(f"{item['gaji_id']:<5} {item['nama']:<20} {item['periode']:<12} {item['kode_bank']:<5} {format_rupiah(item['total_gaji']):<15}")
            total_needed += item['total_gaji']
            valid_items.append(item)
            
        print("-" * 60)
        print(f"TOTAL DANA DIBUTUHKAN: {format_rupiah(total_needed)}")

        # 3. Cek Saldo Perusahaan
        cur.execute("SELECT id, saldo FROM rekening_perusahaan LIMIT 1")
        comp_acc = cur.fetchone()
        
        if not comp_acc:
            print("❌ Rekening perusahaan tidak ditemukan.")
            return
            
        print(f"SALDO PERUSAHAAN     : {format_rupiah(comp_acc['saldo'])}")
        
        if comp_acc['saldo'] < total_needed:
            print(f"❌ SALDO KURANG! Butuh tambahan: {format_rupiah(total_needed - comp_acc['saldo'])}")
            return

        if not valid_items:
            print("❌ Tidak ada data yang valid untuk diproses.")
            return

        # 4. Konfirmasi Eksekusi
        confirm = input("\n👉 Proses transfer untuk data di atas? (Y/N): ").strip().upper()
        if confirm != 'Y':
            print("Dibatalkan.")
            return

        # 5. Eksekusi Loop
        success_count = 0
        fail_count = 0
        
        print("\n--- MULAI PROSES TRANSFER ---")
        
        for item in valid_items:
            print(f"\n🔄 Memproses: {item['nama']} ({format_rupiah(item['total_gaji'])})...")
            
            # Panggil Payment Gateway
            # Note: ref_id menggunakan item['gaji_id'] yang sama. 
            # Karena di payment_service.py kita pakai logic "PAYROLL-GAJI-{id}", 
            # Xendit akan aman dari double transfer (Idempotency).
            desc = f"Gaji Susulan {item['nama']} {item['periode']}"
            
            res = PaymentGateway.transfer_gaji(
                bank_code=item['kode_bank'],
                account_number=item['nomor_rekening'],
                amount=item['total_gaji'],
                description=desc,
                ref_id=str(item['gaji_id'])
            )
            
            if res['success']:
                print(f"   ✅ Sukses! TRX ID: {res['trx_id']}")
                
                # Update DB (Atomic per user)
                try:
                    # Kurangi Saldo
                    # Ambil saldo terbaru dulu untuk keamanan concurrency
                    cur.execute("SELECT saldo FROM rekening_perusahaan WHERE id = ?", (comp_acc['id'],))
                    curr_saldo = cur.fetchone()['saldo']
                    new_saldo = curr_saldo - item['total_gaji']
                    
                    cur.execute("UPDATE rekening_perusahaan SET saldo = ? WHERE id = ?", (new_saldo, comp_acc['id']))
                    
                    # Update Status Gaji
                    cur.execute("""
                        UPDATE gaji 
                        SET status_transfer = 'SUCCESS', 
                            transfer_ref_id = ?, 
                            waktu_transfer = datetime('now')
                        WHERE id = ?
                    """, (res['trx_id'], item['gaji_id']))
                    
                    conn.commit()
                    success_count += 1
                    
                    # Kirim Email (Best Effort)
                    if item['email']:
                        try:
                            pdf_data = reconstruct_pdf_data(conn, item)
                            pdf_path = generate_slip_pdf(pdf_data, item['periode'])
                            send_payslip_email(item['email'], item['nama'], item['periode'], pdf_path)
                            print("   📧 Email notifikasi terkirim.")
                            if os.path.exists(pdf_path): os.remove(pdf_path)
                        except Exception as e:
                            print(f"   ⚠️ Gagal kirim email: {e}")
                            
                except Exception as e:
                    conn.rollback()
                    print(f"   ❌ DB Error saat update status: {e}")
                    fail_count += 1
            else:
                # Jika Gagal (misal Bank Error)
                print(f"   ❌ Gagal Transfer: {res['message']}")
                # Opsional: Update jadi FAILED atau biarkan PENDING untuk dicoba lagi nanti
                # cur.execute("UPDATE gaji SET status_transfer = 'FAILED' WHERE id = ?", (item['gaji_id'],))
                # conn.commit()
                fail_count += 1

        print("\n" + "="*30)
        print("LAPORAN AKHIR")
        print(f"Berhasil : {success_count}")
        print(f"Gagal    : {fail_count}")
        print("="*30)

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    process_pending_transfers()