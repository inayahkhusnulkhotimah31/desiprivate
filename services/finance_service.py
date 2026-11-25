"""
DESI PRIVAT - Finance Service
Layanan Pengelolaan Keuangan, Tagihan Periode Siswa, Pembayaran Cicilan,
Kuitansi Transaksi, dan Rekapitulasi Honor Mentor Berdasarkan Sesi Terlaksana.
"""
from datetime import datetime, date
from services.database_service import query_db, execute_db

def generate_bill_code(student_id, period_number):
    """Menghasilkan kode unik tagihan periode (INV-YYYYMM-XXXX)."""
    now_str = datetime.now().strftime("%Y%m")
    return f"INV-{now_str}-{student_id:03d}-P{period_number}"

def generate_receipt_number(payment_id=None):
    """Menghasilkan nomor unik kuitansi pembayaran (KW-YYYYMM-XXXX)."""
    now_str = datetime.now().strftime("%Y%m%d")
    import secrets
    rnd = secrets.token_hex(2).upper()
    return f"KW-{now_str}-{rnd}"

def get_student_bills(student_id=None, program_id=None, status=None, search=None, db_path=None):
    """Mengambil daftar tagihan periode siswa dengan filter."""
    query = """
        SELECT b.*,
               st.full_name as student_name, st.grade as student_grade,
               pr.name as program_name, pr.code as program_code,
               p.full_name as parent_name, p.phone as parent_phone
        FROM student_bills b
        JOIN students st ON b.student_id = st.id
        JOIN programs pr ON b.program_id = pr.id
        LEFT JOIN parents p ON st.parent_id = p.id
    """
    conditions = []
    args = []

    if student_id:
        conditions.append("b.student_id = ?")
        args.append(student_id)
    if program_id:
        conditions.append("b.program_id = ?")
        args.append(program_id)
    if status:
        conditions.append("b.status = ?")
        args.append(status)
    if search:
        conditions.append("(st.full_name LIKE ? OR b.bill_code LIKE ? OR p.full_name LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term, term])

    if conditions:
        query += f" WHERE {' AND '.join(conditions)}"

    query += " ORDER BY b.created_at DESC"
    return query_db(query, args, db_path=db_path)

def create_student_bill(student_id, program_id, period_number, title, total_amount, due_date=None, notes=None, db_path=None):
    """Membuat tagihan periode baru untuk siswa pada program tertentu."""
    bill_code = generate_bill_code(int(student_id), int(period_number))

    # Cek duplikasi kode tagihan
    existing = query_db("SELECT id FROM student_bills WHERE bill_code = ?", (bill_code,), one=True, db_path=db_path)
    if existing:
        import secrets
        bill_code += f"-{secrets.token_hex(1).upper()}"

    total_amount = float(total_amount)
    remaining = total_amount

    bill_id = execute_db("""
        INSERT INTO student_bills (
            bill_code, student_id, program_id, period_number,
            title, total_amount, paid_amount, remaining_amount,
            status, due_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'belum_lunas', ?, ?)
    """, (bill_code, student_id, program_id, period_number, title, total_amount, remaining, due_date, notes), db_path=db_path)

    return bill_id

def record_bill_payment(bill_id, amount, payment_date, payment_method="Transfer Bank", recorded_by=None, notes=None, db_path=None):
    """Mencatat pembayaran/cicilan tagihan dan memperbarui sisa tagihan secara atomik."""
    bill = query_db("SELECT * FROM student_bills WHERE id = ?", (bill_id,), one=True, db_path=db_path)
    if not bill:
        raise ValueError("Tagihan tidak ditemukan.")

    amount = float(amount)
    if amount <= 0:
        raise ValueError("Nominal pembayaran harus lebih besar dari 0.")

    paid_before = float(bill["paid_amount"] or 0)
    total_amount = float(bill["total_amount"] or 0)
    new_paid = paid_before + amount
    new_remaining = max(0.0, total_amount - new_paid)

    if new_remaining == 0:
        new_status = "lunas"
    elif new_paid > 0:
        new_status = "sebagian"
    else:
        new_status = "belum_lunas"

    receipt_number = generate_receipt_number()

    # Catat pembayaran
    payment_id = execute_db("""
        INSERT INTO bill_payments (
            receipt_number, bill_id, student_id, program_id,
            amount, payment_date, payment_method, recorded_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (receipt_number, bill_id, bill["student_id"], bill["program_id"], amount, payment_date, payment_method, recorded_by, notes), db_path=db_path)

    # Perbarui tagihan
    execute_db("""
        UPDATE student_bills
        SET paid_amount = ?, remaining_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_paid, new_remaining, new_status, bill_id), db_path=db_path)

    # Jika tagihan sudah lunas, nonaktifkan peringatan tagihan periode baru terkait periode sebelumnya
    if new_remaining == 0 or new_status == "lunas":
        execute_db("""
            UPDATE mentor_period_honor
            SET billing_alert_active = 0
            WHERE student_id = ? AND program_id = ? AND period_number <= ?
        """, (bill["student_id"], bill["program_id"], int(bill["period_number"] or 1)), db_path=db_path)

    return payment_id, receipt_number

def get_student_bill_detail(bill_id, db_path=None):
    """Mengambil rincian tagihan beserta histori seluruh cicilan/pembayarannya."""
    bill = query_db("""
        SELECT b.*,
               st.full_name as student_name, st.grade as student_grade, st.school as student_school,
               pr.name as program_name, pr.code as program_code,
               p.full_name as parent_name, p.phone as parent_phone, p.address as parent_address
        FROM student_bills b
        JOIN students st ON b.student_id = st.id
        JOIN programs pr ON b.program_id = pr.id
        LEFT JOIN parents p ON st.parent_id = p.id
        WHERE b.id = ?
    """, (bill_id,), one=True, db_path=db_path)

    if not bill:
        return None, []

    payments = query_db("""
        SELECT bp.*, u.full_name as recorder_name
        FROM bill_payments bp
        LEFT JOIN users u ON bp.recorded_by = u.id
        WHERE bp.bill_id = ?
        ORDER BY bp.payment_date DESC, bp.created_at DESC
    """, (bill_id,), db_path=db_path)

    return bill, payments

def get_bill_payment_receipt(payment_id, db_path=None):
    """Mengambil rincian lengkap kuitansi pembayaran untuk keperluan cetak/PDF."""
    return query_db("""
        SELECT bp.*,
               b.bill_code, b.title as bill_title, b.period_number,
               b.total_amount, b.paid_amount as bill_paid_total, b.remaining_amount, b.status as bill_status,
               st.full_name as student_name, st.grade as student_grade,
               pr.name as program_name,
               p.full_name as parent_name, p.phone as parent_phone,
               u.full_name as recorder_name
        FROM bill_payments bp
        JOIN student_bills b ON bp.bill_id = b.id
        JOIN students st ON bp.student_id = st.id
        LEFT JOIN programs pr ON bp.program_id = pr.id
        LEFT JOIN parents p ON st.parent_id = p.id
        LEFT JOIN users u ON bp.recorded_by = u.id
        WHERE bp.id = ?
    """, (payment_id,), one=True, db_path=db_path)

