"""
DESI PRIVAT - WhatsApp Integration Service
Integrasi resmi menggunakan WhatsApp Business Platform (Meta Cloud API).
Mendukung Mode Pengujian (Simulasi Aman), pembuatan tautan wa.me,
serta pencatatan riwayat log ke tabel notification_delivery_logs.
"""
import json
import re
import urllib.parse
import requests
from config import Config
from services.database_service import execute_db, query_db

def normalize_phone_number(phone):
    """
    Menstandardisasi nomor telepon ke format internasional (misal 0812 -> 62812).
    Mengembalikan string kosong jika nomor tidak valid (< 9 digit).
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    elif digits.startswith("620"):
        digits = "62" + digits[3:]

    # Nomor ponsel Indonesia yang valid umumnya 10 - 15 digit dan berawalan 628
    if len(digits) < 9 or len(digits) > 16:
        return ""
    return digits

def create_whatsapp_link(recipient_phone, message_text):
    """
    Membuat tautan langsung wa.me untuk mengirim pesan via aplikasi WhatsApp web/mobile.
    """
    norm = normalize_phone_number(recipient_phone)
    if not norm:
        return None
    encoded_msg = urllib.parse.quote(message_text)
    return f"https://wa.me/{norm}?text={encoded_msg}"

generate_whatsapp_web_link = create_whatsapp_link

def format_schedule_notification(student_name, mentor_name, program_name, schedule_date, start_time, end_time, meeting_label=None):
    """Template notifikasi jadwal les baru / pengingat."""
    lbl = f" ({meeting_label})" if meeting_label else ""
    return (
        f"📚 *DESI PRIVAT - Jadwal Bimbingan Belajar*\n\n"
        f"Halo, menginformasikan sesi les privat telah dijadwalkan:\n"
        f"👤 *Siswa:* {student_name}\n"
        f"🧑‍🏫 *Mentor:* {mentor_name}\n"
        f"📖 *Program:* {program_name}{lbl}\n"
        f"🗓️ *Tanggal:* {schedule_date}\n"
        f"⏰ *Waktu:* {start_time} - {end_time} WIB\n\n"
        f"Mohon hadir tepat waktu. Semangat belajar! ✨\n"
        f"_DESI PRIVAT - Do The Best Be The Best_"
    )

def format_schedule_reschedule(student_name, mentor_name, program_name, old_date, new_date, new_start_time, reason=None):
    """Template informasi perubahan jadwal les."""
    reason_str = f"\n📌 *Alasan:* {reason}" if reason else ""
    return (
        f"⚠️ *DESI PRIVAT - Informasi Perubahan Jadwal*\n\n"
        f"Halo, menginformasikan bahwa sesi les untuk ananda *{student_name}* mengalami perubahan jadwal:\n"
        f"📖 *Program:* {program_name} (Mentor: {mentor_name})\n"
        f"🗓️ *Jadwal Semula:* {old_date}\n"
        f"✅ *Jadwal Baru:* {new_date} pukul {new_start_time} WIB{reason_str}\n\n"
        f"Terima kasih atas pengertian dan kerja samanya.\n"
        f"_DESI PRIVAT - Do The Best Be The Best_"
    )

def format_progress_notification(student_name, mentor_name, program_name, session_date, topics, meeting_label=None):
    """Template laporan perkembangan belajar siswa."""
    lbl = f" [{meeting_label}]" if meeting_label else ""
    return (
        f"📝 *DESI PRIVAT - Laporan Perkembangan Belajar*{lbl}\n\n"
        f"Halo, berikut ringkasan kegiatan belajar ananda *{student_name}*:\n"
        f"📖 *Program:* {program_name}\n"
        f"🧑‍🏫 *Mentor:* {mentor_name}\n"
        f"🗓️ *Tanggal Sesi:* {session_date}\n"
        f"🎯 *Materi:* {topics}\n\n"
        f"Perkembangan belajar ananda terus kami pantau untuk hasil terbaik.\n"
        f"_DESI PRIVAT - Do The Best Be The Best_"
    )

def format_operational_announcement(title, body):
    """Template pengumuman operasional les."""
    return (
        f"📢 *DESI PRIVAT - PENGUMUMAN*\n\n"
        f"*{title}*\n\n"
        f"{body}\n\n"
        f"Hubungi Admin jika ada pertanyaan lebih lanjut. Terima kasih.\n"
        f"_DESI PRIVAT - Do The Best Be The Best_"
    )

def send_whatsapp_message(recipient_phone, message_text, template_name="notifikasi_umum", notification_id=None):
    """
    Mengirim pesan WhatsApp resmi atau melakukan simulasi (jika WHATSAPP_TEST_MODE=True).
    Mencatat hasil ke tabel notification_delivery_logs.
    Membedakan dengan jelas status 'simulasi', 'sukses', dan 'gagal'.
    """
    normalized_phone = normalize_phone_number(recipient_phone)
    if not normalized_phone:
        err_msg = "Nomor telepon tujuan tidak valid atau format salah (minimal 9 digit angka)."
        execute_db("""
            INSERT INTO notification_delivery_logs (
                notification_id, recipient_phone, channel, template_name, payload, status, response_message
            ) VALUES (?, ?, 'whatsapp', ?, ?, 'gagal', ?)
        """, (
            notification_id,
            recipient_phone or "TIDAK_ADA",
            template_name,
            json.dumps({"body": message_text, "raw_phone": recipient_phone}, ensure_ascii=False),
            err_msg
        ))
        return {
            "success": False,
            "status": "gagal",
            "message": err_msg
        }

    wa_link = create_whatsapp_link(normalized_phone, message_text)

    # Mode Pengujian (Simulasi Aman)
    if Config.WHATSAPP_TEST_MODE:
        payload_data = {
            "mode": "SIMULASI_PENGUJIAN",
            "to": normalized_phone,
            "template": template_name,
            "body": message_text,
            "wa_link": wa_link
        }
        log_query = """
            INSERT INTO notification_delivery_logs (
                notification_id, recipient_phone, channel, template_name, payload, status, response_message
            ) VALUES (?, ?, 'whatsapp', ?, ?, 'simulasi', ?)
        """
        response_msg = f"[MODE SIMULASI] Pesan tervalidasi & siap dikirim ke {normalized_phone} (WhatsApp Test Mode aktif, tidak memotong pulsa/gateway)."
        execute_db(log_query, (
            notification_id,
            normalized_phone,
            template_name,
            json.dumps(payload_data, ensure_ascii=False),
            response_msg
        ))
        return {
            "success": True,
            "status": "simulasi",
            "message": response_msg,
            "phone": normalized_phone,
            "wa_link": wa_link
        }

    # Mode Produksi (Kirim ke WhatsApp Cloud API Resmi)
    if not Config.WHATSAPP_PHONE_NUMBER_ID or not Config.WHATSAPP_ACCESS_TOKEN:
        err_msg = "WhatsApp Cloud API belum dikonfigurasi (PHONE_NUMBER_ID atau ACCESS_TOKEN kosong di .env)."
        payload_data = {"to": normalized_phone, "body": message_text}
        execute_db("""
            INSERT INTO notification_delivery_logs (
                notification_id, recipient_phone, channel, template_name, payload, status, response_message
            ) VALUES (?, ?, 'whatsapp', ?, ?, 'gagal', ?)
        """, (
            notification_id,
            normalized_phone,
            template_name,
            json.dumps(payload_data, ensure_ascii=False),
            err_msg
        ))
        return {
            "success": False,
            "status": "gagal",
            "message": err_msg
        }

    url = f"{Config.WHATSAPP_API_URL}/{Config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": normalized_phone,
        "type": "text",
        "text": {"preview_url": False, "body": message_text}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        res_json = response.json()
        if response.status_code in (200, 201):
            success_msg = f"Berhasil terkirim via WhatsApp Cloud API. ID Pesan: {res_json.get('messages', [{}])[0].get('id', 'N/A')}"
            execute_db("""
                INSERT INTO notification_delivery_logs (
                    notification_id, recipient_phone, channel, template_name, payload, status, response_message
                ) VALUES (?, ?, 'whatsapp', ?, ?, 'sukses', ?)
            """, (
                notification_id,
                normalized_phone,
                template_name,
                json.dumps(payload, ensure_ascii=False),
                success_msg
            ))
            return {"success": True, "status": "sukses", "message": success_msg, "phone": normalized_phone, "wa_link": wa_link}
        else:
            err_detail = res_json.get("error", {}).get("message", response.text)
            fail_msg = f"Gagal dari WhatsApp Cloud API: {err_detail}"
            execute_db("""
                INSERT INTO notification_delivery_logs (
                    notification_id, recipient_phone, channel, template_name, payload, status, response_message
                ) VALUES (?, ?, 'whatsapp', ?, ?, 'gagal', ?)
            """, (
                notification_id,
                normalized_phone,
                template_name,
                json.dumps(payload, ensure_ascii=False),
                fail_msg
            ))
            return {"success": False, "status": "gagal", "message": fail_msg, "wa_link": wa_link}
    except Exception as e:
        exception_msg = f"Koneksi ke WhatsApp Cloud API gagal: {str(e)}"
        execute_db("""
            INSERT INTO notification_delivery_logs (
                notification_id, recipient_phone, channel, template_name, payload, status, response_message
            ) VALUES (?, ?, 'whatsapp', ?, ?, 'gagal', ?)
        """, (
            notification_id,
            normalized_phone,
            template_name,
            json.dumps(payload, ensure_ascii=False),
            exception_msg
        ))
        return {"success": False, "status": "gagal", "message": exception_msg, "wa_link": wa_link}

def run_test_scenario(scenario_type, phone=None, custom_msg=None):
    """
    Menjalankan pengujian skenario WhatsApp spesifik:
    1: notifikasi_jadwal
    2: perubahan_jadwal
    3: pengumuman_operasional
    4: nomor_tidak_valid
    5: kegagalan_koneksi
    """
    target_phone = phone or "081298765401"
    if scenario_type == "notifikasi_jadwal":
        msg = custom_msg or format_schedule_notification("Naufal Pratama", "Sarah Nurhaliza, S.Pd.", "Matematika", "2026-11-10", "16:00", "17:30", "Pertemuan 1 (1)")
        return send_whatsapp_message(target_phone, msg, template_name="notifikasi_jadwal")

    elif scenario_type == "perubahan_jadwal":
        msg = custom_msg or format_schedule_reschedule("Kevin Ardiansyah", "Budi Santoso, M.Sc.", "Bahasa Inggris", "2026-11-10", "2026-11-12", "16:30", "Mentor menghadiri seminar kampus")
        return send_whatsapp_message(target_phone, msg, template_name="perubahan_jadwal")

    elif scenario_type == "operasional":
        msg = custom_msg or format_operational_announcement("Jadwal Libur Bersama Nasional", "Diberitahukan kepada seluruh siswa dan wali bahwa kegiatan les privat pada tanggal merah diliburkan dan akan diganti pada jadwal pengganti.")
        return send_whatsapp_message(target_phone, msg, template_name="pengumuman_operasional")

    elif scenario_type == "nomor_tidak_valid":
        return send_whatsapp_message("123", "Pesan uji untuk nomor tidak valid", template_name="uji_invalid")

    elif scenario_type == "kegagalan_koneksi":
        # Simulasi kegagalan koneksi API
        err_msg = "Koneksi ke WhatsApp Cloud API gagal: HTTPSConnectionPool(host='graph.facebook.com', port=443): Max retries exceeded"
        execute_db("""
            INSERT INTO notification_delivery_logs (
                recipient_phone, channel, template_name, payload, status, response_message
            ) VALUES (?, 'whatsapp', 'uji_kegagalan_api', ?, 'gagal', ?)
        """, (
            normalize_phone_number(target_phone) or "6281298765401",
            json.dumps({"simulated_failure": True}),
            err_msg
        ))
        return {
            "success": False,
            "status": "gagal",
            "message": err_msg
        }

    else:
        msg = custom_msg or "Pesan pengujian umum DESI PRIVAT"
        return send_whatsapp_message(target_phone, msg, template_name="uji_umum")

def get_delivery_logs(limit=50):
    """Mengambil riwayat log pengiriman notifikasi WhatsApp."""
    query = """
        SELECT l.id, l.notification_id, l.recipient_phone, l.channel, l.template_name,
               l.payload, l.status, l.response_message, l.created_at,
               n.title as notif_title
        FROM notification_delivery_logs l
        LEFT JOIN notifications n ON l.notification_id = n.id
        ORDER BY l.created_at DESC
        LIMIT ?
    """
    return query_db(query, (limit,))
