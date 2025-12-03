import os
import requests 
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load API Key
load_dotenv()
API_KEY = os.getenv("XENDIT_SECRET_KEY")

if not API_KEY:
    print("⚠️  WARNING: XENDIT_SECRET_KEY tidak ditemukan di .env")

class PaymentGateway:
    """
    Class khusus untuk menangani request ke Xendit via HTTP Request.
    """
    
    @staticmethod
    def transfer_gaji(bank_code: str, account_number: str, amount: float, description: str, ref_id: str):
        """
        Mengirim permintaan transfer (Disbursement).
        """
        # 1. Pastikan amount bulat (Integer)
        amount_int = int(amount)
        
        # Cek Minimum Transfer Xendit (Biasanya Rp 10.000)
        if amount_int < 10000:
            return {"success": False, "trx_id": None, "message": "Nominal di bawah batas minimum transfer (Rp10.000)"}

        print(f"\n[XENDIT] 📡 Menghubungkan ke API... (Nominal: Rp{amount_int:,.0f})")

        url = "https://api.xendit.co/disbursements"
        
        # --- PERBAIKAN KEAMANAN (IDEMPOTENCY) ---
        # Hapus UUID acak. Gunakan ID Gaji dari database agar unik & konsisten.
        # Jika script dijalankan 2x untuk gaji yang sama, Xendit akan menolak yang kedua.
        external_id = f"PAYROLL-GAJI-{ref_id}"

        payload = {
            "external_id": str(external_id),
            "amount": amount_int,                  
            "bank_code": str(bank_code).upper(),   
            "account_holder_name": "Karyawan", 
            "account_number": str(account_number), 
            "description": str(description)[:250]  
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                auth=HTTPBasicAuth(API_KEY, '') 
            )

            response_data = response.json()

            # Status 200 (OK) atau 201 (Created)
            if response.status_code in [200, 201]:
                status_trx = response_data.get('status', 'PENDING')
                trx_id = response_data.get('id')
                return {
                    "success": True,
                    "trx_id": trx_id,
                    "message": f"Permintaan berhasil (Status: {status_trx})"
                }
            else:
                # Handle Error Spesifik
                error_code = response_data.get('error_code', 'UNKNOWN')
                error_msg = response_data.get('message', 'Terjadi kesalahan')

                # Jika error karena DUPLICATE, kita anggap sukses saja (karena sudah pernah terkirim)
                if error_code == 'DUPLICATE_EXTERNAL_ID':
                     return {
                        "success": False, # Tetap false agar tidak potong saldo 2x di DB
                        "trx_id": None,
                        "message": "⚠️ Transaksi ini sudah pernah sukses sebelumnya (Duplicate)."
                    }

                print(f"❌ Response Xendit: {response_data}")
                return {
                    "success": False,
                    "trx_id": None,
                    "message": f"{error_code}: {error_msg}"
                }

        except Exception as e:
            return {"success": False, "trx_id": None, "message": str(e)}

    # --- FITUR TOP UP & CEK SALDO (TIDAK BERUBAH) ---
    @staticmethod
    def create_topup_invoice(amount: float):
        url = "https://api.xendit.co/v2/invoices"
        # Untuk Topup, UUID boleh dipakai karena kita ingin invoice baru terus
        import uuid 
        external_id = f"TOPUP-{uuid.uuid4().hex[:8]}" 
        payload = {
            "external_id": external_id,
            "amount": int(amount),
            "description": "Top Up Saldo Payroll App",
            "invoice_duration": 172800,
            "currency": "IDR"
        }
        try:
            resp = requests.post(url, json=payload, auth=HTTPBasicAuth(API_KEY, ''))
            data = resp.json()
            if resp.status_code == 200:
                return {"success": True, "invoice_url": data['invoice_url'], "status": data['status'], "id": data['id']}
            return {"success": False, "message": data.get('message', 'Error')}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    def get_real_balance():
        url = "https://api.xendit.co/balance?account_type=CASH"
        try:
            resp = requests.get(url, auth=HTTPBasicAuth(API_KEY, ''))
            data = resp.json()
            if resp.status_code == 200:
                return data['balance']
            return 0
        except:
            return 0