def get_all_payments(start_date=None, end_date=None, student_id=None, bill_id=None, db_path=None):
    """Mengambil seluruh riwayat transaksi pembayaran murid."""
    query = """
        SELECT bp.*,
               b.bill_code, b.period_number,
               st.full_name as student_name,
               pr.name as program_name,
               p.full_name as parent_name,
               u.full_name as recorder_name
        FROM bill_payments bp
        JOIN student_bills b ON bp.bill_id = b.id
        JOIN students st ON bp.student_id = st.id
        LEFT JOIN programs pr ON bp.program_id = pr.id
        LEFT JOIN parents p ON st.parent_id = p.id
        LEFT JOIN users u ON bp.recorded_by = u.id
    """
    conditions = []
    args = []

    if start_date:
        conditions.append("date(bp.payment_date) >= date(?)")
        args.append(start_date)
    if end_date:
        conditions.append("date(bp.payment_date) <= date(?)")
        args.append(end_date)
    if student_id:
        conditions.append("bp.student_id = ?")
        args.append(student_id)
    if bill_id:
        conditions.append("bp.bill_id = ?")
        args.append(bill_id)

    if conditions:
        query += f" WHERE {' AND '.join(conditions)}"

    query += " ORDER BY bp.payment_date DESC, bp.created_at DESC"
    return query_db(query, args, db_path=db_path)

def get_financial_overview(db_path=None):
    """Menghitung agregasi keuangan eksekutif untuk Admin dan Pemilik."""
    bills = query_db("""
        SELECT
            COUNT(id) as total_bills_count,
            COALESCE(SUM(total_amount), 0) as total_billed,
            COALESCE(SUM(paid_amount), 0) as total_collected,
            COALESCE(SUM(remaining_amount), 0) as total_outstanding,
            SUM(CASE WHEN status = 'lunas' THEN 1 ELSE 0 END) as fully_paid_count,
            SUM(CASE WHEN status IN ('belum_lunas', 'sebagian') THEN 1 ELSE 0 END) as unpaid_count
        FROM student_bills
    """, one=True, db_path=db_path)

    recent_payments = query_db("""
        SELECT bp.*, st.full_name as student_name, pr.name as program_name, b.period_number
        FROM bill_payments bp
        JOIN students st ON bp.student_id = st.id
        LEFT JOIN programs pr ON bp.program_id = pr.id
        JOIN student_bills b ON bp.bill_id = b.id
        ORDER BY bp.payment_date DESC, bp.created_at DESC
        LIMIT 10
    """, db_path=db_path)

    return {
        "total_bills_count": bills["total_bills_count"] or 0,
        "total_billed": bills["total_billed"] or 0.0,
        "total_collected": bills["total_collected"] or 0.0,
        "total_outstanding": bills["total_outstanding"] or 0.0,
        "fully_paid_count": bills["fully_paid_count"] or 0,
        "unpaid_count": bills["unpaid_count"] or 0,
        "recent_payments": recent_payments
    }

def get_mentor_honor_summary(mentor_id=None, start_date=None, end_date=None, rate_per_session=None, db_path=None):
    """
    Menghitung rekapitulasi realisasi mengajar mentor dan perkiraan honor:
    - Hanya menghitung sesi yang BENAR-BENAR TERLAKSANA (session_status='terlaksana' / status='hadir').
    - Sesi siswa_berhalangan atau mentor_berhalangan TIDAK dihitung sebagai sesi terlaksana.
    - Tarif per sesi opsional (default None = Menunggu Penetapan Pemilik).
    """
    query = """
        SELECT m.id as mentor_id, m.full_name as mentor_name, m.phone as mentor_phone,
               m.expertise, m.status as mentor_status,
               COUNT(a.id) as total_recorded_sessions,
               SUM(CASE WHEN a.session_status = 'terlaksana' OR (a.session_status IS NULL AND a.status = 'hadir') THEN 1 ELSE 0 END) as completed_sessions,
               SUM(CASE WHEN a.session_status = 'siswa_berhalangan' OR a.status = 'izin' THEN 1 ELSE 0 END) as student_absent_sessions,
               SUM(CASE WHEN a.session_status = 'mentor_berhalangan' OR a.status = 'tidak_hadir' THEN 1 ELSE 0 END) as mentor_absent_sessions
        FROM mentors m
        LEFT JOIN attendance a ON m.id = a.mentor_id
    """
    conditions = []
    args = []

    if mentor_id:
        conditions.append("m.id = ?")
        args.append(mentor_id)
    if start_date:
        conditions.append("date(a.recorded_at) >= date(?)")
        args.append(start_date)
    if end_date:
        conditions.append("date(a.recorded_at) <= date(?)")
        args.append(end_date)

    if conditions:
        query += f" WHERE {' AND '.join(conditions)}"

    query += " GROUP BY m.id ORDER BY m.full_name ASC"
    rows = query_db(query, args, db_path=db_path)

    rate = None
    if rate_per_session is not None and str(rate_per_session).strip() != "":
        try:
            rate = float(rate_per_session)
        except (ValueError, TypeError):
            rate = None

    result = []
    for r in rows:
        completed = r["completed_sessions"] or 0
        periods_completed = completed // 8
        remaining_in_period = completed % 8
        estimated_honor = (completed * rate) if rate is not None else None
        result.append({
            "mentor_id": r["mentor_id"],
            "mentor_name": r["mentor_name"],
            "mentor_phone": r["mentor_phone"],
            "expertise": r["expertise"],
            "mentor_status": r["mentor_status"],
            "total_recorded_sessions": r["total_recorded_sessions"] or 0,
            "completed_sessions": completed,
            "student_absent_sessions": r["student_absent_sessions"] or 0,
            "mentor_absent_sessions": r["mentor_absent_sessions"] or 0,
            "periods_completed": periods_completed,
            "remaining_in_period": remaining_in_period,
            "rate_per_session": rate,
            "estimated_honor": estimated_honor
        })

    return result


def get_pending_new_students(db_path=None):
    """Mengambil siswa baru yang berstatus 'menunggu_validasi' pembayaran sebelum diizinkan belajar."""
    return query_db("""
        SELECT st.*, p.full_name as parent_name, p.phone as parent_phone,
               GROUP_CONCAT(pr.name, ', ') as enrolled_programs,
               b.id as initial_bill_id, b.total_amount as initial_bill_amount,
               b.paid_amount as initial_paid_amount, b.remaining_amount as initial_remaining,
               b.status as bill_status
        FROM students st
        LEFT JOIN parents p ON st.parent_id = p.id
        LEFT JOIN student_programs sp ON st.id = sp.student_id
        LEFT JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN student_bills b ON st.id = b.student_id AND b.period_number = 1
        WHERE (st.payment_status = 'menunggu_validasi' OR st.status = 'menunggu_validasi')
        GROUP BY st.id
        ORDER BY st.created_at DESC
    """, db_path=db_path)


