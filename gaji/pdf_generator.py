import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors

def format_rupiah(value):
    """Helper untuk memformat angka ke format Rupiah (Rp1.000.000)."""
    return f"Rp{value:,.0f}".replace(",", ".")

def draw_header_section(c, y, slip_data, periode):
    """Menggambar Kop Perusahaan dan Data Karyawan."""
    # --- LOGO & KOP ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "PT. OTOMOTIF MAJU JAYA") # Ganti nama PT sesuai selera
    
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, y - 0.5 * cm, "Kawasan Industri Cikarang, Jawa Barat")
    c.drawString(2 * cm, y - 0.9 * cm, "Telp: (021) 888-9999 | Email: payroll@otomotif.com")
    
    # Label "SLIP GAJI" di kanan atas
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(19 * cm, y, "SLIP GAJI")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(19 * cm, y - 0.6 * cm, f"PERIODE: {periode.upper()}")
    
    # Garis pemisah header
    y -= 1.5 * cm
    c.setLineWidth(2)
    c.line(2 * cm, y, 19 * cm, y)
    
    # --- DATA KARYAWAN (Dalam Kotak) ---
    y -= 0.5 * cm
    c.setLineWidth(1)
    
    # Kolom Kiri
    c.setFont("Helvetica-Bold", 9)
    c.drawString(2.2 * cm, y - 0.5 * cm, "Nama Karyawan")
    c.drawString(5 * cm, y - 0.5 * cm, f": {slip_data['nama_karyawan']}")
    
    c.drawString(2.2 * cm, y - 1.0 * cm, "ID Karyawan")
    c.drawString(5 * cm, y - 1.0 * cm, f": {slip_data.get('id_karyawan', '-')}")

    # Kolom Kanan
    c.drawString(12 * cm, y - 0.5 * cm, "Jabatan")
    c.drawString(14.5 * cm, y - 0.5 * cm, f": {slip_data['nama_jabatan']}")
    
    c.drawString(12 * cm, y - 1.0 * cm, "Status")
    c.drawString(14.5 * cm, y - 1.0 * cm, ": Karyawan Tetap")

    # Garis bawah kotak info
    y -= 1.5 * cm
    c.setStrokeColor(colors.lightgrey)
    c.line(2 * cm, y, 19 * cm, y)
    c.setStrokeColor(colors.black)
    
    return y - 0.5 * cm

