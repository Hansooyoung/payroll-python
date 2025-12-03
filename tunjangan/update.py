# tunjangan/update.py
from db import get_connection
# Import fungsi lihat untuk membantu proses pemilihan ID
from .read import lihat_semua_tunjangan

def update_tunjangan():
    """Mengubah data tunjangan master yang sudah ada."""
    
    # 1. Tampilkan data dan minta ID
    lihat_semua_tunjangan()
    tunjangan_id = input("\nMasukkan ID tunjangan yang ingin diubah: ").strip()
    if not tunjangan_id.isdigit():
        print("ID harus berupa angka.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nama_tunjangan, nominal_default, tipe FROM tunjangan WHERE id = ?", (tunjangan_id,))
    data = cur.fetchone()

    if not data:
        print(f"ID tunjangan {tunjangan_id} tidak ditemukan.")
        conn.close()
        return

    nama_lama, nominal_lama, tipe_lama = data
    
    print(f"\n--- Mengubah Tunjangan ID {tunjangan_id} ({nama_lama}) ---")
    
    # 2. Input data baru (kosong = data lama)
    nama_baru = input(f"Nama baru (Kosongkan: {nama_lama}): ").strip() or nama_lama

    while True:
        nominal_input = input(f"Nominal baru (Kosongkan: {nominal_lama}): ").strip()
        if not nominal_input:
            nominal_baru = nominal_lama
            break
        try:
            nominal_baru = float(nominal_input)
            if nominal_baru < 0:
                print("Nominal tidak boleh negatif!")
                continue
            break
        except ValueError:
            print("Input nominal harus angka!")
            
    while True:
        tipe_input = input(f"Tipe baru (Kosongkan: {tipe_lama}, Pilihan: tetap/persentase/per_hari): ").strip().lower()
        if not tipe_input or tipe_input == tipe_lama:
            tipe_baru = tipe_lama
            break
        if tipe_input in ['tetap', 'persentase', 'per_hari']:
            tipe_baru = tipe_input
            break
        print("Tipe tidak valid! Pilih: tetap, persentase, atau per_hari.")
    
    # 3. Eksekusi UPDATE
    cur.execute("""
        UPDATE tunjangan
        SET nama_tunjangan = ?, nominal_default = ?, tipe = ?
        WHERE id = ?
    """, (nama_baru, nominal_baru, tipe_baru, tunjangan_id))
    
    conn.commit()
    conn.close()
    print(f"\nTunjangan '{nama_baru}' berhasil diubah.")