def validate_new_student_payment(student_id, validated_by_user_id, db_path=None):
    """Owner memvalidasi pembayaran murid baru dan membuka izin pembelajaran."""
    student = query_db("SELECT id, full_name, status FROM students WHERE id = ?", (student_id,), one=True, db_path=db_path)
    if not student:
        raise ValueError("Data siswa tidak ditemukan.")

    execute_db("""
        UPDATE students
        SET status = 'aktif', payment_status = 'lunas', payment_validated_by = ?, payment_validated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (validated_by_user_id, student_id), db_path=db_path)

    execute_db("""
        UPDATE student_programs
        SET status = 'aktif'
        WHERE student_id = ? AND status = 'menunggu_validasi'
    """, (student_id,), db_path=db_path)

    return student


def update_mentor_fee_rate(mentor_id, fee_per_session, fee_per_session_4=None, db_path=None):
    """Owner memperbarui tarif honor default mentor per satu pertemuan (sesi) untuk paket 8 dan paket 4 pertemuan."""
    fee = float(fee_per_session)
    if fee < 0:
        raise ValueError("Tarif fee tidak boleh bernilai negatif.")
    fee_4 = float(fee_per_session_4) if (fee_per_session_4 is not None and str(fee_per_session_4).strip() != "") else None
    if fee_4 is not None and fee_4 < 0:
        raise ValueError("Tarif fee paket 4 tidak boleh bernilai negatif.")

    execute_db("UPDATE mentors SET fee_per_session = ?, fee_per_session_4 = ? WHERE id = ?", (fee, fee_4, mentor_id), db_path=db_path)
    # Perbarui kalkulasi honor yang belum ditransfer (siap_ditransfer) yang TIDAK memiliki tarif fee khusus
    execute_db("""
        UPDATE mentor_period_honor
        SET fee_per_session = ?, total_fee = completed_meetings * ?, updated_at = CURRENT_TIMESTAMP
        WHERE mentor_id = ? AND status = 'siap_ditransfer'
          AND NOT EXISTS (
              SELECT 1 FROM mentor_student_program_fees mspf
              WHERE mspf.mentor_id = mentor_period_honor.mentor_id
                AND mspf.student_id = mentor_period_honor.student_id
                AND mspf.program_id = mentor_period_honor.program_id
          )
    """, (fee, fee, mentor_id), db_path=db_path)
    return fee, fee_4


def get_mentor_student_program_fees(mentor_id, db_path=None):
    """
    Mengambil daftar murid dan program yang diajar oleh mentor tertentu,
    beserta tarif fee khusus per sesi yang telah ditetapkan oleh Owner.
    Jika satu siswa mengambil 2 program dengan mentor yang sama,
    keduanya muncul sebagai baris terpisah sehingga Owner dapat menetapkan tarif berbeda untuk masing-masing program.
    """
    query = """
        SELECT DISTINCT pairs.student_id, st.full_name as student_name, st.grade as student_grade,
               pairs.program_id, pr.name as program_name,
               COALESCE(sp.meetings_per_period, 8) as meetings_per_period,
               mspf.id as custom_fee_id,
               mspf.fee_per_session as custom_fee_per_session,
               mspf.notes as fee_notes,
               m.fee_per_session as default_mentor_fee,
               m.fee_per_session_4 as default_mentor_fee_4
        FROM (
            SELECT student_id, program_id FROM mentor_student_program_fees WHERE mentor_id = ?
            UNION
            SELECT student_id, program_id FROM routine_schedules WHERE mentor_id = ? AND student_id IS NOT NULL AND program_id IS NOT NULL
            UNION
            SELECT student_id, program_id FROM schedules WHERE mentor_id = ? AND student_id IS NOT NULL AND program_id IS NOT NULL
            UNION
            SELECT a.student_id, COALESCE(a.program_id, s.program_id) as program_id 
            FROM attendance a 
            LEFT JOIN schedules s ON a.schedule_id = s.id 
            WHERE a.mentor_id = ? AND a.student_id IS NOT NULL AND COALESCE(a.program_id, s.program_id) IS NOT NULL
        ) pairs
        JOIN students st ON pairs.student_id = st.id
        JOIN programs pr ON pairs.program_id = pr.id
        LEFT JOIN student_programs sp ON (sp.student_id = st.id AND sp.program_id = pr.id)
        JOIN mentors m ON m.id = ?
        LEFT JOIN mentor_student_program_fees mspf ON (mspf.mentor_id = ? AND mspf.student_id = st.id AND mspf.program_id = pr.id)
        ORDER BY st.full_name ASC, pr.name ASC
    """
    rows = query_db(query, (mentor_id, mentor_id, mentor_id, mentor_id, mentor_id, mentor_id), db_path=db_path)

    results = []
    for r in rows:
        row = dict(r)
        mpp = int(row.get("meetings_per_period") or 8)
        default_fee = float(row.get("default_mentor_fee") or 35000.0)
        default_fee_4 = row.get("default_mentor_fee_4")
        default_fee_4 = float(default_fee_4) if (default_fee_4 is not None and str(default_fee_4).strip() != "") else None

        if row.get("custom_fee_per_session") is not None:
            effective_fee = float(row["custom_fee_per_session"])
            is_custom = True
        else:
            if mpp == 4 and default_fee_4 is not None and default_fee_4 > 0:
                effective_fee = default_fee_4
            else:
                effective_fee = default_fee
            is_custom = False

        row["effective_fee_per_session"] = effective_fee
        row["is_custom"] = is_custom
        row["estimated_period_honor"] = effective_fee * mpp
        results.append(row)

    return results


def save_mentor_student_program_fee(mentor_id, student_id, program_id, fee_per_session, notes=None, db_path=None):
    """
    Menyimpan atau memperbarui tarif fee per sesi untuk kombinasi mentor, murid, dan program tertentu.
    Juga memperbarui kalkulasi honor periode yang belum ditransfer (siap_ditransfer) untuk kombinasi ini.
    """
    fee = float(fee_per_session)
    if fee < 0:
        raise ValueError("Tarif fee per sesi tidak boleh bernilai negatif.")

    existing = query_db("""
        SELECT id FROM mentor_student_program_fees
        WHERE mentor_id = ? AND student_id = ? AND program_id = ?
    """, (mentor_id, student_id, program_id), one=True, db_path=db_path)

    if existing:
        execute_db("""
            UPDATE mentor_student_program_fees
            SET fee_per_session = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (fee, notes, existing["id"]), db_path=db_path)
    else:
        execute_db("""
            INSERT INTO mentor_student_program_fees (mentor_id, student_id, program_id, fee_per_session, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (mentor_id, student_id, program_id, fee, notes), db_path=db_path)

    # Sinkronisasi ke honor yang belum ditransfer
    execute_db("""
        UPDATE mentor_period_honor
        SET fee_per_session = ?, total_fee = completed_meetings * ?, updated_at = CURRENT_TIMESTAMP
        WHERE mentor_id = ? AND student_id = ? AND program_id = ? AND status = 'siap_ditransfer'
    """, (fee, fee, mentor_id, student_id, program_id), db_path=db_path)

    return fee


def delete_mentor_student_program_fee(mentor_id, student_id, program_id, db_path=None):
    """Menghapus tarif khusus murid & program mentor sehingga kembali ke tarif default mentor."""
    execute_db("""
        DELETE FROM mentor_student_program_fees
        WHERE mentor_id = ? AND student_id = ? AND program_id = ?
    """, (mentor_id, student_id, program_id), db_path=db_path)

    # Kembalikan honor yang belum ditransfer ke tarif default
    m = query_db("SELECT fee_per_session, fee_per_session_4 FROM mentors WHERE id = ?", (mentor_id,), one=True, db_path=db_path)
    sp = query_db("SELECT meetings_per_period FROM student_programs WHERE student_id = ? AND program_id = ?", (student_id, program_id), one=True, db_path=db_path)
    mpp = int(sp["meetings_per_period"]) if (sp and "meetings_per_period" in sp.keys() and sp["meetings_per_period"]) else 8

    if m:
        if mpp == 4 and m["fee_per_session_4"] is not None and m["fee_per_session_4"] > 0:
            rate = float(m["fee_per_session_4"])
        else:
            rate = float(m["fee_per_session"] or 35000.0)

        execute_db("""
            UPDATE mentor_period_honor
            SET fee_per_session = ?, total_fee = completed_meetings * ?, updated_at = CURRENT_TIMESTAMP
            WHERE mentor_id = ? AND student_id = ? AND program_id = ? AND status = 'siap_ditransfer'
        """, (rate, rate, mentor_id, student_id, program_id), db_path=db_path)


def sync_and_get_mentor_period_honors(db_path=None):
    """
    Menyelaraskan data absensi (per 8 pertemuan terlaksana) ke dalam pencatatan fee honor mentor:
    - 1 Periode Fee = 8 Pertemuan Selesai Terlaksana.
    - Terdeteksi saat ada sesi absensi ke-8 (meeting_number = 8 atau kelipatan 8) yang telah diisi dan terlaksana.
    - Fee dihitung per mentor yang mengajar di periode tersebut: (jumlah sesi diajar) × (fee_per_session).
    - Menghasilkan status 'siap_ditransfer' bagi Owner jika sudah 8 pertemuan tapi belum ditransfer.
    - Menyajikan peringatan bagi Pemilik untuk memberikan fee.
    """
    from services.meeting_service import MEETINGS_PER_PERIOD

    # Dapatkan seluruh kombinasi siswa & program yang memiliki absensi terlaksana
    pairs = query_db("""
        SELECT a.student_id, COALESCE(a.program_id, s.program_id) as program_id,
               st.full_name as student_name, pr.name as program_name
        FROM attendance a
        LEFT JOIN schedules s ON a.schedule_id = s.id
        JOIN students st ON a.student_id = st.id
        LEFT JOIN programs pr ON COALESCE(a.program_id, s.program_id) = pr.id
        WHERE (a.session_status = 'terlaksana' OR (a.session_status IS NULL AND a.status = 'hadir'))
        GROUP BY a.student_id, COALESCE(a.program_id, s.program_id)
    """, db_path=db_path)

    for pair in pairs:
        st_id = pair["student_id"]
        pr_id = pair["program_id"]

        # Dapatkan jumlah pertemuan per periode untuk siswa & program ini (default 8, atau 4 pertemuan)
        sp = query_db("""
            SELECT initial_periods_completed, initial_last_meeting, meetings_per_period
            FROM student_programs
            WHERE student_id = ? AND program_id = ?
        """, (st_id, pr_id), one=True, db_path=db_path)
        mpp = int(sp["meetings_per_period"]) if (sp and "meetings_per_period" in sp.keys() and sp["meetings_per_period"]) else 8
        mpp = mpp or 8

        # Cari periode-periode yang sudah memiliki pertemuan ke-mpp selesai (atau minimal mpp pertemuan)
        periods_raw = query_db("""
            SELECT COALESCE(a.period_number, 1) as period_num,
                   COUNT(a.id) as sessions_in_period,
                   MAX(COALESCE(a.meeting_number, 0)) as max_meeting
            FROM attendance a
            LEFT JOIN schedules s ON a.schedule_id = s.id
            WHERE a.student_id = ? AND COALESCE(a.program_id, s.program_id) = ?
              AND (a.session_status = 'terlaksana' OR (a.session_status IS NULL AND a.status = 'hadir'))
            GROUP BY COALESCE(a.period_number, 1)
            HAVING MAX(COALESCE(a.meeting_number, 0)) >= ? OR COUNT(a.id) >= ?
        """, (st_id, pr_id, mpp, mpp), db_path=db_path)

        for p_row in periods_raw:
            period_num = p_row["period_num"]

            # Cek apakah ada offset pertemuan pra-sistem di periode ini dari student_programs
            pre_system_offset = 0
            if sp:
                init_p = sp["initial_periods_completed"] or 1
                init_m = sp["initial_last_meeting"] or 0
                if init_p == period_num and init_m > 0:
                    pre_system_offset = int(init_m)

            # Cari mentor siapa saja yang mengajar dalam periode pertemuan ini
            mentor_sessions = query_db("""
                SELECT a.mentor_id, m.full_name as mentor_name, m.fee_per_session, m.fee_per_session_4, COUNT(a.id) as count_sessions
                FROM attendance a
                LEFT JOIN schedules s ON a.schedule_id = s.id
                JOIN mentors m ON a.mentor_id = m.id
                WHERE a.student_id = ? AND COALESCE(a.program_id, s.program_id) = ? AND COALESCE(a.period_number, 1) = ?
                  AND (a.session_status = 'terlaksana' OR (a.session_status IS NULL AND a.status = 'hadir'))
                GROUP BY a.mentor_id
            """, (st_id, pr_id, period_num), db_path=db_path)

            for ms in mentor_sessions:
                m_id = ms["mentor_id"]
                # Cek apakah ada tarif khusus mentor untuk murid dan program spesifik ini (Detail Fee Tentor)
                custom_fee_row = query_db("""
                    SELECT fee_per_session FROM mentor_student_program_fees
                    WHERE mentor_id = ? AND student_id = ? AND program_id = ?
                """, (m_id, st_id, pr_id), one=True, db_path=db_path)

                if custom_fee_row and custom_fee_row["fee_per_session"] is not None and custom_fee_row["fee_per_session"] > 0:
                    rate = float(custom_fee_row["fee_per_session"])
                elif mpp == 4 and ms["fee_per_session_4"] is not None and ms["fee_per_session_4"] > 0:
                    rate = float(ms["fee_per_session_4"])
                else:
                    rate = float(ms["fee_per_session"] if ms["fee_per_session"] is not None else 35000.0)
                sessions_count = int(ms["count_sessions"])

                # Jika ada offset sesi pra-sistem (pertemuan 1-3 sebelum sistem),
                # tambahkan ke mentor yang mengajar di periode ini agar total siklus menjadi lengkap
                if pre_system_offset > 0:
                    sessions_count += pre_system_offset

                # Batas maksimal per periode adalah mpp sesi pertemuan (misal 4 atau 8)
                sessions_count = min(mpp, sessions_count)
                total_fee = sessions_count * rate

                existing = query_db("""
                    SELECT id, status, completed_meetings, total_fee FROM mentor_period_honor
                    WHERE mentor_id = ? AND student_id = ? AND program_id = ? AND period_number = ?
                """, (m_id, st_id, pr_id, period_num), one=True, db_path=db_path)

                if not existing:
                    execute_db("""
                        INSERT INTO mentor_period_honor (
                            mentor_id, student_id, program_id, period_number,
                            completed_meetings, fee_per_session, total_fee, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'siap_ditransfer')
                    """, (m_id, st_id, pr_id, period_num, sessions_count, rate, total_fee), db_path=db_path)
                elif existing["status"] == "siap_ditransfer":
                    execute_db("""
                        UPDATE mentor_period_honor
                        SET completed_meetings = ?, fee_per_session = ?, total_fee = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (sessions_count, rate, total_fee, existing["id"]), db_path=db_path)

    honors = query_db("""
        SELECT h.*,
               m.full_name as mentor_name, m.phone as mentor_phone, m.expertise,
               st.full_name as student_name, st.grade as student_grade,
               pr.name as program_name,
               p.full_name as parent_name, p.phone as parent_phone,
               u.full_name as transferred_by_name,
               sp.initial_periods_completed, sp.initial_last_meeting
        FROM mentor_period_honor h
        JOIN mentors m ON h.mentor_id = m.id
        JOIN students st ON h.student_id = st.id
        JOIN programs pr ON h.program_id = pr.id
        LEFT JOIN student_programs sp ON (h.student_id = sp.student_id AND h.program_id = sp.program_id)
        LEFT JOIN parents p ON st.parent_id = p.id
        LEFT JOIN users u ON h.transferred_by = u.id
        ORDER BY h.period_number DESC, h.created_at DESC
    """, db_path=db_path)

    ready_count = sum(1 for h in honors if h["status"] == "siap_ditransfer")
    transferred_count = sum(1 for h in honors if h["status"] == "sudah_ditransfer")

    return {
        "honors": honors,
        "ready_count": ready_count,
        "transferred_count": transferred_count
    }


