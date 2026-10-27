'use strict';

document.documentElement.classList.add('js');

(() => {
  const menu = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#main-nav');
  const setMenu = open => {
    menu.setAttribute('aria-expanded', String(open));
    menu.querySelector('span').textContent = open ? '×' : '+';
    nav.classList.toggle('open', open);
  };
  menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') !== 'true'));
  nav.addEventListener('click', e => { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') { setMenu(false); menu.focus(); }
  });
  document.addEventListener('click', e => { if (!e.target.closest('.site-header')) setMenu(false); });
  document.documentElement.classList.add('menu-ready');

  const search = document.querySelector('#publication-search');
  const entries = Array.from(document.querySelectorAll('.publication'));
  const filters = Array.from(document.querySelectorAll('[data-filter]'));
  const count = document.querySelector('#publication-count');
  let filter = 'all';
  const normalize = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const applyFilter = () => {
    const terms = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    let visible = 0;
    entries.forEach(entry => {
      const haystack = normalize(entry.textContent);
      const topicMatch = filter === 'all' || entry.dataset.topics.split('|').includes(filter);
      entry.hidden = !topicMatch || !terms.every(term => haystack.includes(term));
      if (!entry.hidden) visible++;
    });
    count.textContent = visible === entries.length ? `${visible} PUBLICATIONS` : `${visible} OF ${entries.length} PUBLICATIONS`;
    document.querySelector('#empty-results').hidden = visible > 0;
  };
  const reset = () => {
    filter = 'all'; search.value = '';
    filters.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.filter === 'all')));
    applyFilter();
  };
  filters.forEach(button => button.addEventListener('click', () => {
    filter = button.dataset.filter;
    filters.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    applyFilter();
  }));
  search.addEventListener('input', applyFilter);
  document.querySelector('#reset-search').addEventListener('click', () => { reset(); search.focus(); });
  const revealHash = () => {
    if (location.hash.startsWith('#pub-')) {
      const target = document.getElementById(location.hash.slice(1));
      if (target && target.hidden) { reset(); target.scrollIntoView({ block: 'start' }); }
    }
  };
  window.addEventListener('hashchange', revealHash);
  document.querySelectorAll('a[href^="#pub-"]').forEach(link => link.addEventListener('click', () => {
    const target = document.querySelector(link.getAttribute('href'));
    if (target && target.hidden) reset();
  }));
  revealHash();

  const citations = JSON.parse(document.querySelector('#citation-data').textContent);
  const dialog = document.querySelector('#citation-dialog');
  const citationText = document.querySelector('#citation-text');
  const citationStatus = document.querySelector('#citation-status');
  let citationUrl;
  document.querySelectorAll('[data-cite]').forEach(button => button.addEventListener('click', () => {
    const citation = citations[button.dataset.cite];
    document.querySelector('#citation-paper-title').textContent = citation.title;
    citationText.value = citation.bibtex;
    citationStatus.textContent = '';
    document.querySelector('#copy-citation').textContent = 'Copy BibTeX';
    if (citationUrl) URL.revokeObjectURL(citationUrl);
    citationUrl = URL.createObjectURL(new Blob([citation.bibtex + '\n'], { type: 'application/x-bibtex' }));
    const download = document.querySelector('#download-citation');
    download.href = citationUrl;
    download.download = `${button.dataset.cite}.bib`;
    dialog.showModal();
  }));
  document.querySelector('#close-citation').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => {
    const rect = dialog.getBoundingClientRect();
    if (e.target === dialog && (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => { if (citationUrl) { URL.revokeObjectURL(citationUrl); citationUrl = null; } });
  document.querySelector('#copy-citation').addEventListener('click', async () => {
    try {
      if (!navigator.clipboard) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(citationText.value);
      document.querySelector('#copy-citation').textContent = 'Copied';
      citationStatus.textContent = 'BibTeX copied to your clipboard.';
    } catch {
      citationText.focus(); citationText.select();
      citationStatus.textContent = 'Citation selected. Press Ctrl+C or Command+C to copy.';
    }
  });

  if ('IntersectionObserver' in window) {
    const navLinks = Array.from(nav.querySelectorAll('a[href^="#"]'));
    const observer = new IntersectionObserver(changes => {
      changes.forEach(change => {
        if (change.isIntersecting) navLinks.forEach(link => {
          if (link.hash === `#${change.target.id}`) link.setAttribute('aria-current', 'true');
          else link.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-15% 0px -65% 0px', threshold: 0 });
    document.querySelectorAll('main section[id]').forEach(section => observer.observe(section));
  }
  const closedForPrint = [];
  window.addEventListener('beforeprint', () => { document.querySelectorAll('details:not([open])').forEach(d => { closedForPrint.push(d); d.open = true; }); });
  window.addEventListener('afterprint', () => { closedForPrint.splice(0).forEach(d => { d.open = false; }); });
  document.querySelector('#current-year').textContent = new Date().getFullYear();
})();

// An illustrative reverse diffusion path through a fixed noise sample and portrait.
// This visualization blends a known image with noise; it does not run a trained model.
(() => {
  const canvas = document.querySelector('#research-canvas');
  const context = canvas.getContext('2d');
  const portrait = document.querySelector('#plot-fallback');
  const slider = document.querySelector('#structure');
  const play = document.querySelector('#animate-plot');
  const replay = document.querySelector('#replay-portrait');
  const stageButtons = [...document.querySelectorAll('[data-progress]')];
  const timeLabel = document.querySelector('#diffusion-time');
  const status = document.querySelector('#plot-caption');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  if (!context) return;
  const width = 480, height = 400;
  const source = document.createElement('canvas');
  source.width = canvas.width = width; source.height = canvas.height = height;
  const sourceContext = source.getContext('2d', {willReadFrequently:true});
  let pixels, noise, output, ready = false, playing = false, inView = true;
  let frame = 0, previous = 0, elapsed = 0, lastDraw = 0;
  const scenes = [];
  let currentScene = -1;
  const duration = 10000;
  // Ease out: establish the face quickly, then spend more time on fine details.
  const revealAt = u => 100 * (1 - Math.pow(1 - u, 2.4));
  const valueAt = ms => ms < 400 ? 0 : ms < 6400 ? revealAt((ms - 400) / 6000) : ms < 9400 ? 100 : (10000 - ms) / 6;
  const paint = progress => {
    const angle = (1 - progress / 100) * Math.PI / 2;
    const signal = Math.cos(angle), grain = Math.sin(angle);
    for (let i=0; i<pixels.length; i+=4) {
      const n = noise[i/4];
      for(let c=0;c<3;c++) output.data[i+c] = 127.5 + (pixels[i+c]-127.5)*signal + (n*63 + (c-1)*5)*grain;
      output.data[i+3] = 255;
    }
    sourceContext.putImageData(output,0,0);
  };
  const draw = () => {
    if (!ready) return;
    const value = Number(slider.value);
    paint(value); context.drawImage(source,0,0);
    timeLabel.textContent = `t = ${(1-value/100).toFixed(2)}`;
    status.textContent = value < 12 ? 'Starting with noise' : value < 65 ? 'A face takes shape' : value < 99 ? 'Recovering the details' : 'Hello, I’m Eitan.';
    slider.setAttribute('aria-valuetext', `${Math.round(value)} percent revealed`);
    canvas.setAttribute('aria-label', `Eitan Kosman’s portrait, ${Math.round(value)} percent revealed from noise`);
    stageButtons.forEach(button => button.setAttribute('aria-pressed',String(Math.abs(value-Number(button.dataset.progress))<2)));
  };
  const schedule = () => { if (ready && playing && inView && !document.hidden && !frame) frame=requestAnimationFrame(tick); };
  const tick = timestamp => {
    frame=0;
    if (!playing || !inView || document.hidden) {previous=0;return;}
    if (previous) {
      const next = elapsed + Math.min(timestamp-previous,100);
      if (next >= duration) chooseScene();
      elapsed = next % duration;
    }
    previous=timestamp;
    if(timestamp-lastDraw>=50){slider.value=valueAt(elapsed);draw();lastDraw=timestamp;}
    frame=requestAnimationFrame(tick);
  };
  const setPlaying = value => {
    playing=value;
    play.setAttribute('aria-pressed',String(value));
    play.setAttribute('aria-label',value?'Pause portrait diffusion':'Play portrait diffusion');
    play.innerHTML=value?'<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M6 4h3v12H6zm6 0h3v12h-3z" fill="currentColor"/></svg>':'<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="m7 4 9 6-9 6Z" fill="currentColor"/></svg>';
    if(!value && frame){cancelAnimationFrame(frame);frame=0;}
    previous=0;schedule();
  };
  const select = value => {setPlaying(false);slider.value=value;elapsed=400+6000*(1-Math.pow(1-Number(value)/100,1/2.4));draw();};
  slider.addEventListener('input',()=>select(slider.value));
  stageButtons.forEach(button=>button.addEventListener('click',()=>select(button.dataset.progress)));
  play.addEventListener('click',()=>{if(!playing && Number(slider.value)>=99){elapsed=0;chooseScene();}setPlaying(!playing);});
  replay.addEventListener('click',()=>{chooseScene();elapsed=0;slider.value=0;draw();setPlaying(true);});
  document.addEventListener('visibilitychange',()=>{previous=0;schedule();});
  reduced.addEventListener('change',e=>{if(e.matches){setPlaying(false);select(100);}});
  if('IntersectionObserver' in window)new IntersectionObserver(entries=>{inView=entries[0].isIntersecting;previous=0;schedule();}).observe(canvas);
  const chooseScene = () => {
    if (!scenes.length) return;
    // Uniformly choose another available photo, avoiding back-to-back repeats.
    const candidates = scenes.map((_, i)=>i).filter(i=>i!==currentScene);
    currentScene = candidates.length ? candidates[Math.floor(Math.random()*candidates.length)] : 0;
    pixels = scenes[currentScene];
    canvas.dataset.scene = String(currentScene);
    let seed = Math.floor(Math.random()*4294967296);
    const random=()=>{seed=(1664525*seed+1013904223)>>>0;return (seed+1)/4294967297;};
    for(let i=0;i<noise.length;i++)noise[i]=Math.sqrt(-2*Math.log(random()))*Math.cos(2*Math.PI*random());
    stageButtons.forEach(button=>{
      paint(Number(button.dataset.progress));
      const thumb=button.querySelector('canvas');
      thumb.getContext('2d').drawImage(source,0,0,thumb.width,thumb.height);
    });
  };
  const loadImage = image => new Promise(resolve => {
    if (image.complete) {resolve(image.naturalWidth ? image : null);return;}
    image.addEventListener('load',()=>resolve(image),{once:true});
    image.addEventListener('error',()=>resolve(null),{once:true});
  });
  const initialize = async () => {
    const images = await Promise.all([portrait,...document.querySelectorAll('#portrait-gallery img')].map(loadImage));
    for (const image of images.filter(Boolean)) {
      try {
        sourceContext.fillStyle='#002654';sourceContext.fillRect(0,0,width,height);
        const iw=image.naturalWidth, ih=image.naturalHeight;
        if (image.dataset.fit==='contain') {
          const scale=Math.min(width/iw,height/ih), w=iw*scale, h=ih*scale;
          sourceContext.drawImage(image,(width-w)/2,(height-h)/2,w,h);
        } else {
          const scale=Math.max(width/iw,height/ih), sw=width/scale, sh=height/scale;
          const sy=image===portrait ? Math.min(ih-sh,ih*.20) : (ih-sh)*Number(image.dataset.y||.5);
          sourceContext.drawImage(image,(iw-sw)/2,Math.max(0,sy),sw,sh,0,0,width,height);
        }
        scenes.push(new Uint8ClampedArray(sourceContext.getImageData(0,0,width,height).data));
      } catch { /* Skip any photo whose pixels cannot be read. */ }
    }
    if (!scenes.length) return; // Keep the original photo visible as a fallback.
    output=sourceContext.createImageData(width,height);
    noise=new Float32Array(width*height);
    chooseScene();ready=true;
    slider.value=reduced.matches?100:0;
    draw();canvas.parentElement.classList.add('canvas-ready');
    document.querySelector('.portrait-controls').classList.add('is-ready');
    setPlaying(!reduced.matches);
  };
  initialize();
})();

// Reveal each section once. Content stays visible without JS or with reduced motion.
(() => {
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  if (preference.matches || !('IntersectionObserver' in window)) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.remove('reveal-pending');
      entry.target.classList.add('reveal-visible');
      observer.unobserve(entry.target);
    });
  }, { threshold: .08 });
  document.querySelectorAll('.section-heading,.feature-work,.small-work,.research-footnote,.experience-intro,.timeline-entry,.patent-feature,.beyond-column,.contact-inner').forEach(element => {
    if (element.getBoundingClientRect().top < innerHeight) return;
    element.classList.add('reveal-pending');
    observer.observe(element);
  });
  preference.addEventListener('change', event => {
    if (!event.matches) return;
    observer.disconnect();
    document.querySelectorAll('.reveal-pending').forEach(element => element.classList.remove('reveal-pending'));
  });
})();

// Public GitHub data only. Retain the dated static snapshot on any failure.
(async () => {
  const status = document.querySelector('#github-metrics-status');
  try {
    const repos = [];
    for (let page = 1; page <= 100; page++) {
      const response = await fetch(`https://api.github.com/users/ekosman/repos?type=owner&per_page=100&page=${page}`, {signal:AbortSignal.timeout(8000)});
      if (!response.ok) throw new Error('GitHub unavailable');
      const batch = await response.json();
      if (!Array.isArray(batch) || batch.some(r => typeof r.stargazers_count !== 'number' || typeof r.forks_count !== 'number')) throw new Error('Invalid repository data');
      repos.push(...batch.filter(r => !r.fork));
      if (batch.length < 100) break;
      if (page === 100) throw new Error('Incomplete repository list');
    }
    document.querySelector('#total-stars').textContent = repos.reduce((n,r)=>n+r.stargazers_count,0).toLocaleString();
    document.querySelector('#total-forks').textContent = repos.reduce((n,r)=>n+r.forks_count,0).toLocaleString();
    document.querySelectorAll('[data-repo]').forEach(card => {
      const repo = repos.find(r => r.name === card.dataset.repo);
      if (!repo) return;
      card.querySelector('[data-stars]').textContent = repo.stargazers_count.toLocaleString();
      card.querySelector('[data-forks]').textContent = repo.forks_count.toLocaleString();
    });
    status.textContent = 'GitHub: refreshed ' + new Date().toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric'}) + '.';
  } catch { status.textContent = 'GitHub: snapshot, 26 October 2026. Live refresh unavailable.'; }
})();

// The discovery bar uses the publication archive's existing search and filters.
(() => {
  const form = document.querySelector('#research-discovery');
  form.addEventListener('submit', event => {
    event.preventDefault();
    const topic = document.querySelector('#discovery-topic').value;
    const search = document.querySelector('#publication-search');
    search.value = document.querySelector('#discovery-query').value;
    const filter = Array.from(document.querySelectorAll('[data-filter]')).find(button => button.dataset.filter === topic);
    filter.click();
    search.dispatchEvent(new Event('input', {bubbles:true}));
    location.hash = 'publications';
    search.focus({preventScroll:true});
    document.querySelector('#publications').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  });
})();
