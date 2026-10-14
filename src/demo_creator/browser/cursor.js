(() => {
  if (window.__demoCreatorCursor) return;

  const CURSOR_SVG = `
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <path fill="#111" stroke="#fff" stroke-width="1.2"
        d="M4 3l1.2 16.5 4.2-4.1 3.6 7.2 2.4-1.2-3.7-7.3L18.5 13.5z"/>
    </svg>`;

  const root = document.createElement("div");
  root.id = "__demo_creator_cursor_root";
  root.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "width:0",
    "height:0",
    "z-index:2147483647",
    "pointer-events:none",
    "overflow:visible",
  ].join(";");

  const cursor = document.createElement("div");
  cursor.innerHTML = CURSOR_SVG;
  cursor.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "width:24px",
    "height:24px",
    "transform:translate(-2px,-2px)",
    "transition:transform 80ms ease",
    "filter:drop-shadow(0 1px 2px rgba(0,0,0,.35))",
  ].join(";");

  const ripple = document.createElement("div");
  ripple.style.cssText = [
    "position:fixed",
    "left:0",
    "top:0",
    "width:12px",
    "height:12px",
    "margin-left:-6px",
    "margin-top:-6px",
    "border-radius:50%",
    "border:2px solid rgba(37,99,235,.85)",
    "opacity:0",
    "pointer-events:none",
    "transform:scale(0.4)",
  ].join(";");

  root.appendChild(ripple);
  root.appendChild(cursor);

  function ensureMounted() {
    if (!document.documentElement.contains(root)) {
      (document.body || document.documentElement).appendChild(root);
    }
  }

  let x = window.innerWidth / 2;
  let y = window.innerHeight / 2;
  let anim = null;

  function setPos(nx, ny) {
    x = nx;
    y = ny;
    cursor.style.left = `${x}px`;
    cursor.style.top = `${y}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
  }

  function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function moveTo(tx, ty, ms) {
    ensureMounted();
    return new Promise((resolve) => {
      if (anim) cancelAnimationFrame(anim);
      const sx = x;
      const sy = y;
      const dx = tx - sx;
      const dy = ty - sy;
      // Slight curve control point
      const cx = sx + dx * 0.5 + (Math.random() - 0.5) * Math.min(80, Math.abs(dy) * 0.2);
      const cy = sy + dy * 0.5 + (Math.random() - 0.5) * Math.min(80, Math.abs(dx) * 0.2);
      const duration = Math.max(120, ms || 400);
      const start = performance.now();

      function frame(now) {
        const t = Math.min(1, (now - start) / duration);
        const e = easeInOutCubic(t);
        const ox = (1 - e) * (1 - e) * sx + 2 * (1 - e) * e * cx + e * e * tx;
        const oy = (1 - e) * (1 - e) * sy + 2 * (1 - e) * e * cy + e * e * ty;
        setPos(ox, oy);
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
    ensureMounted();
    cursor.style.transform = "translate(-2px,-2px) scale(0.88)";
    ripple.style.transition = "none";
    ripple.style.opacity = "0.9";
    ripple.style.transform = "scale(0.4)";
    // force reflow
    void ripple.offsetWidth;
    ripple.style.transition = "transform 420ms ease-out, opacity 420ms ease-out";
    ripple.style.transform = "scale(2.6)";
    ripple.style.opacity = "0";
    return new Promise((resolve) => {
      setTimeout(() => {
        cursor.style.transform = "translate(-2px,-2px) scale(1)";
        resolve({ x, y });
      }, 140);
    });
  }

  function hover() {
    ensureMounted();
    cursor.style.transform = "translate(-2px,-2px) scale(1.08)";
    return Promise.resolve({ x, y });
  }

  function getPos() {
    return { x, y };
  }

  ensureMounted();
  setPos(x, y);

  const observer = new MutationObserver(() => ensureMounted());
  observer.observe(document.documentElement, { childList: true, subtree: true });

  window.__demoCreatorCursor = { moveTo, press, hover, getPos, setPos };
})();