def mark_mentor_honor_as_transferred(honor_id, transferred_by_user_id, notes=None, db_path=None):
    """
    Owner menandai bahwa fee honor 8 pertemuan untuk mentor sudah ditransfer.
    Otomatis mengaktifkan peringatan penagihan ke wali murid untuk periode berikutnya!
    """
    honor = query_db("SELECT * FROM mentor_period_honor WHERE id = ?", (honor_id,), one=True, db_path=db_path)
    if not honor:
        raise ValueError("Data honor tidak ditemukan.")

    execute_db("""
        UPDATE mentor_period_honor
        SET status = 'sudah_ditransfer',
            transferred_at = CURRENT_TIMESTAMP,
            transferred_by = ?,
            transfer_notes = ?,
            billing_alert_active = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (transferred_by_user_id, notes, honor_id), db_path=db_path)

    next_period = honor["period_number"] + 1
    existing_bill = query_db("""
        SELECT id FROM student_bills
        WHERE student_id = ? AND program_id = ? AND period_number = ?
    """, (honor["student_id"], honor["program_id"], next_period), one=True, db_path=db_path)

    if not existing_bill:
        pr = query_db("SELECT name FROM programs WHERE id = ?", (honor["program_id"],), one=True, db_path=db_path)
        prog_name = pr["name"] if pr else "Les"
        title = f"Tagihan {prog_name} - Periode {next_period} ({honor['completed_meetings']} Pertemuan)"
        prev_bill = query_db("""
            SELECT total_amount FROM student_bills
            WHERE student_id = ? AND program_id = ?
            ORDER BY period_number DESC LIMIT 1
        """, (honor["student_id"], honor["program_id"]), one=True, db_path=db_path)
        if prev_bill:
            amount = float(prev_bill["total_amount"])
        else:
            pr_data = query_db("SELECT default_fee_8, default_fee_4 FROM programs WHERE id = ?", (honor["program_id"],), one=True, db_path=db_path)
            if pr_data:
                amount = float(pr_data["default_fee_4"] if honor["completed_meetings"] == 4 and pr_data["default_fee_4"] else (pr_data["default_fee_8"] or 800000.0))
            else:
                amount = 450000.0 if honor["completed_meetings"] == 4 else 800000.0

        create_student_bill(
            student_id=honor["student_id"],
            program_id=honor["program_id"],
            period_number=next_period,
            title=title,
            total_amount=amount,
            notes=f"Tagihan otomatis setelah penyelesaian {honor['completed_meetings']} pertemuan Periode {honor['period_number']} dan pencairan fee mentor.",
            db_path=db_path
        )

    return honor


def update_mentor_period_honor_meetings(honor_id, meetings_count, db_path=None):
    """
    Owner menyesuaikan jumlah pertemuan/sesi yang dihitung untuk honor periode tertentu.
    Misalnya jika ada pembagian sesi antar tentor atau penyesuaian sesi manual.
    """
    honor = query_db("SELECT * FROM mentor_period_honor WHERE id = ?", (honor_id,), one=True, db_path=db_path)
    if not honor:
        raise ValueError("Data honor tidak ditemukan.")
    count = int(meetings_count)
    if count < 1 or count > 8:
        raise ValueError("Jumlah sesi pertemuan harus antara 1 dan 8.")
    rate = float(honor["fee_per_session"])
    total = count * rate
    execute_db("""
        UPDATE mentor_period_honor
        SET completed_meetings = ?, total_fee = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (count, total, honor_id), db_path=db_path)
    return {"id": honor_id, "completed_meetings": count, "total_fee": total}


