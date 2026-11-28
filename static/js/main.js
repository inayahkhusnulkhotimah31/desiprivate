/**
 * DESI PRIVAT - Lightweight Core UI Script (V12)
 * Zero heavy vendor dependencies for instant load & smooth 60fps interaction:
 * - Viewport-centered modals & drawers
 * - Responsive sidebar & landing mobile menu
 * - Animated password eye swap
 * - Seamless Login Closing-Gate (Left photo + Right empty white panel, text after)
 * - Live schedule conflict & mentor replacement handlers
 */

let dpLockedScrollY = 0;
let dpIsScrollLocked = false;

function lockPageScroll() {
  if (dpIsScrollLocked) return;
  dpLockedScrollY = window.scrollY || window.pageYOffset || 0;
  dpIsScrollLocked = true;
  document.documentElement.classList.add("dp-scroll-lock");
  document.body.style.position = "fixed";
  document.body.style.top = `-${dpLockedScrollY}px`;
  document.body.style.left = "0";
  document.body.style.right = "0";
  document.body.style.width = "100%";
  document.body.style.overflow = "hidden";
}

function unlockPageScroll() {
  if (document.querySelector(".modal-overlay.active, .dp-drawer-panel.is-open, .dp-mobile-menu-sheet.is-open")) {
    return;
  }
  if (!dpIsScrollLocked) {
    document.documentElement.classList.remove("dp-scroll-lock");
    document.body.style.overflow = "";
    return;
  }
  dpIsScrollLocked = false;
  document.documentElement.classList.remove("dp-scroll-lock");
  const prevBehavior = document.documentElement.style.scrollBehavior;
  document.documentElement.style.scrollBehavior = "auto";
  document.body.style.position = "";
  document.body.style.top = "";
  document.body.style.left = "";
  document.body.style.right = "";
  document.body.style.width = "";
  document.body.style.overflow = "";
  window.scrollTo(0, dpLockedScrollY);
  document.documentElement.style.scrollBehavior = prevBehavior;
}

window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  modal.classList.add("active");
  lockPageScroll();
  const bodyEl = modal.querySelector(".modal-body");
  if (bodyEl) bodyEl.scrollTop = 0;
};

window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  modal.classList.remove("active");
  unlockPageScroll();
};

let dpOpenGateTimer = null;

function isMobileFastMode() {
  return Boolean(
    window.matchMedia &&
      (window.matchMedia("(max-width: 1024px)").matches ||
        window.matchMedia("(hover: none) and (pointer: coarse)").matches)
  );
}

function mountClosingGate() {
  let curtain = document.getElementById("dpGateCurtain");
  if (!curtain) {
    const photoUrl =
      (document.body && document.body.getAttribute("data-login-photo")) ||
      "/static/images/client/galeri_02.webp";
    curtain = document.createElement("div");
    curtain.id = "dpGateCurtain";
    curtain.className = "dp-gate-curtain";
    curtain.innerHTML =
      '<div class="dp-gate-door dp-gate-door--left">' +
        '<img class="dp-gate-door-photo" src="' + photoUrl + '" alt="">' +
        '<div class="dp-gate-door-fade"></div>' +
      '</div>' +
      '<div class="dp-gate-door dp-gate-door--right"></div>';
    document.body.appendChild(curtain);
  }
  window.requestAnimationFrame(() => curtain.classList.add("is-closing"));
  return curtain;
}

function cleanupGateCurtain() {
  const curtain = document.getElementById("dpGateCurtain");
  if (curtain) curtain.remove();
  const openGate = document.getElementById("dpOpenGate");
  if (openGate) {
    openGate.classList.remove("is-opening");
    delete openGate.dataset.animating;
  }
  if (dpOpenGateTimer) {
    window.clearTimeout(dpOpenGateTimer);
    dpOpenGateTimer = null;
  }
  document.documentElement.classList.remove("dp-opening-gate");
  document.body.classList.remove("dp-page-leaving", "dp-login-leaving");
  if (!document.querySelector(".modal-overlay.active, .dp-drawer-panel.is-open")) {
    document.body.style.overflow = "";
  }
}

