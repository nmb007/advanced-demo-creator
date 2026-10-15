(() => {
  if (window.__demoCreatorCursor) return;

  // Track position only — do NOT paint a DOM cursor. Chromium screencast may
  // also draw the system pointer; we hide that and composite one cursor in post.
  const style = document.createElement("style");
  style.id = "__demo_creator_cursor_style";
  style.textContent = `
    html, body, * { cursor: none !important; }
  `;
  (document.head || document.documentElement).appendChild(style);

  let x = window.innerWidth / 2;
  let y = window.innerHeight / 2;
  let anim = null;

  function setPos(nx, ny) {
    x = nx;
    y = ny;
  }

  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function moveTo(tx, ty, ms) {
    return new Promise((resolve) => {
      if (anim) cancelAnimationFrame(anim);
      const sx = x;
      const sy = y;
      const dx = tx - sx;
      const dy = ty - sy;
      const cx = sx + dx * 0.5 + (Math.random() - 0.5) * Math.min(80, Math.abs(dy) * 0.2);
      const cy = sy + dy * 0.5 + (Math.random() - 0.5) * Math.min(80, Math.abs(dx) * 0.2);
      const duration = Math.max(180, ms || 450);
      const start = performance.now();

      function frame(now) {
        const t = Math.min(1, (now - start) / duration);
        const e = easeInOutCubic(t);
        setPos(
          (1 - e) * (1 - e) * sx + 2 * (1 - e) * e * cx + e * e * tx,
          (1 - e) * (1 - e) * sy + 2 * (1 - e) * e * cy + e * e * ty
        );
        if (t < 1) {
          anim = requestAnimationFrame(frame);
        } else {
          setPos(tx, ty);
          resolve({ x: tx, y: ty });
        }
      }
      anim = requestAnimationFrame(frame);
    });
  }

  function press() {
    return new Promise((resolve) => {
      setTimeout(() => resolve({ x, y }), 140);
    });
  }

  function hover() {
    return Promise.resolve({ x, y });
  }

  function getPos() {
    return { x, y };
  }

  function ensureStyle() {
    if (!document.getElementById("__demo_creator_cursor_style")) {
      (document.head || document.documentElement).appendChild(style);
    }
  }

  ensureStyle();
  const observer = new MutationObserver(() => ensureStyle());
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.__demoCreatorCursor = { moveTo, press, hover, getPos, setPos };
})();
