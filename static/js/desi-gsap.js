(function () {
  "use strict";

  var prefersReduced = Boolean(
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  function initGsapAnimations() {
    var gsap = window.gsap;
    var ScrollTrigger = window.ScrollTrigger;
    if (!gsap) return;

    if (ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
      if (window.__dpLenis && typeof window.__dpLenis.on === "function") {
        window.__dpLenis.on("scroll", ScrollTrigger.update);
      }
    }

    // 0. Login Closing-Gate Choreography (.dp-login-gate left+right doors close inward)
    var loginGate = document.querySelector(".dp-login-gate");
    if (loginGate && !prefersReduced) {
      var gateLeft = loginGate.querySelector(".dp-login-gate-left");
      var gateRight = loginGate.querySelector(".dp-login-gate-right");
      var gateSeam = loginGate.querySelector(".dp-gate-seam");
      var gateCard = loginGate.querySelector(".dp-login-card");
      var gateTexts = loginGate.querySelectorAll(".dp-login-photo-inner");

      var gateTl = gsap.timeline({ defaults: { ease: "power3.out" } });
      if (gateLeft && gateRight) {
        gateTl
          .fromTo(gateLeft, { xPercent: -100, opacity: 0.45 }, { xPercent: 0, opacity: 1, duration: 0.78 }, 0)
          .fromTo(gateRight, { xPercent: 100, opacity: 0.45 }, { xPercent: 0, opacity: 1, duration: 0.78 }, 0);
      }
      if (gateSeam) {
        gateTl
          .fromTo(gateSeam, { opacity: 0, scaleY: 0.3 }, { opacity: 0.9, scaleY: 1, duration: 0.24 }, 0.56)
          .to(gateSeam, { opacity: 0, duration: 0.36 }, 0.84);
      }
      if (gateTexts && gateTexts.length) {
        gateTl.fromTo(gateTexts, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.44, stagger: 0.05 }, 0.42);
      }
      if (gateCard) {
        gateTl.fromTo(gateCard, { opacity: 0, y: 16, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.46 }, 0.48);
      }
    }

    // 1. Top Scroll Progress Bar (#dpScrollProgress)
    var progressBar = document.getElementById("dpScrollProgress");
    if (progressBar && ScrollTrigger && !prefersReduced) {
      gsap.to(progressBar, {
        scaleX: 1,
        ease: "none",
        scrollTrigger: {
          trigger: document.documentElement,
          start: "top top",
          end: "bottom bottom",
          scrub: 0.15,
        },
      });
    }

    if (!prefersReduced) {
      // 2. Masked Reveals for headings/titles ([data-gsap-reveal])
      document.querySelectorAll("[data-gsap-reveal]").forEach(function (el) {
        gsap.fromTo(
          el,
          { clipPath: "inset(0 0 100% 0)", opacity: 0, y: 18 },
          {
            clipPath: "inset(0 0 0% 0)",
            opacity: 1,
            y: 0,
            duration: 0.65,
            ease: "power3.out",
            scrollTrigger: ScrollTrigger
              ? { trigger: el, start: "top 90%", once: true }
              : undefined,
          }
        );
      });

      // 2b. Subtle Parallax Drift on Mosaic Tiles (.dp-mosaic-tile)
      if (ScrollTrigger) {
        document.querySelectorAll(".dp-mosaic-tile").forEach(function (item, idx) {
          var shift = idx % 2 === 0 ? -10 : 10;
          gsap.fromTo(
            item,
            { y: -shift * 0.4 },
            {
              y: shift * 0.4,
              ease: "none",
              scrollTrigger: {
                trigger: item.closest("section") || item,
                start: "top bottom",
                end: "bottom top",
                scrub: 0.4,
              },
            }
          );
        });
      }

      // 3. Staggered Entrances (30ms stagger, clean ease-out, no bounce)
      var staggerGroups = [
        ".dp-an-tiles",
        ".dp-agenda-scroll",
        ".dp-codename-list",
        ".dp-portal-rows",
        ".dp-faq-list",
      ];
      staggerGroups.forEach(function (parentSel) {
        document.querySelectorAll(parentSel).forEach(function (wrap) {
          var kids = wrap.children;
          if (!kids || !kids.length) return;
          gsap.fromTo(
            kids,
            { opacity: 0, y: 14 },
            {
              opacity: 1,
              y: 0,
              duration: 0.48,
              stagger: 0.03,
              ease: "power3.out",
              clearProps: "transform",
              scrollTrigger: ScrollTrigger
                ? { trigger: wrap, start: "top 92%", once: true }
                : undefined,
            }
          );
        });
      });

      // 4. Proportional Segment Fills
      document.querySelectorAll(".dp-seg-fill").forEach(function (seg) {
        gsap.fromTo(
          seg,
          { scaleX: 0 },
          {
            scaleX: 1,
            duration: 0.68,
            ease: "power3.out",
            transformOrigin: "left center",
            scrollTrigger: ScrollTrigger
              ? { trigger: seg.parentElement || seg, start: "top 92%", once: true }
              : undefined,
          }
        );
      });

      // 5. Numeric Count-Up ([data-gsap-count])
      document.querySelectorAll("[data-gsap-count]").forEach(function (el) {
        var raw = el.getAttribute("data-gsap-count");
        var target = parseFloat(raw);
        if (!Number.isFinite(target)) return;
        var suffix = el.getAttribute("data-gsap-suffix") || "";
        var prefix = el.getAttribute("data-gsap-prefix") || "";
        var obj = { val: 0 };
        gsap.to(obj, {
          val: target,
          duration: 0.85,
          ease: "power3.out",
          scrollTrigger: ScrollTrigger
            ? { trigger: el, start: "top 92%", once: true }
            : undefined,
          onUpdate: function () {
            el.textContent = prefix + Math.round(obj.val).toLocaleString("id-ID") + suffix;
          },
        });
      });

      // 6. Scale to 0.97 on Press (Rule 4)
      var pressTargets = document.querySelectorAll(
        ".dp-btn, .dp-flight-cta, .dp-portal-tab, .dp-cycle-btn, .dp-prog-open-btn, .dash-tab-pill, .dp-float-icon-btn"
      );
      pressTargets.forEach(function (btn) {
        btn.addEventListener("pointerdown", function () {
          gsap.to(btn, { scale: 0.97, duration: 0.1, ease: "power2.out", overwrite: "auto" });
        });
        ["pointerup", "pointercancel", "pointerleave"].forEach(function (evName) {
          btn.addEventListener(evName, function () {
            gsap.to(btn, { scale: 1, duration: 0.16, ease: "power2.out", overwrite: "auto" });
          });
        });
      });
    }

    // 7. Interactive 8-Session Cycle Explorer (Rules 5, 8, 16) - clean typography, zero middots
    var explorer = document.getElementById("dpCycleExplorer");
    if (explorer) {
      var btns = Array.prototype.slice.call(explorer.querySelectorAll(".dp-cycle-btn"));
      var indicator = explorer.querySelector(".dp-cycle-indicator");
      var badge = document.getElementById("dpCycleBadge");
      var titleEl = document.getElementById("dpCycleTitle");
      var descEl = document.getElementById("dpCycleDesc");
      var tagEl = document.getElementById("dpCycleTag");
      var readout = explorer.querySelector(".dp-cycle-readout");

      function moveIndicator(btn, animate) {
        if (!indicator || !btn) return;
        var offsetX = btn.offsetLeft - 4;
        var w = btn.offsetWidth;
        if (animate && !prefersReduced) {
          var tl = gsap.timeline();
          tl.to(indicator, {
            x: offsetX,
            width: w,
            scaleX: 1.12,
            duration: 0.16,
            ease: "power2.inOut",
          }).to(indicator, {
            scaleX: 1,
            duration: 0.18,
            ease: "power3.out",
          });
        } else {
          gsap.set(indicator, { x: offsetX, width: w, scaleX: 1 });
        }
      }

      var activeBtn = explorer.querySelector(".dp-cycle-btn.is-active") || btns[0];
      if (activeBtn) {
        window.requestAnimationFrame(function () {
          moveIndicator(activeBtn, false);
        });
        window.addEventListener("resize", function () {
          var cur = explorer.querySelector(".dp-cycle-btn.is-active") || btns[0];
          if (cur) moveIndicator(cur, false);
        });
      }

      btns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          btns.forEach(function (b) {
            b.classList.remove("is-active");
            b.setAttribute("aria-selected", "false");
          });
          btn.classList.add("is-active");
          btn.setAttribute("aria-selected", "true");
          moveIndicator(btn, true);

          var stepNo = btn.getAttribute("data-cycle-step") || "1";
          var cTitle = btn.getAttribute("data-cycle-title") || "";
          var cDesc = btn.getAttribute("data-cycle-desc") || "";
          var cTag = btn.getAttribute("data-cycle-tag") || "";

          if (readout && !prefersReduced) {
            gsap.fromTo(
              readout,
              { opacity: 0.45, y: 6 },
              { opacity: 1, y: 0, duration: 0.24, ease: "power3.out" }
            );
          }
          if (badge) {
            badge.textContent = "Pertemuan " + stepNo + " dari 8";
          }
          if (titleEl) titleEl.textContent = cTitle;
          if (descEl) descEl.textContent = cDesc;
          if (tagEl) tagEl.textContent = cTag;
        });
      });
    }

    // 8. Floating Scroll Action Bar (Rules 10 & 15)
    var floatBar = document.getElementById("dpFloatBar");
    if (floatBar) {
      var shown = false;
      function toggleFloatBar() {
        var shouldShow = (window.scrollY || 0) > 520;
        if (shouldShow === shown) return;
        shown = shouldShow;
        if (prefersReduced) {
          floatBar.classList.toggle("is-visible", shown);
          return;
        }
        if (shown) {
          floatBar.classList.add("is-visible");
          gsap.fromTo(
            floatBar,
            { opacity: 0, y: 14, scale: 0.95 },
            { opacity: 1, y: 0, scale: 1, duration: 0.24, ease: "power3.out" }
          );
        } else {
          gsap.to(floatBar, {
            opacity: 0,
            y: 10,
            scale: 0.96,
            duration: 0.18,
            ease: "power2.in",
            onComplete: function () {
              if (!shown) floatBar.classList.remove("is-visible");
            },
          });
        }
      }
      window.addEventListener("scroll", toggleFloatBar, { passive: true });
      toggleFloatBar();

      var topBtn = document.getElementById("dpFloatTopBtn");
      if (topBtn) {
        topBtn.addEventListener("click", function () {
          if (window.__dpLenis && typeof window.__dpLenis.scrollTo === "function") {
            window.__dpLenis.scrollTo(0, { duration: 1.0 });
          } else {
            window.scrollTo({ top: 0, behavior: prefersReduced ? "auto" : "smooth" });
          }
        });
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGsapAnimations);
  } else {
    initGsapAnimations();
  }
})();