def generate_slip_pdf(slip_data, periode):
    """Menghasilkan slip gaji dengan layout korporat profesional."""
    
    filename = f"SlipGaji_{slip_data['nama_karyawan'].replace(' ', '_')}_{periode}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # Posisi awal (Y)
    y_pos = height - 2 * cm
    
    # 1. Gambar Header & Info
    y_pos = draw_header_section(c, y_pos, slip_data, periode)
    
    # 2. Setup Kolom (Kiri: Pendapatan, Kanan: Potongan)
    col_left_x = 2 * cm
    col_right_x = 11 * cm
    col_width = 8.5 * cm
    
    # Judul Kolom (Background Abu-abu)
    c.setFillColor(colors.lightgrey)
    c.rect(col_left_x, y_pos - 0.8 * cm, col_width, 0.8 * cm, fill=1, stroke=0)
    c.rect(col_right_x, y_pos - 0.8 * cm, col_width, 0.8 * cm, fill=1, stroke=0)
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col_left_x + 0.2 * cm, y_pos - 0.6 * cm, "A. PENERIMAAN (EARNINGS)")
    c.drawString(col_right_x + 0.2 * cm, y_pos - 0.6 * cm, "B. POTONGAN (DEDUCTIONS)")
    
    y_start_items = y_pos - 1.5 * cm
    y_curr_left = y_start_items
    y_curr_right = y_start_items
    line_height = 0.5 * cm
    
    c.setFont("Helvetica", 9)
    
    # --- ISI KOLOM KIRI (PENDAPATAN) ---
    # Gaji Pokok
    c.drawString(col_left_x, y_curr_left, "Gaji Pokok")
    c.drawRightString(col_left_x + col_width - 0.5 * cm, y_curr_left, format_rupiah(slip_data['gaji_pokok']))
    y_curr_left -= line_height
    
    # Tunjangan Jabatan
    c.drawString(col_left_x, y_curr_left, "Tunjangan Jabatan")
    c.drawRightString(col_left_x + col_width - 0.5 * cm, y_curr_left, format_rupiah(slip_data['tunjangan_jabatan']))
    y_curr_left -= line_height
    
    # --- DETAIL LEMBUR (UPDATE DISINI) ---
    # Kita cek apakah ada detail lembur weekday/weekend
    lembur_wd = slip_data.get('lembur_weekday', 0)
    lembur_we = slip_data.get('lembur_weekend', 0)
    total_lembur = slip_data.get('uang_lembur', 0)

    # Jika ada detail Weekday
    if lembur_wd > 0:
        c.drawString(col_left_x, y_curr_left, "Lembur (Hari Kerja)")
        c.drawRightString(col_left_x + col_width - 0.5 * cm, y_curr_left, format_rupiah(lembur_wd))
        y_curr_left -= line_height

    # Jika ada detail Weekend
    if lembur_we > 0:
        c.drawString(col_left_x, y_curr_left, "Lembur (Hari Libur/Minggu)")
        c.drawRightString(col_left_x + col_width - 0.5 * cm, y_curr_left, format_rupiah(lembur_we))
        y_curr_left -= line_height

    # Fallback: Jika tidak ada detail tapi ada total (untuk data lama)
    if lembur_wd == 0 and lembur_we == 0 and total_lembur > 0:
        c.drawString(col_left_x, y_curr_left, "Uang Lembur (Total)")
        c.drawRightString(col_left_x + col_width - 0.5 * cm, y_curr_left, format_rupiah(total_lembur))
        y_curr_left -= line_height

    # Tunjangan Lain
    for nama, nominal in slip_data.get('rincian_tunjangan', {}).items():
        if nominal > 0:
            c.drawString(col_left_x, y_curr_left, f"Tunj. {nama}")
            c.drawRightString(col_left_x + col_width - 0.5 * cm, y_curr_left, format_rupiah(nominal))
            y_curr_left -= line_height
            
    # --- ISI KOLOM KANAN (POTONGAN) ---
    for nama, nominal in slip_data.get('rincian_potongan', {}).items():
        if nominal > 0:
            c.drawString(col_right_x + 0.2*cm, y_curr_right, f"Pot. {nama}")
            c.drawRightString(col_right_x + col_width - 0.2*cm, y_curr_right, format_rupiah(nominal))
            y_curr_right -= line_height

    # Tentukan Y terendah untuk garis penutup
    y_bottom = min(y_curr_left, y_curr_right) - 0.5 * cm
    
    # --- TOTAL ---
    # Garis pemisah item dan total
    c.setLineWidth(1)
    c.setStrokeColor(colors.grey)
    c.line(col_left_x, y_bottom + 0.2*cm, 19 * cm, y_bottom + 0.2*cm)
    
    y_total = y_bottom - 0.5 * cm
    c.setFont("Helvetica-Bold", 9)
    
    # Total Kotor (Hitung ulang di PDF untuk display)
    total_tunjangan_lain = sum(slip_data.get('rincian_tunjangan', {}).values())
    total_kotor = slip_data['gaji_pokok'] + slip_data['tunjangan_jabatan'] + total_lembur + total_tunjangan_lain
    
    c.drawString(col_left_x, y_total, "Total Penerimaan Kotor")
    c.drawRightString(col_left_x + col_width - 0.5 * cm, y_total, format_rupiah(total_kotor))
    
    # Total Potongan
    total_potongan = slip_data.get('total_potongan', sum(slip_data.get('rincian_potongan', {}).values()))
    c.drawString(col_right_x + 0.2*cm, y_total, "Total Potongan")
    c.drawRightString(col_right_x + col_width - 0.2*cm, y_total, format_rupiah(total_potongan))
    
    # --- TAKE HOME PAY (BOX BESAR) ---
    y_thp = y_total - 1.5 * cm
    
    # Box Background
    c.setFillColor(colors.whitesmoke)
    c.rect(2 * cm, y_thp - 0.5*cm, 17 * cm, 1.2 * cm, fill=1, stroke=1)
    c.setFillColor(colors.black)
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2.5 * cm, y_thp, "GAJI BERSIH (TAKE HOME PAY)")
    
    c.setFont("Helvetica-Bold", 16)
    net_salary = slip_data.get('total_gaji_bersih', total_kotor - total_potongan)
    
    # Logic Hutang/Negatif
    if 'tunggakan' in slip_data and slip_data['tunggakan'] > 0:
        c.setFillColor(colors.red)
        c.drawRightString(18.5 * cm, y_thp, "Rp 0")
        c.setFont("Helvetica", 10)
        c.drawRightString(18.5 * cm, y_thp - 1.2 * cm, f"(*Sisa Utang: {format_rupiah(slip_data['tunggakan'])})")
    else:
        c.drawRightString(18.5 * cm, y_thp, format_rupiah(net_salary))

    # --- FOOTER & TANDA TANGAN ---
    y_sign = y_thp - 3 * cm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    
    # Kiri: Penerima
    c.drawString(3 * cm, y_sign, "Diterima Oleh,")
    c.line(3 * cm, y_sign - 2 * cm, 7 * cm, y_sign - 2 * cm)
    c.drawString(3 * cm, y_sign - 2.4 * cm, f"({slip_data['nama_karyawan']})")
    
    # Kanan: HRD/Finance
    c.drawString(13 * cm, y_sign, f"Jakarta, {periode}") # Asumsi lokasi
    c.drawString(13 * cm, y_sign - 0.5 * cm, "Finance / HRD,")
    c.line(13 * cm, y_sign - 2 * cm, 17 * cm, y_sign - 2 * cm)
    c.drawString(13 * cm, y_sign - 2.4 * cm, "(_________________)")
    
    # Status Transfer (NEW FEATURE)
    status_tf = slip_data.get('status_transfer', '')
    if status_tf:
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(width / 2, y_sign - 3.5 * cm, f"Status Pembayaran: {status_tf}")

    # Disclaimer Bawah
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(width / 2, 2 * cm, "Dokumen ini dibuat secara otomatis oleh sistem dan valid tanpa tanda tangan basah.")
    
    c.save()
    return filename