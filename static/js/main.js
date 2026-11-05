/**
 * DESI PRIVAT - Main JavaScript File
 * Mengelola interaktivitas UI:
 * - Toggle navigasi mobile
 * - Show/Hide password
 * - Modal dialogs
 * - Deteksi bentrokan jadwal dinamis (AJAX/Fetch)
 * - Helper pengujian akun cepat
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Toggle Sidebar & Drawer Mobile/Tablet (Responsif Modern)
  const toggleBtn = document.getElementById("mobileToggleBtn");
  const sidebar = document.getElementById("sidebar");
  const closeBtn = document.getElementById("sidebarCloseBtn");
  const backdrop = document.getElementById("sidebarBackdrop");

  function openSidebar() {
    if (sidebar) sidebar.classList.add("show");
    if (backdrop) backdrop.classList.add("active");
    if (window.innerWidth <= 1023) {
      document.body.style.overflow = "hidden";
    }
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("show");
    if (backdrop) backdrop.classList.remove("active");
    document.body.style.overflow = "";
  }

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (sidebar.classList.contains("show")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", closeSidebar);
    }

    if (backdrop) {
      backdrop.addEventListener("click", closeSidebar);
    }

    // Tutup drawer otomatis setelah klik tautan menu di layar tablet & smartphone
    sidebar.querySelectorAll(".sidebar-nav a").forEach(link => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 1023) {
          closeSidebar();
        }
      });
    });

    // Menangani resize window: jika kembali ke desktop (>1023px), reset overflow & drawer
    window.addEventListener("resize", () => {
      if (window.innerWidth > 1023) {
        closeSidebar();
      }
    });
  }

  // 2. Toggle Tampilkan / Sembunyikan Password
  const togglePwBtn = document.getElementById("togglePasswordBtn");
  const pwInput = document.getElementById("passwordInput");
  if (togglePwBtn && pwInput) {
    togglePwBtn.addEventListener("click", () => {
      const isPassword = pwInput.type === "password";
      pwInput.type = isPassword ? "text" : "password";
      togglePwBtn.innerHTML = isPassword ? "👁️ Sembunyikan" : "👁️ Tampilkan";
    });
  }

  // 4. Modal Dialog Handler
  window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.add("active");
      document.body.style.overflow = "hidden";
      const bodyEl = modal.querySelector(".modal-body");
      if (bodyEl) {
        bodyEl.scrollTop = 0;
      }
    }
  };

  window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("active");
      const hasOther = document.querySelector(".modal-overlay.active");
      if (!hasOther) {
        document.body.style.overflow = "";
      }
    }
  };

  // Tutup modal jika klik overlay latar belakang
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
        const hasOther = document.querySelector(".modal-overlay.active");
        if (!hasOther) {
          document.body.style.overflow = "";
        }
      }
    });
  });

  // Tutup modal atau drawer dengan tombol keyboard Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const activeModals = document.querySelectorAll(".modal-overlay.active");
      if (activeModals.length > 0) {
        activeModals.forEach(m => m.classList.remove("active"));
        document.body.style.overflow = "";
      }
      if (sidebar && sidebar.classList.contains("show")) {
        closeSidebar();
      }
    }
  });

  // 5. Deteksi Bentrokan Jadwal Dinamis (Frontend live check)
  const scheduleForm = document.getElementById("scheduleForm");
  if (scheduleForm) {
    const mentorSelect = scheduleForm.querySelector("[name='mentor_id']");
    const studentSelect = scheduleForm.querySelector("[name='student_id']");
    const dateInput = scheduleForm.querySelector("[name='schedule_date']");
    const timeInput = scheduleForm.querySelector("[name='start_time']");
    const durationInput = scheduleForm.querySelector("[name='duration_minutes']");
    const conflictAlertBox = document.getElementById("conflictAlertBox");

    async function checkConflictLive() {
      if (!mentorSelect || !studentSelect || !dateInput || !timeInput || !conflictAlertBox) return;

      const mId = mentorSelect.value;
      const sId = studentSelect.value;
      const sDate = dateInput.value;
      const sTime = timeInput.value;
      const duration = durationInput ? durationInput.value : 90;

      if (!mId || !sId || !sDate || !sTime) {
        conflictAlertBox.style.display = "none";
        return;
      }

      try {
        const resp = await fetch("/admin/api/check-conflict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mentor_id: mId,
            student_id: sId,
            schedule_date: sDate,
            start_time: sTime,
            duration: duration
          })
        });
        const data = await resp.json();
        if (data.has_conflict) {
          conflictAlertBox.className = "alert-box alert-danger";
          conflictAlertBox.innerHTML = `⚠️ <strong>Peringatan Bentrokan Jadwal:</strong> ${data.message}`;
          conflictAlertBox.style.display = "block";
        } else {
          conflictAlertBox.className = "alert-box alert-success";
          conflictAlertBox.innerHTML = `✅ <strong>Waktu Aman:</strong> ${data.message}`;
          conflictAlertBox.style.display = "block";
        }
      } catch (err) {
        console.error("Gagal memeriksa bentrokan:", err);
      }
    }

    [mentorSelect, studentSelect, dateInput, timeInput, durationInput].forEach(el => {
      if (el) el.addEventListener("change", checkConflictLive);
    });
  }

  // 6. Modal Pergantian Mentor Dinamis
  window.prepareMentorReplacementModal = async function(scheduleId, currentMentorName) {
    const modal = document.getElementById("replacementModal");
    const schedIdInput = document.getElementById("replaceScheduleId");
    const currentMentorSpan = document.getElementById("currentMentorSpan");
    const mentorSelect = document.getElementById("replacementMentorSelect");

    if (!modal || !schedIdInput || !mentorSelect) return;

    schedIdInput.value = scheduleId;
    if (currentMentorSpan) currentMentorSpan.innerText = currentMentorName;

    mentorSelect.innerHTML = "<option value=''>-- Memuat daftar mentor yang memenuhi syarat... --</option>";
    window.openModal("replacementModal");

    try {
      const resp = await fetch(`/admin/api/eligible-replacements/${scheduleId}`);
      const list = await resp.json();
      mentorSelect.innerHTML = "<option value=''>-- Pilih Mentor Pengganti --</option>";
      list.forEach(item => {
        const m = item.mentor;
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.disabled = item.has_conflict;
        opt.innerText = `${m.full_name} (${m.expertise}) ${item.has_conflict ? ' [BENTROK]' : ' [TERSEDIA]'}`;
        mentorSelect.appendChild(opt);
      });
    } catch (e) {
      mentorSelect.innerHTML = "<option value=''>Gagal memuat mentor pengganti</option>";
    }
  };
});