function playOpenGateAnimation() {
  const openGate = document.getElementById("dpOpenGate");
  const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!openGate || reduced || isMobileFastMode()) {
    document.documentElement.classList.remove("dp-opening-gate");
    return;
  }
  if (openGate.dataset.animating === "1") return;
  openGate.dataset.animating = "1";
  document.documentElement.classList.add("dp-opening-gate");
  openGate.classList.remove("is-opening");
  // Force layout so browser paints closed doors on frame 0 before sliding open
  void openGate.offsetWidth;
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      openGate.classList.add("is-opening");
    });
  });
  if (dpOpenGateTimer) window.clearTimeout(dpOpenGateTimer);
  dpOpenGateTimer = window.setTimeout(() => {
    document.documentElement.classList.remove("dp-opening-gate");
    openGate.classList.remove("is-opening");
    delete openGate.dataset.animating;
    dpOpenGateTimer = null;
  }, 420);
}

let dpLoginSubmitting = false;

window.addEventListener("pageshow", (e) => {
  const isLanding = document.body && document.body.classList.contains("dp-landing-body") && !document.body.classList.contains("dp-login-page");
  const openGate = document.getElementById("dpOpenGate");
  const shouldKeepOpening = !isMobileFastMode() && Boolean(openGate) && document.documentElement.classList.contains("dp-opening-gate");

  // Always remove any leftover closing curtain without interrupting an active opening gate
  const curtain = document.getElementById("dpGateCurtain");
  if (curtain) curtain.remove();
  document.body.classList.remove("dp-page-leaving", "dp-login-leaving");
  if (!document.querySelector(".modal-overlay.active, .dp-drawer-panel.is-open")) {
    document.body.style.overflow = "";
  }

  if (isMobileFastMode()) {
    document.documentElement.classList.remove("dp-opening-gate");
    return;
  }

  let fromLoginBack = false;
  if (isLanding) {
    try {
      const leftTs = Number(sessionStorage.getItem("dp_left_login") || "0");
      if (leftTs && Date.now() - leftTs < 4000) {
        sessionStorage.removeItem("dp_left_login");
        fromLoginBack = true;
      } else if (leftTs) {
        sessionStorage.removeItem("dp_left_login");
      }
    } catch (_) {}
  }

  if (openGate && (shouldKeepOpening || (isLanding && fromLoginBack)) && openGate.dataset.animating !== "1") {
    playOpenGateAnimation();
  }
});

window.addEventListener("pagehide", () => {
  cleanupGateCurtain();
  if (!isMobileFastMode() && document.body && document.body.classList.contains("dp-login-page") && !dpLoginSubmitting) {
    try { sessionStorage.setItem("dp_left_login", String(Date.now())); } catch (_) {}
  }
});