def get_billing_alerts_summary(db_path=None):
    """
    Mengambil daftar peringatan penagihan ke wali murid:
    - Muncul saat fee mentor periode sebelumnya telah dibagikan (status 'sudah_ditransfer').
    - Mengingatkan Admin dan Owner untuk menagih wali murid untuk periode berikutnya.
    """
    return query_db("""
        SELECT h.id as honor_id, h.period_number, h.transferred_at, h.total_fee,
               m.full_name as mentor_name,
               st.id as student_id, st.full_name as student_name, st.grade as student_grade,
               pr.id as program_id, pr.name as program_name,
               p.id as parent_id, p.full_name as parent_name, p.phone as parent_phone,
               b.id as next_bill_id, b.bill_code, b.total_amount, b.paid_amount, b.remaining_amount, b.status as bill_status
        FROM mentor_period_honor h
        JOIN mentors m ON h.mentor_id = m.id
        JOIN students st ON h.student_id = st.id
        JOIN programs pr ON h.program_id = pr.id
        LEFT JOIN parents p ON st.parent_id = p.id
        LEFT JOIN student_bills b ON st.id = b.student_id AND pr.id = b.program_id AND b.period_number = (h.period_number + 1)
        WHERE h.status = 'sudah_ditransfer' 
          AND h.billing_alert_active = 1
          AND b.id IS NOT NULL
          AND b.status != 'lunas'
          AND COALESCE(b.remaining_amount, b.total_amount) > 0
        ORDER BY h.transferred_at DESC
    """, db_path=db_path)


