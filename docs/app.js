const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const progress = document.querySelector('.scroll-progress span');
const updateProgress = () => {
  const range = document.documentElement.scrollHeight - window.innerHeight;
  progress.style.width = `${range > 0 ? Math.min(100, window.scrollY / range * 100) : 0}%`;
};
window.addEventListener('scroll', updateProgress, { passive: true });
window.addEventListener('resize', updateProgress, { passive: true });
updateProgress();

// A deterministic particle orbit: two connected loops evoke recursive improvement.
const canvas = document.querySelector('#starfield');
const context = canvas.getContext('2d');
const stage = document.querySelector('.cosmos');
const toggle = document.querySelector('.motion-toggle');
const scrollScene = document.querySelector('.hero-intro');
if (context) {
  let width = 0, height = 0, frame = 0, angle = 0, lastTime = 0;
  let paused = motionPreference.matches, visible = true;
  let scrollAmount = 0;
  let seed = 42;
  const random = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const points = Array.from({ length: 2400 }, () => {
    const t = random() * Math.PI * 2;
    const spread = (random() + random() + random() - 1.5) * .15;
    return { x: Math.cos(t) / (1 + Math.sin(t) ** 2), y: Math.sin(t) * Math.cos(t) / (1 + Math.sin(t) ** 2), z: spread, drift: (random() - .5) * .09, size: random() ** 4 * 2.5 + .45, warm: random() > .88, alpha: random() * .55 + .4, burstAngle: random() * Math.PI * 2, burstDistance: .3 + random() * 1.4, depth: random() };
  });
  const stars = Array.from({ length: 200 }, () => ({ x: random(), y: random(), r: random() * .9 + .2, a: random() * .35 + .08 }));
  const draw = () => {
    context.clearRect(0, 0, width, height);
    stars.forEach(p => { context.fillStyle = `rgba(189,213,230,${p.a})`; context.beginPath();context.arc(p.x*width,p.y*height,p.r,0,Math.PI*2);context.fill(); });
    const amount = paused || motionPreference.matches ? 0 : scrollAmount;
    const scatter = amount * amount * (3 - 2 * amount);
    const scale = Math.min(width * .42, height * .68);
    points.forEach(p => {
      const x = p.x * Math.cos(angle) + p.z * Math.sin(angle);
      const z = p.z * Math.cos(angle) - p.x * Math.sin(angle);
      const expansion = 1 + scatter * (1.4 + p.depth * 2);
      const px = width / 2 + (x * .94 - p.y * .32) * scale * expansion
        + Math.cos(p.burstAngle) * scatter * p.burstDistance * width * .55;
      const py = height * .51 + (x * .32 + p.y * .94 + p.drift) * scale * expansion
        + Math.sin(p.burstAngle) * scatter * p.burstDistance * height * .75;
      const opacity = p.alpha * (.7 + (z + 1) * .15) * (1 - scatter ** 3);
      if (px < -20 || px > width + 20 || py < -20 || py > height + 20) return;
      const color = p.warm ? '224,189,153' : '193,219,240';
      if (p.size > 1.3) {
        const glow = context.createRadialGradient(px,py,0,px,py,p.size*6);
        glow.addColorStop(0,`rgba(${color},${opacity*.6})`);glow.addColorStop(1,`rgba(${color},0)`);
        context.fillStyle=glow;context.fillRect(px-p.size*6,py-p.size*6,p.size*12,p.size*12);
      }
      context.fillStyle=`rgba(${color},${opacity})`;context.beginPath();context.arc(px,py,p.size,0,Math.PI*2);context.fill();
    });
  };
  const animate = time => {
    if (time - lastTime > 32) { angle += .0012; draw(); lastTime = time; }
    frame = requestAnimationFrame(animate);
  };
  const sync = () => {
    cancelAnimationFrame(frame);
    toggle.textContent = paused ? 'Play animation' : 'Pause animation';
    toggle.setAttribute('aria-pressed', String(paused));
    if (!paused && visible && !document.hidden) frame = requestAnimationFrame(animate);
    else draw();
  };
  const readScroll = () => {
    const distance = scrollScene.offsetHeight * .8;
    scrollAmount = distance > 0 ? Math.max(0, Math.min(1, -scrollScene.getBoundingClientRect().top / distance)) : 0;
  };
  window.addEventListener('scroll', readScroll, { passive: true });
  const resize = () => {
    width = stage.clientWidth; height = stage.clientHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width*dpr; canvas.height = height*dpr;
    context.setTransform(dpr,0,0,dpr,0,0); readScroll(); draw();
  };
  toggle.addEventListener('click', () => { paused = !paused;sync(); });
  motionPreference.addEventListener('change', () => { paused = motionPreference.matches;sync(); });
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('resize', resize, {passive:true});
  if ('IntersectionObserver' in window) new IntersectionObserver(entries => { visible=entries[0].isIntersecting;sync(); }).observe(stage);
  resize();sync();
} else toggle.hidden = true;
