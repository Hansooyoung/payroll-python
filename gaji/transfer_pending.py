# gaji/transfer_pending.py
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List

# --- MODULE IMPORTS ---
from db import get_connection
from .payment_service import PaymentGateway
from .email_sender import send_payslip_email
from .pdf_generator import generate_slip_pdf

# Helper Formatter
def format_rupiah(nominal: float) -> str:
    return f"Rp{nominal:,.0f}".replace(",", ".")

def fetch_pending_salaries(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Mengambil semua gaji yang statusnya masih PENDING."""
    query = """
        SELECT 
            g.id AS gaji_id,
            g.periode,
            g.total_gaji,
            k.id AS karyawan_id,
            k.nama,
            k.email,
            k.gaji_pokok,
            k.is_active, 
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
    """Menyusun ulang data untuk PDF dari database."""
    gaji_id = row['gaji_id']
    
    tunjangan_rows = conn.execute("""
        SELECT t.nama_tunjangan, gt.nominal 
        FROM gaji_tunjangan gt 
        JOIN tunjangan t ON gt.tunjangan_id = t.id 
        WHERE gt.gaji_id = ?
    """, (gaji_id,)).fetchall()
    
    potongan_rows = conn.execute("""
        SELECT p.nama_potongan, gp.nominal 
        FROM gaji_potongan gp 
        JOIN potongan p ON gp.potongan_id = p.id 
        WHERE gp.gaji_id = ?
    """, (gaji_id,)).fetchall()

    rincian_tunjangan = {t['nama_tunjangan']: t['nominal'] for t in tunjangan_rows}
    rincian_potongan = {p['nama_potongan']: p['nominal'] for p in potongan_rows}
    total_potongan = sum(item['nominal'] for item in potongan_rows)
    
    return {
        'nama_karyawan': row['nama'],
        'nama_jabatan': row['nama_jabatan'],
        'gaji_pokok': row['gaji_pokok'], 
        'tunjangan_jabatan': row['tunjangan_jabatan'],
        'lembur_weekday': 0, 
        'lembur_weekend': 0,
        'uang_lembur': 0, 
        'rincian_tunjangan': rincian_tunjangan,
        'rincian_potongan': rincian_potongan,
        'total_potongan': total_potongan,
        'total_gaji_bersih': row['total_gaji'],
        'status_transfer': 'LUNAS (SUSULAN)'
    }

# --- PASTIKAN FUNGSI INI ADA DAN TIDAK MENJOROK (INDENTASI SALAH) ---
def process_pending_transfers():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        print("\n=== PEMROSESAN TRANSFER PENDING ===")
        
        pending_list = fetch_pending_salaries(conn)
        
        if not pending_list:
            print("✅ Tidak ada gaji yang statusnya PENDING.")
            return

        total_needed = 0
        print(f"\nDitemukan {len(pending_list)} data pending:")
        print("-" * 75)
        print(f"{'ID':<5} {'Nama':<30} {'Periode':<12} {'Bank':<5} {'Nominal':<15}")
        print("-" * 75)
        
        valid_items = []
        
        for item in pending_list:
            if not item['kode_bank'] or not item['nomor_rekening']:
                print(f"⚠️  SKIP ID {item['gaji_id']} ({item['nama']}): Data Bank tidak lengkap.")
                continue
            
            nama_display = item['nama']
            if item['is_active'] == 0:
                nama_display += " [NON-AKTIF]"

            print(f"{item['gaji_id']:<5} {nama_display:<30} {item['periode']:<12} {item['kode_bank']:<5} {format_rupiah(item['total_gaji']):<15}")
            total_needed += item['total_gaji']
            valid_items.append(item)
            
        print("-" * 75)
        print(f"TOTAL DANA DIBUTUHKAN: {format_rupiah(total_needed)}")

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

        confirm = input("\n👉 Proses transfer & kirim slip gaji? (Y/N): ").strip().upper()
        if confirm != 'Y':
            print("Dibatalkan.")
            return

        success_count = 0
        fail_count = 0
        
        print("\n--- MULAI PROSES TRANSFER & NOTIFIKASI ---")
        
        for item in valid_items:
            print(f"\n🔄 Memproses: {item['nama']} ({format_rupiah(item['total_gaji'])})...")
            desc = f"Gaji Susulan {item['nama']} {item['periode']}"
            
            res = PaymentGateway.transfer_gaji(
                bank_code=item['kode_bank'],
                account_number=item['nomor_rekening'],
                amount=item['total_gaji'],
                description=desc,
                ref_id=str(item['gaji_id'])
            )
            
            if res['success']:
                print(f"   ✅ Transfer Sukses! TRX ID: {res['trx_id']}")
                try:
                    cur.execute("SELECT saldo FROM rekening_perusahaan WHERE id = ?", (comp_acc['id'],))
                    curr_saldo = cur.fetchone()['saldo']
                    new_saldo = curr_saldo - item['total_gaji']
                    
                    cur.execute("UPDATE rekening_perusahaan SET saldo = ? WHERE id = ?", (new_saldo, comp_acc['id']))
                    cur.execute("""
                        UPDATE gaji SET status_transfer = 'SUCCESS', transfer_ref_id = ?, waktu_transfer = datetime('now')
                        WHERE id = ?
                    """, (res['trx_id'], item['gaji_id']))
                    conn.commit()
                    success_count += 1
                    
                    if item['email']:
                        print("   📄 Membuat Slip Gaji PDF...")
                        try:
                            pdf_data = reconstruct_pdf_data(conn, item)
                            pdf_path = generate_slip_pdf(pdf_data, item['periode'])
                            print(f"   📧 Mengirim email ke {item['email']}...")
                            send_payslip_email(item['email'], item['nama'], item['periode'], pdf_path)
                            print("   ✅ Email terkirim.")
                            if os.path.exists(pdf_path): os.remove(pdf_path)
                        except Exception as e:
                            print(f"   ⚠️ Gagal proses email/PDF: {e}")
                    else:
                        print("   ℹ️  Email tidak tersedia, skip pengiriman slip.")
                            
                except Exception as e:
                    conn.rollback()
                    print(f"   ❌ DB Error saat update status: {e}")
                    fail_count += 1
            else:
                print(f"   ❌ Gagal Transfer: {res['message']}")
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