def record_owner_custom_payment(bill_id, amount, payment_option, target_total_amount=None, payment_date=None, payment_method="Transfer Bank", notes=None, recorded_by=None, db_path=None):
    """
    Owner mencatat pembayaran dari wali murid (bisa tunai / transfer):
    - Jika 'lunas': Tagihan langsung lunas, sisa tunggakan = 0.
    - Jika 'cicilan': Owner menentukan target nominal agar lunas, sistem mendeteksi sisa tunggakan yang belum dibayar.
    """
    bill = query_db("SELECT * FROM student_bills WHERE id = ?", (bill_id,), one=True, db_path=db_path)
    if not bill:
        raise ValueError("Tagihan tidak ditemukan.")

    amount = float(amount)
    if amount <= 0:
        raise ValueError("Nominal pembayaran harus lebih besar dari Rp 0.")

    if not payment_date:
        payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing_paid = float(bill["paid_amount"] or 0)
    current_total = float(bill["total_amount"] or 0)

    if payment_option == "lunas":
        new_paid = existing_paid + amount
        new_total = max(current_total, new_paid)
        new_remaining = 0.0
        new_status = "lunas"
    else:  # cicilan
        if target_total_amount is not None and str(target_total_amount).strip() != "":
            new_total = float(target_total_amount)
        else:
            new_total = current_total

        new_paid = existing_paid + amount
        new_remaining = max(0.0, new_total - new_paid)
        new_status = "lunas" if new_remaining == 0 else "sebagian"

    receipt_number = generate_receipt_number()

    # Catat ke bill_payments
    payment_id = execute_db("""
        INSERT INTO bill_payments (
            receipt_number, bill_id, student_id, program_id,
            amount, payment_date, payment_method, recorded_by, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (receipt_number, bill_id, bill["student_id"], bill["program_id"], amount, payment_date, payment_method, recorded_by, notes), db_path=db_path)

    # Perbarui student_bills
    execute_db("""
        UPDATE student_bills
        SET total_amount = ?, paid_amount = ?, remaining_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_total, new_paid, new_remaining, new_status, bill_id), db_path=db_path)

    # Jika tagihan sudah lunas, nonaktifkan peringatan tagihan periode baru terkait periode sebelumnya
    if new_remaining == 0 or new_status == "lunas":
        execute_db("""
            UPDATE mentor_period_honor
            SET billing_alert_active = 0
            WHERE student_id = ? AND program_id = ? AND period_number <= ?
        """, (bill["student_id"], bill["program_id"], int(bill["period_number"] or 1)), db_path=db_path)

    # Jika siswa baru masih dalam status menunggu_validasi, otomatis validasi jika pembayaran lunas
    st = query_db("SELECT payment_status FROM students WHERE id = ?", (bill["student_id"],), one=True, db_path=db_path)
    if st and st["payment_status"] == "menunggu_validasi" and (payment_option == "lunas" or new_remaining == 0):
        validate_new_student_payment(bill["student_id"], recorded_by, db_path=db_path)

    return payment_id, receipt_number, new_remaining


