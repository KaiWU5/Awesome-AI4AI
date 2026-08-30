const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const revealItems = document.querySelectorAll(".reveal");
if (reducedMotion || !("IntersectionObserver" in window)) {
  revealItems.forEach((item) => item.classList.add("in-view"));
} else {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealItems.forEach((item) => observer.observe(item));
}

const progress = document.querySelector(".scroll-progress span");
const updateProgress = () => {
  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  const value = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
  progress.style.width = `${Math.min(value, 100)}%`;
};
window.addEventListener("scroll", updateProgress, { passive: true });
updateProgress();

const counters = document.querySelectorAll("[data-count]");
if (!reducedMotion && "IntersectionObserver" in window) {
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const element = entry.target;
      const target = Number(element.dataset.count);
      const start = performance.now();
      const tick = (now) => {
        const progressValue = Math.min((now - start) / 1100, 1);
        const eased = 1 - Math.pow(1 - progressValue, 3);
        element.textContent = Math.round(target * eased);
        if (progressValue < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      counterObserver.unobserve(element);
    });
  }, { threshold: 0.6 });
  counters.forEach((counter) => {
    counter.textContent = "0";
    counterObserver.observe(counter);
  });
}

if (!reducedMotion && window.matchMedia("(pointer: fine)").matches) {
  document.querySelectorAll(".tilt").forEach((card) => {
    card.addEventListener("pointermove", (event) => {
      const bounds = card.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / bounds.width - 0.5;
      const y = (event.clientY - bounds.top) / bounds.height - 0.5;
      card.style.transform = `rotateX(${-y * 4}deg) rotateY(${x * 5}deg) translateY(-3px)`;
    });
    card.addEventListener("pointerleave", () => { card.style.transform = ""; });
  });
}

if (!reducedMotion) {
  const canvas = document.querySelector("#starfield");
  const context = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let points = [];
  let frame = 0;

  const resize = () => {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const count = Math.min(90, Math.max(35, Math.floor(width / 18)));
    points = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.12,
      vy: (Math.random() - 0.5) * 0.12,
      radius: Math.random() * 1.2 + 0.35
    }));
  };

  const draw = () => {
    context.clearRect(0, 0, width, height);
    points.forEach((point, index) => {
      point.x = (point.x + point.vx + width) % width;
      point.y = (point.y + point.vy + height) % height;
      context.beginPath();
      context.arc(point.x, point.y, point.radius, 0, Math.PI * 2);
      context.fillStyle = index % 7 === 0 ? "rgba(155,124,255,.8)" : "rgba(210,229,255,.62)";
      context.fill();
      for (let next = index + 1; next < points.length; next += 1) {
        const other = points[next];
        const distance = Math.hypot(point.x - other.x, point.y - other.y);
        if (distance < 105) {
          context.beginPath();
          context.moveTo(point.x, point.y);
          context.lineTo(other.x, other.y);
          context.strokeStyle = `rgba(103,212,255,${(1 - distance / 105) * 0.08})`;
          context.stroke();
        }
      }
    });
    frame = requestAnimationFrame(draw);
  };

  window.addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(frame);
    else draw();
  });
  resize();
  draw();
}
