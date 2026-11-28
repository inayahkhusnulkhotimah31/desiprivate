/**
 * DESI PRIVAT - Main JavaScript File
 * Mengelola interaktivitas UI:
 * - Modal dialogs (Global & Immediate availability)
 * - Toggle navigasi mobile
 * - Show/Hide password
 * - Deteksi bentrokan jadwal dinamis (AJAX/Fetch)
 * - Transisi halaman & inisialisasi Scroll-Craft
 */

// ============================================================================
// 1. MODAL DIALOG HANDLERS (DEFINED AT TOP-LEVEL FOR IMMEDIATE GLOBAL AVAILABILITY)
// ============================================================================
window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
    const bodyEl = modal.querySelector(".modal-body");
    if (bodyEl) {
      bodyEl.scrollTop = 0;
    }
    const card = modal.querySelector(".modal-dialog, .modal-content");
    if (card && window.gsap) {
      window.gsap.fromTo(
        card,
        { opacity: 0, scale: 0.95, y: 8 },
        { opacity: 1, scale: 1, y: 0, duration: 0.24, ease: "power3.out", clearProps: "transform" }
      );
    }
  }
};

window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    const finishClose = () => {
      modal.classList.remove("active");
      const hasOther = document.querySelector(".modal-overlay.active");
      if (!hasOther) {
        document.body.style.overflow = "";
      }
    };
    const card = modal.querySelector(".modal-dialog, .modal-content");
    if (card && window.gsap && modal.classList.contains("active")) {
      window.gsap.to(card, {
        opacity: 0,
        scale: 0.96,
        duration: 0.18,
        ease: "power2.in",
        onComplete: () => {
          card.style.opacity = "";
          card.style.transform = "";
          finishClose();
        },
      });
    } else {
      finishClose();
    }
  }
};

