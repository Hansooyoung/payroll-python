import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

SENDER_EMAIL = "62-85117584651_191@zohomail.com" 
SENDER_PASSWORD = "wHaZTMRy42Xu" 
SMTP_SERVER = "smtp.zoho.com" 
SMTP_PORT = 587 # Port TLS standar

def send_payslip_email(recipient_email, recipient_name, periode, pdf_file_path):
    
    if not recipient_email or not os.path.exists(pdf_file_path):
        print("[EMAIL FAILED] Email atau file PDF tidak valid.")
        return False
        
    try:
        # 1. Setup Email Message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = f"Slip Gaji {recipient_name} Periode {periode}"

        body = f"""
Yth. Bapak/Ibu {recipient_name},

Terlampir adalah slip gaji Anda untuk periode {periode} dalam format PDF.

Harap simpan dokumen ini dengan aman.
Jika Anda memiliki pertanyaan, silakan hubungi HRD.

Hormat kami,
Tim Administrasi Gaji
"""
        msg.attach(MIMEText(body, 'plain'))
        
        # 2. Attach PDF File
        with open(pdf_file_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= SlipGaji_{recipient_name.replace(' ', '_')}_{periode}.pdf",
        )
        msg.attach(part)
        
        # 3. Send Email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, recipient_email, text)
        server.quit()

        return True

    except Exception as e:
        print(f"\n[ERROR] Gagal mengirim email ke {recipient_email}: {e}")
        print("Pastikan SENDER_PASSWORD (App Password Zoho) sudah benar.")
        return False