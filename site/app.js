/* ==========================================================================
   GeekLord · profile micro-site behaviour
   - theme control (auto / dark / light) persisted in localStorage
   - scroll reveal + nav highlighting
   - live contribution clock from the generated data
   - sandboxed demo browser for deployed projects, with an allowlist
   ========================================================================== */

(() => {
  "use strict";

  const root = document.documentElement;
  const STORE = "geeklord-theme";

  /* ── theme ───────────────────────────────────────────────────────────── */
  const setTheme = (mode) => {
    if (mode === "auto") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", mode);
    document.querySelectorAll("[data-theme-set]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.themeSet === mode));
    });
    try { localStorage.setItem(STORE, mode); } catch { /* private mode */ }
  };

  let saved = "auto";
  try { saved = localStorage.getItem(STORE) || "auto"; } catch { /* ignore */ }
  setTheme(saved);
  document.querySelectorAll("[data-theme-set]").forEach((button) => {
    button.addEventListener("click", () => setTheme(button.dataset.themeSet));
  });

  /* ── reveal + nav ────────────────────────────────────────────────────── */
  // One rAF-throttled scroll handler rather than IntersectionObserver: it works
  // in every browser, in print, in headless renderers and for crawlers, and a
  // failsafe timer reveals the page outright if anything goes wrong.
  const revealables = [...document.querySelectorAll(".reveal")];
  const navLinks = new Map(
    [...document.querySelectorAll(".nav a")].map((link) => [link.getAttribute("href").slice(1), link])
  );
  const sections = [...document.querySelectorAll("section[id]")].filter((s) => navLinks.has(s.id));

  if ("requestAnimationFrame" in window) {
    root.classList.add("js");
    let queued = false;

    const sweep = () => {
      queued = false;
      const line = window.innerHeight * 1.05;

      revealables.forEach((element) => {
        if (!element.classList.contains("in") && element.getBoundingClientRect().top < line) {
          element.classList.add("in");
        }
      });

      const focus = window.innerHeight * 0.35;
      let current = sections[0];
      sections.forEach((section) => {
        if (section.getBoundingClientRect().top <= focus) current = section;
      });
      navLinks.forEach((link, id) => link.classList.toggle("active", current && id === current.id));
    };

    const queue = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(sweep);
    };

    window.addEventListener("scroll", queue, { passive: true });
    window.addEventListener("resize", queue, { passive: true });
    window.addEventListener("load", queue);
    queue();
    // Failsafe: whatever happens, the content is on screen within three seconds.
    setTimeout(() => revealables.forEach((element) => element.classList.add("in")), 3000);
  } else {
    revealables.forEach((element) => element.classList.add("in"));
  }

  /* ── contribution clock ──────────────────────────────────────────────── */
  const clock = document.querySelector(".clock");
  if (clock) {
    fetch("data/activity-hours.json")
      .then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
      .then((data) => {
        const hours = data.hours || [];
        // Square-root scale: one very busy hour should not flatten the rest of
        // the day into invisible slivers.
        const peak = Math.sqrt(Math.max(1, ...hours.map((entry) => entry.events)));
        const scale = (events) => Math.max(3, Math.round((Math.sqrt(events) / peak) * 100));
        clock.innerHTML = hours.map((entry) =>
          `<div class="bar" title="${String(entry.hour).padStart(2, "0")}:00 IST — ${entry.events} public event${entry.events === 1 ? "" : "s"}"
                data-height="${scale(entry.events)}%"></div>`
        ).join("");
        const label = document.querySelector("[data-clock-note]");
        if (label) {
          const busiest = hours.reduce((best, entry) => (entry.events > best.events ? entry : best), hours[0]);
          label.textContent = data.sample
            ? `${data.sample} recent public events, bucketed in IST — busiest around ${String(busiest.hour).padStart(2, "0")}:00`
            : "Not enough recent public activity to chart yet.";
        }
        requestAnimationFrame(() => {
          clock.querySelectorAll(".bar").forEach((bar) => { bar.style.height = bar.dataset.height; });
        });
      })
      .catch(() => {
        const label = document.querySelector("[data-clock-note]");
        if (label) label.textContent = "Activity data unavailable offline.";
      });
  }

  /* ── demo browser ────────────────────────────────────────────────────── */
  const frame = document.querySelector("[data-frame]");
  const picker = document.querySelector("[data-demo-picker]");
  if (frame && picker) {
    const overlay = frame.querySelector(".overlay");
    const iframe = frame.querySelector("iframe");
    const title = frame.querySelector("[data-frame-title]");
    const status = frame.querySelector("[data-frame-status]");
    const allowlist = (picker.dataset.allowlist || "").split(/\s+/).filter(Boolean);

    const load = (target) => {
      let parsed;
      try { parsed = new URL(target, location.href); } catch { return; }
      const allowed = allowlist.some((host) => parsed.hostname === host || parsed.hostname.endsWith(`.${host}`))
        || parsed.origin === location.origin;
      if (!allowed) {
        overlay.hidden = false;
        overlay.innerHTML = "<b>Blocked by the local allowlist.</b><span>Add the host to <code>allowlist</code> before embedding it.</span>";
        return;
      }
      overlay.hidden = false;
      overlay.innerHTML = `<b>Loading ${parsed.hostname}…</b><span>Some sites refuse to be framed — use “Open in a new tab” if the panel stays empty.</span>`;
      frame.classList.remove("loaded");
      iframe.src = parsed.href;
      if (title) title.textContent = parsed.hostname + parsed.pathname;
      if (status) status.textContent = `embedding ${parsed.origin}`;
    };

    iframe.addEventListener("load", () => {
      if (!iframe.src) return;
      frame.classList.add("loaded");
    });

    picker.addEventListener("change", (event) => load(event.target.value));
    const reload = document.querySelector("[data-frame-reload]");
    if (reload) reload.addEventListener("click", () => { if (iframe.src) { frame.classList.remove("loaded"); iframe.src = iframe.src; } });
    const open = document.querySelector("[data-frame-open]");
    if (open) open.addEventListener("click", () => { if (iframe.src) window.open(iframe.src, "_blank", "noopener"); });

    const first = picker.value;
    if (first) load(first);
  }

  /* ── credential filters ──────────────────────────────────────────────── */
  const filters = document.querySelectorAll("[data-filter]");
  if (filters.length) {
    const items = [...document.querySelectorAll("[data-issuer]")];
    filters.forEach((button) => {
      button.addEventListener("click", () => {
        const wanted = button.dataset.filter;
        filters.forEach((other) => other.setAttribute("aria-pressed", String(other === button)));
        items.forEach((item) => {
          item.hidden = !(wanted === "all" || item.dataset.issuer === wanted);
        });
      });
    });
  }

  /* ── copy to clipboard ───────────────────────────────────────────────── */
  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        const original = button.textContent;
        button.textContent = "copied";
        setTimeout(() => { button.textContent = original; }, 1400);
      } catch {
        button.textContent = button.dataset.copy;
      }
    });
  });

  /* ── footer stamp ────────────────────────────────────────────────────── */
  const stamp = document.querySelector("[data-built]");
  if (stamp) stamp.textContent = stamp.dataset.built;
})();