function initMain() {
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

  // 2. Toggle Tampilkan / Sembunyikan Password (Animated Blurred Eye Swap)
  const togglePwBtn = document.getElementById("togglePasswordBtn");
  const pwInput = document.getElementById("passwordInput");
  if (togglePwBtn && pwInput) {
    togglePwBtn.addEventListener("click", () => {
      const isPassword = pwInput.type === "password";
      pwInput.type = isPassword ? "text" : "password";
      togglePwBtn.classList.toggle("is-revealed", isPassword);
      togglePwBtn.setAttribute("aria-pressed", isPassword ? "true" : "false");
      togglePwBtn.setAttribute("aria-label", isPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi");
      togglePwBtn.setAttribute("title", isPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi");
    });
  }

  // 3. Landing Mobile Menu Toggle
  const landingToggle = document.getElementById("landingMobileToggle");
  const landingMenu = document.getElementById("landingNavMenu");
  if (landingToggle && landingMenu) {
    landingToggle.addEventListener("click", () => {
      const opened = landingMenu.classList.toggle("is-open");
      landingToggle.setAttribute("aria-expanded", opened ? "true" : "false");
    });
    landingMenu.querySelectorAll("a").forEach(a => {
      a.addEventListener("click", () => landingMenu.classList.remove("is-open"));
    });
  }

  // 4. Floating Transparent-to-Glass Navbar State
  const heroNav = document.querySelector(".dp-nav-bar.dp-nav-hero");
  const syncHeroNav = () => {
    if (!heroNav) return;
    heroNav.classList.toggle("is-scrolled", (window.scrollY || 0) > 40);
  };
  syncHeroNav();

  // 5. Mount Scroll-Craft + Lenis + Native CSS Scroll-Driven Animations
  const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let scApi = null;
  if (window.ScrollCraft && document.querySelector("[data-sc-act]")) {
    scApi = window.ScrollCraft.mount(document);
  }

  if (!prefersReduced && window.Lenis && document.body.classList.contains("dp-landing-body")) {
    const lenis = new window.Lenis({
      duration: 1.15,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      wheelMultiplier: 0.95,
      autoRaf: true,
    });
    window.__dpLenis = lenis;
    lenis.on("scroll", () => {
      syncHeroNav();
      if (scApi && typeof scApi.read === "function") {
        scApi.read();
      }
      if (window.ScrollTrigger) {
        window.ScrollTrigger.update();
      }
    });
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        const id = anchor.getAttribute("href");
        if (!id || id === "#") return;
        const target = document.querySelector(id);
        if (!target) return;
        e.preventDefault();
        lenis.scrollTo(target, { offset: -72, duration: 1.2 });
      });
    });
  } else {
    window.addEventListener("scroll", syncHeroNav, { passive: true });
  }

  // 5b. Interactive Portal Tabs, FAQ Accordion & Program Detail Drawer
  const portalTabs = document.querySelectorAll(".dp-portal-tab");
  if (portalTabs.length > 0) {
    portalTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const targetId = tab.getAttribute("data-portal-target");
        portalTabs.forEach((t) => {
          t.classList.remove("is-active");
          t.setAttribute("aria-selected", "false");
        });
        document.querySelectorAll(".dp-portal-pane").forEach((pane) => {
          pane.classList.remove("is-active");
          pane.setAttribute("hidden", "");
        });
        tab.classList.add("is-active");
        tab.setAttribute("aria-selected", "true");
        const activePane = targetId ? document.getElementById(targetId) : null;
        if (activePane) {
          activePane.removeAttribute("hidden");
          activePane.classList.add("is-active");
        }
      });
    });
  }

  document.querySelectorAll(".dp-faq-trigger").forEach((btn) => {
    btn.addEventListener("click", () => {
      const expanded = btn.getAttribute("aria-expanded") === "true";
      const panel = btn.nextElementSibling;
      btn.setAttribute("aria-expanded", expanded ? "false" : "true");
      if (panel) panel.classList.toggle("is-open", !expanded);
    });
  });

  const drawerPanel = document.getElementById("dpProgramDrawer");
  const drawerBackdrop = document.getElementById("dpDrawerBackdrop");
  const closeDrawer = () => {
    if (!drawerPanel || !drawerBackdrop) return;
    drawerPanel.classList.remove("is-open");
    drawerBackdrop.classList.remove("is-open");
    drawerPanel.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };
  if (drawerPanel && drawerBackdrop) {
    document.querySelectorAll(".dp-prog-open-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const titleEl = document.getElementById("dpDrawerTitle");
        const descEl = document.getElementById("dpDrawerDesc");
        const focusEl = document.getElementById("dpDrawerFocus");
        const cadEl = document.getElementById("dpDrawerCadence");
        if (titleEl) titleEl.textContent = btn.getAttribute("data-prog-title") || "Program Bimbingan";
        if (descEl) descEl.textContent = btn.getAttribute("data-prog-desc") || "";
        if (focusEl) focusEl.textContent = btn.getAttribute("data-prog-focus") || "";
        if (cadEl) cadEl.textContent = btn.getAttribute("data-prog-cadence") || "";
        drawerPanel.classList.add("is-open");
        drawerBackdrop.classList.add("is-open");
        drawerPanel.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
      });
    });
    drawerBackdrop.addEventListener("click", closeDrawer);
    const closeBtn1 = document.getElementById("dpDrawerCloseBtn");
    const closeBtn2 = document.getElementById("dpDrawerDismissBtn");
    const consultBtn = document.getElementById("dpDrawerConsultBtn");
    if (closeBtn1) closeBtn1.addEventListener("click", closeDrawer);
    if (closeBtn2) closeBtn2.addEventListener("click", closeDrawer);
    if (consultBtn) {
      consultBtn.addEventListener("click", (e) => {
        const href = consultBtn.getAttribute("href") || "";
        closeDrawer();
        if (href.startsWith("#")) {
          e.preventDefault();
          const target = document.querySelector(href);
          if (target) {
            if (window.__dpLenis && typeof window.__dpLenis.scrollTo === "function") {
              window.__dpLenis.scrollTo(target, { offset: -40, duration: 1.0 });
            } else {
              target.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth" });
            }
          }
        }
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && drawerPanel.classList.contains("is-open")) {
        closeDrawer();
      }
    });
  }

  // 5c. Achievement Poster Lightbox Modal (.dp-poster-open-btn)
  document.querySelectorAll(".dp-poster-open-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const src = btn.getAttribute("data-poster-src") || "";
      const ttl = btn.getAttribute("data-poster-title") || "Pencapaian Siswa";
      const imgEl = document.getElementById("dpPosterModalImg");
      const ttlEl = document.getElementById("dpPosterModalTitle");
      if (imgEl && src) imgEl.src = src;
      if (ttlEl) ttlEl.textContent = ttl;
      window.openModal("dpPosterModal");
    });
  });

  window.addEventListener("load", () => {
    if (scApi && typeof scApi.layout === "function") scApi.layout();
  });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => {
      if (scApi && typeof scApi.layout === "function") scApi.layout();
    });
  }

  // 6. Dynamic Page Transition: Closing-Gate Curtain for /login, Clean Fade Otherwise
  if (!prefersReduced) {
    document.addEventListener("click", (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = e.target.closest("a[href]");
      if (!link) return;
      const href = link.getAttribute("href") || "";
      if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("mailto:") || href.startsWith("tel:")) return;
      if (link.target === "_blank" || link.hasAttribute("download")) return;
      let destPath = "";
      try {
        const dest = new URL(link.href, window.location.origin);
        if (dest.origin !== window.location.origin || (dest.pathname === window.location.pathname && dest.search === window.location.search)) return;
        destPath = dest.pathname || "";
      } catch (_) {
        return;
      }
      e.preventDefault();
      if (destPath === "/login" || destPath.endsWith("/login")) {
        let curtain = document.getElementById("dpGateCurtain");
        if (!curtain) {
          curtain = document.createElement("div");
          curtain.id = "dpGateCurtain";
          curtain.className = "dp-gate-curtain";
          curtain.innerHTML = '<div class="dp-gate-door dp-gate-door--left"></div><div class="dp-gate-door dp-gate-door--right"></div>';
          document.body.appendChild(curtain);
        }
        window.requestAnimationFrame(() => curtain.classList.add("is-closing"));
        window.setTimeout(() => {
          window.location.href = link.href;
        }, 290);
        return;
      }
      document.body.classList.add("dp-page-leaving");
      window.setTimeout(() => {
        window.location.href = link.href;
      }, 170);
    });
  }

  // 3. Modal Overlay & Keyboard Event Listeners
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        window.closeModal(overlay.id);
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

  // 4. Deteksi Bentrokan Jadwal Dinamis (Frontend live check)
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
        const csrfInput = scheduleForm.querySelector("[name='csrf_token']");
        const headers = { "Content-Type": "application/json" };
        if (csrfInput && csrfInput.value) {
          headers["X-CSRF-Token"] = csrfInput.value;
        }
        const resp = await fetch("/admin/api/check-conflict", {
          method: "POST",
          headers,
          body: JSON.stringify({
            mentor_id: mId,
            student_id: sId,
            schedule_date: sDate,
            start_time: sTime,
            duration: duration
          })
        });
        const data = await resp.json();
        conflictAlertBox.replaceChildren();
        const strong = document.createElement("strong");
        if (data.has_conflict) {
          conflictAlertBox.className = "alert-box alert-danger";
          strong.textContent = "Peringatan Bentrokan Jadwal: ";
        } else {
          conflictAlertBox.className = "alert-box alert-success";
          strong.textContent = "Waktu Aman: ";
        }
        conflictAlertBox.appendChild(strong);
        conflictAlertBox.appendChild(document.createTextNode(String(data.message || "")));
        conflictAlertBox.style.display = "block";
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
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMain);
} else {
  initMain();
}