def get_monthly_finance_report(month_str=None, db_path=None):
    """
    Menghasilkan laporan keuangan kas masuk (pembayaran orang tua) & kas keluar (honor mentor):
    - Filter per bulan (format 'YYYY-MM', misal '2026-11' atau 'all').
    - Menghitung Total Uang Masuk, Total Uang Keluar, dan Saldo Kas Bersih.
    - Menghasilkan daftar riwayat transaksi kas terpadu (kronologis descending).
    """
    now = datetime.now()
    if not month_str:
        month_str = now.strftime("%Y-%m")

    # Ambil daftar bulan yang tersedia dari riwayat transaksi
    months_query = query_db("""
        SELECT DISTINCT strftime('%Y-%m', payment_date) as ym FROM bill_payments WHERE payment_date IS NOT NULL
        UNION
        SELECT DISTINCT strftime('%Y-%m', transferred_at) as ym FROM mentor_period_honor WHERE transferred_at IS NOT NULL
        ORDER BY ym DESC
    """, db_path=db_path)
    available_months = [m["ym"] for m in months_query if m["ym"]]
    if month_str != "all" and month_str not in available_months:
        available_months.insert(0, month_str)

    # 1. Uang Masuk (Pembayaran Tagihan / Cicilan dari Orang Tua)
    in_query = """
        SELECT bp.id, bp.receipt_number, bp.amount, bp.payment_date, bp.payment_method, bp.notes,
               st.id as student_id, st.full_name as student_name,
               pr.name as program_name,
               p.full_name as parent_name, p.phone as parent_phone,
               b.bill_code, b.period_number,
               u.full_name as recorder_name
        FROM bill_payments bp
        JOIN student_bills b ON bp.bill_id = b.id
        JOIN students st ON bp.student_id = st.id
        LEFT JOIN programs pr ON bp.program_id = pr.id
        LEFT JOIN parents p ON st.parent_id = p.id
        LEFT JOIN users u ON bp.recorded_by = u.id
    """
    in_args = []
    if month_str != "all":
        in_query += " WHERE strftime('%Y-%m', bp.payment_date) = ?"
        in_args.append(month_str)
    in_query += " ORDER BY bp.payment_date DESC, bp.created_at DESC"
    income_records = query_db(in_query, in_args, db_path=db_path)

    # 2. Uang Keluar (Honor / Fee Mengajar Tentor yang Telah Ditransfer)
    out_query = """
        SELECT h.id, h.total_fee as amount, h.transferred_at as expense_date, h.transfer_notes as notes,
               h.period_number, h.completed_meetings, h.fee_per_session,
               m.id as mentor_id, m.full_name as mentor_name, m.phone as mentor_phone,
               st.full_name as student_name,
               pr.name as program_name,
               u.full_name as transferred_by_name
        FROM mentor_period_honor h
        JOIN mentors m ON h.mentor_id = m.id
        JOIN students st ON h.student_id = st.id
        JOIN programs pr ON h.program_id = pr.id
        LEFT JOIN users u ON h.transferred_by = u.id
        WHERE h.status = 'sudah_ditransfer'
    """
    out_args = []
    if month_str != "all":
        out_query += " AND strftime('%Y-%m', h.transferred_at) = ?"
        out_args.append(month_str)
    out_query += " ORDER BY h.transferred_at DESC"
    expense_records = query_db(out_query, out_args, db_path=db_path)

    total_income = sum(float(r["amount"] or 0) for r in income_records)
    total_expense = sum(float(r["amount"] or 0) for r in expense_records)
    net_balance = total_income - total_expense

    # Susun transaksi kas terpadu (gabungan masuk & keluar)
    transactions = []
    for inc in income_records:
        transactions.append({
            "type": "masuk",
            "type_label": "Uang Masuk",
            "category": "Pembayaran Les Siswa",
            "date": inc["payment_date"],
            "amount": float(inc["amount"]),
            "party": f"{inc['student_name']} (Wali: {inc['parent_name'] or '-'})",
            "description": f"{inc['program_name']} - Periode {inc['period_number']} (Ref: {inc['receipt_number']})",
            "notes": inc["notes"] or inc["payment_method"] or "-",
            "officer": inc["recorder_name"] or "Owner",
            "raw_id": inc["id"]
        })
    for exp in expense_records:
        transactions.append({
            "type": "keluar",
            "type_label": "Uang Keluar",
            "category": "Honor Mengajar Mentor",
            "date": exp["expense_date"],
            "amount": float(exp["amount"]),
            "party": f"Mentor: {exp['mentor_name']}",
            "description": f"Fee {exp['program_name']} Siswa {exp['student_name']} (Periode {exp['period_number']}, {exp['completed_meetings']} Sesi)",
            "notes": exp["notes"] or "Transfer Honor",
            "officer": exp["transferred_by_name"] or "Owner",
            "raw_id": exp["id"]
        })

    transactions.sort(key=lambda x: str(x["date"]), reverse=True)

    return {
        "selected_month": month_str,
        "available_months": available_months,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "income_records": income_records,
        "expense_records": expense_records,
        "transactions": transactions,
        "total_transactions_count": len(transactions)
    }