function initMain() {
  const isLanding = document.body && document.body.classList.contains("dp-landing-body") && !document.body.classList.contains("dp-login-page");
  const openGate = document.getElementById("dpOpenGate");
  const hasOpeningFlag = !isMobileFastMode() && Boolean(openGate) && document.documentElement.classList.contains("dp-opening-gate");
  if (!hasOpeningFlag) {
    cleanupGateCurtain();
  } else {
    const curtain = document.getElementById("dpGateCurtain");
    if (curtain) curtain.remove();
    playOpenGateAnimation();
  }
  if (document.body && document.body.classList.contains("dp-login-page")) {
    dpLoginSubmitting = false;
    try {
      sessionStorage.removeItem("dp_left_login");
      sessionStorage.removeItem("dp_gate_open");
    } catch (_) {}
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelectorAll("form").forEach((f) => {
      f.addEventListener("submit", (e) => {
        if (dpLoginSubmitting) return;
        if (typeof f.checkValidity === "function" && !f.checkValidity()) return;
        dpLoginSubmitting = true;
        if (!reduced && !isMobileFastMode()) {
          e.preventDefault();
          document.body.classList.add("dp-login-leaving");
          try { sessionStorage.setItem("dp_gate_open", "1"); } catch (_) {}
          window.setTimeout(() => {
            f.submit();
          }, 140);
        }
      });
    });
  } else if (!isLanding) {
    try { sessionStorage.removeItem("dp_left_login"); } catch (_) {}
  }
  // 0. Normalize /landing -> / so Landing Page always displays root URL
  if (window.location.pathname === "/landing" && window.history && typeof window.history.replaceState === "function") {
    window.history.replaceState(null, "", "/" + window.location.search + window.location.hash);
  }

  // 0b. Global Anti-Drag & Anti-Save Image Protection
  document.querySelectorAll("img").forEach((img) => {
    img.setAttribute("draggable", "false");
  });
  document.addEventListener("dragstart", (e) => {
    if (e.target && (e.target.tagName === "IMG" || e.target.closest("img"))) {
      e.preventDefault();
    }
  });
  document.addEventListener("contextmenu", (e) => {
    if (
      e.target &&
      (e.target.tagName === "IMG" ||
        e.target.closest(".dp-sophie-inner, .dp-poster-modal-frame, .dp-hero-mosaic-cell, .dp-closing-thumb-wrap, .dp-login-photo"))
    ) {
      e.preventDefault();
    }
  });

  // 1. Sidebar & Drawer Mobile/Tablet
  const toggleBtn = document.getElementById("mobileToggleBtn");
  const sidebar = document.getElementById("sidebar");
  const closeBtn = document.getElementById("sidebarCloseBtn");
  const backdrop = document.getElementById("sidebarBackdrop");

  function openSidebar() {
    if (sidebar) sidebar.classList.add("show");
    if (backdrop) backdrop.classList.add("active");
    if (window.innerWidth <= 1023) document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("show");
    if (backdrop) backdrop.classList.remove("active");
    if (!document.querySelector(".modal-overlay.active")) document.body.style.overflow = "";
  }

  if (sidebar) {
    if (toggleBtn) {
      toggleBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (sidebar.classList.contains("show")) closeSidebar();
        else openSidebar();
      });
    }
    if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
    if (backdrop) backdrop.addEventListener("click", closeSidebar);
    sidebar.querySelectorAll(".sidebar-nav a").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 1023) closeSidebar();
      });
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 1023) closeSidebar();
    });
  }

  // 2. Animated Password Eye Toggle (Blurred Icon Swap)
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

  // 3. Floating Navbar, Top Scroll Progress & Icon-Only Back-to-Top (Passive rAF-free scroll)
  const heroNav = document.querySelector(".dp-nav-bar.dp-nav-hero");
  const floatBar = document.getElementById("dpFloatBar");
  const progressBar = document.getElementById("dpScrollProgress");
  let scrollTick = false;

  const syncScrollUI = () => {
    scrollTick = false;
    if (dpIsScrollLocked) return;
    const y = window.scrollY || 0;
    if (heroNav) heroNav.classList.toggle("is-scrolled", y > 48);
    if (floatBar) floatBar.classList.toggle("is-visible", y > 360);
    if (progressBar) {
      const docH = document.documentElement.scrollHeight - window.innerHeight;
      const pct = docH > 0 ? Math.min(1, Math.max(0, y / docH)) : 0;
      progressBar.style.transform = `scaleX(${pct})`;
    }
  };

  syncScrollUI();
  window.addEventListener("scroll", () => {
    if (!scrollTick) {
      scrollTick = true;
      window.requestAnimationFrame(syncScrollUI);
    }
  }, { passive: true });

  const topBtn = document.getElementById("dpFloatTopBtn");
  if (topBtn) {
    topBtn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // 5. Program Detail Drawer (Viewport-Fixed, locks background scroll on mobile)
  const drawer = document.getElementById("dpProgramDrawer");
  const drawerBd = document.getElementById("dpDrawerBackdrop");
  const drawerClose = document.getElementById("dpDrawerCloseBtn");
  const drawerDismiss = document.getElementById("dpDrawerDismissBtn");
  if (drawer && drawerBd) {
    const closeDrawer = () => {
      drawer.classList.remove("is-open");
      drawerBd.classList.remove("is-open");
      drawer.setAttribute("aria-hidden", "true");
      drawerBd.setAttribute("aria-hidden", "true");
      unlockPageScroll();
    };
    const openProgramDrawer = (btn) => {
      if (!btn) return;
      const titleEl = document.getElementById("dpDrawerTitle");
      const descEl = document.getElementById("dpDrawerDesc");
      const focusEl = document.getElementById("dpDrawerFocus");
      const leadEl = document.getElementById("dpDrawerCadenceLead");
      const cadEl = document.getElementById("dpDrawerCadence");
      if (titleEl) titleEl.textContent = btn.getAttribute("data-prog-title") || "Program Bimbingan";
      if (descEl) descEl.textContent = btn.getAttribute("data-prog-desc") || "";
      if (focusEl) {
        focusEl.textContent = "";
        const rawFocus = btn.getAttribute("data-prog-focus") || "";
        rawFocus.split("|").map((s) => s.trim()).filter(Boolean).forEach((item) => {
          const li = document.createElement("li");
          li.textContent = item;
          focusEl.appendChild(li);
        });
      }
      if (leadEl) {
        leadEl.textContent = btn.getAttribute("data-prog-cadence-lead") || "8 Sesi per periode, 90 menit per sesi";
      }
      if (cadEl) cadEl.textContent = btn.getAttribute("data-prog-cadence") || "";
      drawer.classList.add("is-open");
      drawerBd.classList.add("is-open");
      drawer.setAttribute("aria-hidden", "false");
      drawerBd.setAttribute("aria-hidden", "false");
      lockPageScroll();
      const bodyEl = drawer.querySelector(".dp-drawer-body");
      if (bodyEl) bodyEl.scrollTop = 0;
    };

    document.querySelectorAll(".dp-program-simple-card").forEach((card) => {
      const progBtn = card.querySelector(".dp-prog-open-btn");
      if (!progBtn) return;
      card.addEventListener("click", () => {
        openProgramDrawer(progBtn);
      });
      card.addEventListener("keydown", (e) => {
        if (e.target !== card) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openProgramDrawer(progBtn);
        }
      });
    });

    document.querySelectorAll(".dp-prog-open-btn").forEach((btn) => {
      if (btn.closest(".dp-program-simple-card")) return;
      btn.addEventListener("click", () => {
        openProgramDrawer(btn);
      });
    });
    if (drawerClose) drawerClose.addEventListener("click", closeDrawer);
    if (drawerDismiss) drawerDismiss.addEventListener("click", closeDrawer);
    drawerBd.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && drawer.classList.contains("is-open")) closeDrawer();
    });
  }

  // 6. Achievement Poster Lightbox Modal (Clickable full card + eye button)
  const openPosterModal = (trigger) => {
    if (!trigger) return;
    const src = trigger.getAttribute("data-poster-src") || "";
    const ttl = trigger.getAttribute("data-poster-title") || "Pencapaian Siswa";
    const imgEl = document.getElementById("dpPosterModalImg");
    const ttlEl = document.getElementById("dpPosterModalTitle");
    if (imgEl && src) imgEl.src = src;
    if (ttlEl) ttlEl.textContent = ttl;
    window.openModal("dpPosterModal");
  };

  document.querySelectorAll(".dp-sophie-card").forEach((card) => {
    const posterBtn = card.querySelector(".dp-poster-open-btn");
    if (!posterBtn) return;
    card.addEventListener("click", () => {
      openPosterModal(posterBtn);
    });
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openPosterModal(posterBtn);
      }
    });
  });

  document.querySelectorAll(".dp-poster-open-btn").forEach((btn) => {
    if (btn.closest(".dp-sophie-card")) return;
    btn.addEventListener("click", () => {
      openPosterModal(btn);
    });
  });

  // 7. Navigation Gate Transitions (Desktop only; instant on mobile for speed & reliability)
  const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.addEventListener("click", (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

    // 7a. Dashboard Brand Logo -> Logout + Return to Landing Page (Gate Close -> Gate Open on Desktop; instant on Mobile)
    const brandLogoutLink = e.target.closest("a.dp-brand-home-link[data-logout-url]");
    if (brandLogoutLink) {
      e.preventDefault();
      if (brandLogoutLink.dataset.loggingOut === "1") return;
      brandLogoutLink.dataset.loggingOut = "1";
      const logoutUrl = brandLogoutLink.getAttribute("data-logout-url") || "/logout";
      if (prefersReduced || isMobileFastMode()) {
        fetch(logoutUrl, { credentials: "same-origin", redirect: "follow" })
          .catch(() => {})
          .finally(() => {
            window.location.href = "/";
          });
        return;
      }
      mountClosingGate();
      try { sessionStorage.setItem("dp_gate_open", "1"); } catch (_) {}
      Promise.all([
        fetch(logoutUrl, { credentials: "same-origin", redirect: "follow" }).catch(() => {}),
        new Promise((resolve) => window.setTimeout(resolve, 230))
      ]).finally(() => {
        window.location.href = "/";
      });
      window.setTimeout(cleanupGateCurtain, 2400);
      return;
    }

    if (prefersReduced || isMobileFastMode()) return;

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

    if (destPath === "/login" || destPath.endsWith("/login")) {
      e.preventDefault();
      mountClosingGate();
      try { sessionStorage.setItem("dp_gate_arrived", "1"); } catch (_) {}
      window.setTimeout(() => {
        window.location.href = link.href;
      }, 210);
      window.setTimeout(cleanupGateCurtain, 1800);
      return;
    }

    // Login -> Home: fade out login texts first, then open gate cleanly on Landing Page
    if (document.body.classList.contains("dp-login-page") && (destPath === "/" || destPath === "/landing")) {
      e.preventDefault();
      document.body.classList.add("dp-login-leaving");
      try { sessionStorage.setItem("dp_gate_open", "1"); } catch (_) {}
      window.setTimeout(() => {
        window.location.href = "/";
      }, 140);
    }
  });

  // 8. Modal Overlay Backdrop, Touch Swipe-Down Dismiss (Mobile Thumb UX) & Escape Close
  const attachSwipeDismiss = (el, scrollChildSelector, onDismiss) => {
    if (!el) return;
    let startY = 0;
    let deltaY = 0;
    let tracking = false;
    el.addEventListener("touchstart", (e) => {
      if (!isMobileFastMode() || e.touches.length !== 1) return;
      const scroller = scrollChildSelector ? el.querySelector(scrollChildSelector) : null;
      if (scroller && scroller.scrollTop > 4) return;
      startY = e.touches[0].clientY;
      deltaY = 0;
      tracking = true;
    }, { passive: true });
    el.addEventListener("touchmove", (e) => {
      if (!tracking || e.touches.length !== 1) return;
      deltaY = e.touches[0].clientY - startY;
      if (deltaY > 8) {
        el.style.transition = "none";
        el.style.transform = `translateY(${Math.min(deltaY, 180)}px)`;
      }
    }, { passive: true });
    const finishSwipe = () => {
      if (!tracking) return;
      tracking = false;
      el.style.transition = "";
      el.style.transform = "";
      if (deltaY > 56) {
        onDismiss();
      }
    };
    el.addEventListener("touchend", finishSwipe, { passive: true });
    el.addEventListener("touchcancel", finishSwipe, { passive: true });
  };

  if (drawer && drawerBd) {
    drawerBd.addEventListener("touchmove", (e) => {
      if (e.target === drawerBd) e.preventDefault();
    }, { passive: false });
    attachSwipeDismiss(drawer, ".dp-drawer-body", () => {
      drawer.classList.remove("is-open");
      drawerBd.classList.remove("is-open");
      drawer.setAttribute("aria-hidden", "true");
      drawerBd.setAttribute("aria-hidden", "true");
      unlockPageScroll();
    });
  }

  // 8b. Dashboard Mobile Bottom-Sheet Menu (replaces clunky sidebar on mobile)
  const menuSheet = document.getElementById("dpMobileMenuSheet");
  const menuBackdrop = document.getElementById("dpMobileMenuBackdrop");
  const menuBody = document.getElementById("dpMobileMenuBody");
  const menuTriggers = document.querySelectorAll(".dp-mobile-menu-trigger");
  if (menuSheet && menuBackdrop && menuBody && menuTriggers.length > 0) {
    // Populate clean 2-column menu sheet from sidebar nav (100% RBAC parity)
    const sidebarNav = document.querySelector("#sidebar .sidebar-nav");
    if (sidebarNav && !menuBody.childElementCount) {
      const grid = document.createElement("div");
      grid.className = "dp-mobile-menu-grid";
      sidebarNav.querySelectorAll("a.nav-link").forEach((link) => {
        const tile = document.createElement("a");
        tile.href = link.getAttribute("href") || "#";
        tile.className = "dp-mobile-menu-tile" + (link.classList.contains("active") ? " is-active" : "");
        const iconNode = link.querySelector(".nav-icon");
        if (iconNode) {
          const ic = iconNode.cloneNode(true);
          ic.className = "dp-mobile-menu-tile-ic";
          tile.appendChild(ic);
        }
        const lbl = document.createElement("span");
        lbl.className = "dp-mobile-menu-tile-lbl";
        lbl.textContent = link.textContent.trim();
        tile.appendChild(lbl);
        grid.appendChild(tile);
      });
      menuBody.appendChild(grid);

      const logoutLink = document.querySelector("#sidebar .dp-fc-logout-link");
      if (logoutLink) {
        const foot = document.createElement("div");
        foot.className = "dp-mobile-menu-foot";
        const outBtn = document.createElement("a");
        outBtn.href = logoutLink.getAttribute("href") || "/logout";
        outBtn.className = "dp-mobile-menu-logout";
        outBtn.textContent = "Keluar dari Akun";
        foot.appendChild(outBtn);
        menuBody.appendChild(foot);
      }
    }

    const closeMenuSheet = () => {
      menuSheet.classList.remove("is-open");
      menuBackdrop.classList.remove("is-open");
      menuSheet.setAttribute("aria-hidden", "true");
      menuBackdrop.setAttribute("aria-hidden", "true");
      menuTriggers.forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-expanded", "false");
      });
      unlockPageScroll();
    };

    const openMenuSheet = () => {
      menuSheet.classList.add("is-open");
      menuBackdrop.classList.add("is-open");
      menuSheet.setAttribute("aria-hidden", "false");
      menuBackdrop.setAttribute("aria-hidden", "false");
      menuTriggers.forEach((b) => {
        b.classList.add("active");
        b.setAttribute("aria-expanded", "true");
      });
      lockPageScroll();
      menuBody.scrollTop = 0;
    };

    menuTriggers.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        if (menuSheet.classList.contains("is-open")) closeMenuSheet();
        else openMenuSheet();
      });
    });

    menuBackdrop.addEventListener("click", closeMenuSheet);
    menuBackdrop.addEventListener("touchmove", (e) => {
      if (e.target === menuBackdrop) e.preventDefault();
    }, { passive: false });
    attachSwipeDismiss(menuSheet, ".dp-mobile-menu-sheet-body", closeMenuSheet);
    window.addEventListener("resize", () => {
      if (window.innerWidth > 1023 && menuSheet.classList.contains("is-open")) closeMenuSheet();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && menuSheet.classList.contains("is-open")) closeMenuSheet();
    });
  }

  document.querySelectorAll(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) window.closeModal(overlay.id);
    });
    overlay.addEventListener("touchmove", (e) => {
      if (e.target === overlay) e.preventDefault();
    }, { passive: false });
    const dialog = overlay.querySelector(".modal-dialog");
    if (dialog) {
      attachSwipeDismiss(dialog, ".modal-body", () => window.closeModal(overlay.id));
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const activeModals = document.querySelectorAll(".modal-overlay.active");
      if (activeModals.length > 0) {
        activeModals.forEach((m) => m.classList.remove("active"));
        unlockPageScroll();
      }
      if (sidebar && sidebar.classList.contains("show")) closeSidebar();
    }
  });

  // 9. Deteksi Bentrokan Jadwal Dinamis (Admin Schedule Form)
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
        if (csrfInput && csrfInput.value) headers["X-CSRF-Token"] = csrfInput.value;
        const resp = await fetch("/admin/api/check-conflict", {
          method: "POST",
          headers,
          body: JSON.stringify({
            mentor_id: mId,
            student_id: sId,
            schedule_date: sDate,
            start_time: sTime,
            duration: duration,
          }),
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

    [mentorSelect, studentSelect, dateInput, timeInput, durationInput].forEach((el) => {
      if (el) el.addEventListener("change", checkConflictLive);
    });
  }

  // 10. Modal Pergantian Mentor Dinamis
  window.prepareMentorReplacementModal = async function(scheduleId, currentMentorName) {
    const modal = document.getElementById("replacementModal");
    const schedIdInput = document.getElementById("replaceScheduleId");
    const currentMentorSpan = document.getElementById("currentMentorSpan");
    const mentorSelect = document.getElementById("replacementMentorSelect");
    if (!modal || !schedIdInput || !mentorSelect) return;

    schedIdInput.value = scheduleId;
    if (currentMentorSpan) currentMentorSpan.innerText = currentMentorName;
    mentorSelect.replaceChildren();
    const loadingOpt = document.createElement("option");
    loadingOpt.value = "";
    loadingOpt.textContent = "-- Memuat daftar mentor yang memenuhi syarat... --";
    mentorSelect.appendChild(loadingOpt);
    window.openModal("replacementModal");

    try {
      const resp = await fetch(`/admin/api/eligible-replacements/${scheduleId}`);
      const list = await resp.json();
      mentorSelect.replaceChildren();
      const defOpt = document.createElement("option");
      defOpt.value = "";
      defOpt.textContent = "-- Pilih Mentor Pengganti --";
      mentorSelect.appendChild(defOpt);
      list.forEach((item) => {
        const m = item.mentor;
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.disabled = item.has_conflict;
        opt.textContent = `${m.full_name} (${m.expertise}) ${item.has_conflict ? " [BENTROK]" : " [TERSEDIA]"}`;
        mentorSelect.appendChild(opt);
      });
    } catch (_) {
      mentorSelect.replaceChildren();
      const errOpt = document.createElement("option");
      errOpt.value = "";
      errOpt.textContent = "Gagal memuat mentor pengganti";
      mentorSelect.appendChild(errOpt);
    }
  };
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMain);
} else {
  initMain();
}