def generate_finance_excel_report(month_str=None, db_path=None):
    """Menghasilkan file Excel (.xlsx) resmi untuk rekapitulasi laporan keuangan bulanan."""
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    import io

    data = get_monthly_finance_report(month_str=month_str, db_path=db_path)
    wb = openpyxl.Workbook()

    # Sheet 1: Rekap Buku Kas
    ws = wb.active
    ws.title = "Rekap Buku Kas"

    # Styling constants
    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
    subtitle_font = Font(name="Calibri", size=11, italic=True, color="475569")
    bold_font = Font(name="Calibri", size=11, bold=True)
    green_font = Font(name="Calibri", size=11, bold=True, color="16A34A")
    red_font = Font(name="Calibri", size=11, bold=True, color="DC2626")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    summary_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    # Header title
    ws["A1"] = "BIMBEL DESI PRIVAT - REKAPITULASI LAPORAN KEUANGAN KAS"
    ws["A1"].font = title_font
    period_label = "Semua Riwayat Transaksi" if data["selected_month"] == "all" else f"Periode: {data['selected_month']}"
    ws["A2"] = f"{period_label} | Dicetak otomatis oleh Sistem Desi Privat pada {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    ws["A2"].font = subtitle_font

    # Summary KPI block
    ws["A4"] = "RINGKASAN EKSEKUTIF"
    ws["A4"].font = bold_font
    ws["A5"] = "Total Uang Masuk (Wali Murid):"
    ws["B5"] = data["total_income"]
    ws["B5"].number_format = '"Rp "#,##0'
    ws["B5"].font = green_font

    ws["A6"] = "Total Uang Keluar (Honor Tentor):"
    ws["B6"] = data["total_expense"]
    ws["B6"].number_format = '"Rp "#,##0'
    ws["B6"].font = red_font

    ws["A7"] = "Saldo Kas Bersih (Net Profit):"
    ws["B7"] = data["net_balance"]
    ws["B7"].number_format = '"Rp "#,##0'
    ws["B7"].font = bold_font

    # Table headers
    headers = ["No", "Tanggal", "Jenis Kas", "Kategori", "Pihak Terkait", "Deskripsi / Program", "Uang Masuk (Rp)", "Uang Keluar (Rp)", "Keterangan / Ref", "Petugas"]
    row_idx = 9
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=h)
        cell.fill = navy_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Populate rows
    for i, t in enumerate(data["transactions"], 1):
        row_idx += 1
        ws.cell(row=row_idx, column=1, value=i).alignment = Alignment(horizontal="center")
        ws.cell(row=row_idx, column=2, value=str(t["date"])[:19]).alignment = Alignment(horizontal="center")
        
        type_cell = ws.cell(row=row_idx, column=3, value=t["type_label"])
        type_cell.alignment = Alignment(horizontal="center")
        if t["type"] == "masuk":
            type_cell.font = green_font
        else:
            type_cell.font = red_font

        ws.cell(row=row_idx, column=4, value=t["category"])
        ws.cell(row=row_idx, column=5, value=t["party"])
        ws.cell(row=row_idx, column=6, value=t["description"])

        in_cell = ws.cell(row=row_idx, column=7, value=(t["amount"] if t["type"] == "masuk" else 0))
        in_cell.number_format = '#,##0'
        in_cell.alignment = Alignment(horizontal="right")

        out_cell = ws.cell(row=row_idx, column=8, value=(t["amount"] if t["type"] == "keluar" else 0))
        out_cell.number_format = '#,##0'
        out_cell.alignment = Alignment(horizontal="right")

        ws.cell(row=row_idx, column=9, value=t["notes"])
        ws.cell(row=row_idx, column=10, value=t["officer"]).alignment = Alignment(horizontal="center")

        for c in range(1, 11):
            ws.cell(row=row_idx, column=c).border = thin_border

    # Total row
    row_idx += 1
    total_label = ws.cell(row=row_idx, column=1, value="TOTAL KESELURUHAN")
    total_label.font = bold_font
    total_label.alignment = Alignment(horizontal="center")
    ws.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=6)

    sum_in = ws.cell(row=row_idx, column=7, value=data["total_income"])
    sum_in.font = bold_font
    sum_in.number_format = '#,##0'
    sum_in.alignment = Alignment(horizontal="right")

    sum_out = ws.cell(row=row_idx, column=8, value=data["total_expense"])
    sum_out.font = bold_font
    sum_out.number_format = '#,##0'
    sum_out.alignment = Alignment(horizontal="right")

    for c in range(1, 11):
        cell = ws.cell(row=row_idx, column=c)
        cell.fill = summary_fill
        cell.border = thin_border

    # Adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or '')
            if cell.row < 4:
                continue
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def correct_bill_payment(payment_id, new_amount, reason="", user_id=None, db_path=None):
    """
    Mengoreksi nominal pembayaran salah ketik oleh admin/owner:
    - Menyesuaikan nominal pembayaran di bill_payments
    - Menghitung ulang paid_amount, remaining_amount, dan status tagihan di student_bills
    - Mencatat audit trail dengan alasan koreksi
    """
    from services.audit_service import log_audit

    if isinstance(payment_id, (tuple, list)):
        payment_id = payment_id[0]
    payment_id = int(payment_id)

    pay = query_db("SELECT * FROM bill_payments WHERE id = ?", (payment_id,), one=True, db_path=db_path)
    if not pay:
        return {"success": False, "message": "Transaksi pembayaran tidak ditemukan."}

    try:
        new_amount = float(new_amount)
        if new_amount <= 0:
            return {"success": False, "message": "Nominal baru harus lebih besar dari 0. Jika ingin membatalkan transaksi, gunakan fitur Batalkan Pembayaran."}
    except (ValueError, TypeError):
        return {"success": False, "message": "Format nominal baru tidak valid."}

    bill = query_db("SELECT * FROM student_bills WHERE id = ?", (pay["bill_id"],), one=True, db_path=db_path)
    if not bill:
        return {"success": False, "message": "Tagihan terkait tidak ditemukan."}

    old_amount = float(pay["amount"] or 0)
    diff = new_amount - old_amount

    # Hitung total pembayaran baru untuk tagihan ini
    curr_paid = float(bill["paid_amount"] or 0)
    new_paid = max(0.0, curr_paid + diff)
    total_bill = float(bill["total_amount"] or 0)
    new_remaining = max(0.0, total_bill - new_paid)

    if new_remaining == 0:
        new_status = "lunas"
    elif new_paid > 0:
        new_status = "sebagian"
    else:
        new_status = "belum_lunas"

    # Update payment
    correction_note = f" [Koreksi Rp {old_amount:,.0f} -> Rp {new_amount:,.0f}: {reason.strip()}]"
    execute_db("""
        UPDATE bill_payments
        SET amount = ?, notes = COALESCE(notes, '') || ?
        WHERE id = ?
    """, (new_amount, correction_note, payment_id), db_path=db_path)

    # Update bill
    execute_db("""
        UPDATE student_bills
        SET paid_amount = ?, remaining_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_paid, new_remaining, new_status, bill["id"]), db_path=db_path)

    # Audit log
    if user_id:
        user = query_db("SELECT username FROM users WHERE id = ?", (user_id,), one=True, db_path=db_path)
        u_name = user["username"] if user else "system"
        log_audit(
            user_id, u_name, "KOREKSI_NOMINAL_PEMBAYARAN", "bill_payments", payment_id,
            f"Koreksi nominal pembayaran kuitansi {pay['receipt_number']} dari Rp {old_amount:,.0f} menjadi Rp {new_amount:,.0f}. "
            f"Sisa tagihan disesuaikan menjadi Rp {new_remaining:,.0f} (Status: {new_status}). Alasan: {reason.strip()}",
            module_name="Keuangan"
        )

    return {
        "success": True,
        "message": f"Pembayaran kuitansi {pay['receipt_number']} berhasil dikoreksi menjadi Rp {new_amount:,.0f}. Saldo tagihan kini Rp {new_remaining:,.0f}.",
        "new_paid": new_paid,
        "new_remaining": new_remaining,
        "new_status": new_status
    }

def cancel_bill_payment(payment_id, reason="", user_id=None, db_path=None):
    """
    Membatalkan transaksi pembayaran (rollback):
    - Mengurangi nominal terbayar dari tagihan student_bills
    - Menghapus record dari bill_payments
    - Mencatat audit trail dengan alasan pembatalan
    """
    from services.audit_service import log_audit

    if isinstance(payment_id, (tuple, list)):
        payment_id = payment_id[0]
    payment_id = int(payment_id)

    pay = query_db("SELECT * FROM bill_payments WHERE id = ?", (payment_id,), one=True, db_path=db_path)
    if not pay:
        return {"success": False, "message": "Transaksi pembayaran tidak ditemukan."}

    bill = query_db("SELECT * FROM student_bills WHERE id = ?", (pay["bill_id"],), one=True, db_path=db_path)
    if not bill:
        return {"success": False, "message": "Tagihan terkait tidak ditemukan."}

    cancel_amount = float(pay["amount"] or 0)
    curr_paid = float(bill["paid_amount"] or 0)
    total_bill = float(bill["total_amount"] or 0)

    new_paid = max(0.0, curr_paid - cancel_amount)
    new_remaining = max(0.0, total_bill - new_paid)

    if new_remaining == 0:
        new_status = "lunas"
    elif new_paid > 0:
        new_status = "sebagian"
    else:
        new_status = "belum_lunas"

    receipt_num = pay["receipt_number"]

    # Hapus pembayaran
    execute_db("DELETE FROM bill_payments WHERE id = ?", (payment_id,), db_path=db_path)

    # Update status dan nominal tagihan
    execute_db("""
        UPDATE student_bills
        SET paid_amount = ?, remaining_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_paid, new_remaining, new_status, bill["id"]), db_path=db_path)

    # Audit log
    if user_id:
        user = query_db("SELECT username FROM users WHERE id = ?", (user_id,), one=True, db_path=db_path)
        u_name = user["username"] if user else "system"
        log_audit(
            user_id, u_name, "BATALKAN_PEMBAYARAN", "bill_payments", payment_id,
            f"Membatalkan pembayaran kuitansi {receipt_num} sebesar Rp {cancel_amount:,.0f}. "
            f"Saldo tagihan dikembalikan menjadi Rp {new_remaining:,.0f} (Status: {new_status}). Alasan: {reason.strip()}",
            module_name="Keuangan"
        )

    return {
        "success": True,
        "message": f"Pembayaran kuitansi {receipt_num} sebesar Rp {cancel_amount:,.0f} berhasil dibatalkan. Saldo tagihan kembali menjadi Rp {new_remaining:,.0f}.",
        "new_paid": new_paid,
        "new_remaining": new_remaining,
        "new_status": new_status
    }

