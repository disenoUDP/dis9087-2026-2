'use strict';

/*
 * Air Canvas / Light Painting — versión web.
 * Port de la app en Python + OpenCV (carpeta "Open CV") a JavaScript puro:
 * misma detección por pico de brillo, calibración de reflejos de 5 s,
 * recalibración adaptativa en la espera, rotación de colores y autoguardado.
 */

const CFG = {
  maxProcessSide: 1280,      // se procesa como máximo a 1280 px de lado
  minBrightness: 215,        // umbral del puntero (0-255)
  minArea: 3,
  maxArea: 50000,
  movementThresholdPx: 5,
  brushThickness: 13,
  calibrationDuration: 5,
  calibGlareLevel: 225,
  calibMinHitRatio: 0.6,
  maxGlareAreaRatio: 0.08,
  inactivityLimit: 3,
  baseCooldown: 2,
  maxAdditionalRecalib: 3,
  recalibExtra: 1.8,
  cooldownGlareLevel: 220,
  cooldownMinHitRatio: 0.4,
  saveShortSide: 1080,       // capturas en 1080p
  jpegQuality: 0.94,
  notifyDuration: 2.5,
};

// Secuencia de colores por captura: Amarillo -> Azul -> Rojo
const PALETTE = [
  { name: 'Amarillo', css: 'rgb(255, 235, 0)' },
  { name: 'Azul', css: 'rgb(0, 130, 255)' },
  { name: 'Rojo', css: 'rgb(255, 20, 20)' },
];

const COUNTER_KEY = 'airCanvas.nextIndex';
const AUTO_DOWNLOAD_KEY = 'airCanvas.autoDownload';

// ===========================================================================
// Visión: utilidades sobre máscaras binarias (Uint8Array con 0/1)
// ===========================================================================

/** Erosión con el kernel elíptico 3x3 de OpenCV (una cruz), dentro de un ROI. */
function erodeCross(src, dst, w, roi) {
  const [x0, y0, x1, y1] = roi;
  for (let y = y0; y <= y1; y++) {
    let i = y * w + x0;
    for (let x = x0; x <= x1; x++, i++) {
      dst[i] = src[i] &&
        x > x0 && src[i - 1] && x < x1 && src[i + 1] &&
        y > y0 && src[i - w] && y < y1 && src[i + w] ? 1 : 0;
    }
  }
}

/** Dilatación con el kernel elíptico 3x3 de OpenCV (una cruz), dentro de un ROI. */
function dilateCross(src, dst, w, roi) {
  const [x0, y0, x1, y1] = roi;
  for (let y = y0; y <= y1; y++) {
    let i = y * w + x0;
    for (let x = x0; x <= x1; x++, i++) {
      dst[i] = src[i] ||
        (x > x0 && src[i - 1]) || (x < x1 && src[i + 1]) ||
        (y > y0 && src[i - w]) || (y < y1 && src[i + w]) ? 1 : 0;
    }
  }
}

// Filas del kernel elíptico 9x9 de OpenCV: [dy, medio ancho]
const ELLIPSE_9 = [-4, -3, -2, -1, 0, 1, 2, 3, 4].map((dy) => [dy, Math.round(Math.sqrt(16 - dy * dy))]);

/** Dilatación con elipse 9x9 sobre toda la imagen. */
function dilateEllipse9(src, w, h) {
  const out = new Uint8Array(w * h);
  for (let y = 0, i = 0; y < h; y++) {
    for (let x = 0; x < w; x++, i++) {
      if (!src[i]) continue;
      for (const [dy, hw] of ELLIPSE_9) {
        const ny = y + dy;
        if (ny < 0 || ny >= h) continue;
        const row = ny * w;
        const a = x - hw < 0 ? 0 : x - hw;
        const b = x + hw >= w ? w - 1 : x + hw;
        for (let k = row + a; k <= row + b; k++) out[k] = 1;
      }
    }
  }
  return out;
}

/**
 * Etiqueta componentes 8-conexas dentro de un ROI (equivalente a los
 * contornos externos de findContours). Devuelve área y centroide de cada una.
 */
function labelBlobs(mask, w, roi, labels, stack) {
  const [x0, y0, x1, y1] = roi;
  for (let y = y0; y <= y1; y++) labels.fill(0, y * w + x0, y * w + x1 + 1);

  const blobs = [];
  for (let y = y0; y <= y1; y++) {
    for (let x = x0, i = y * w + x0; x <= x1; x++, i++) {
      if (!mask[i] || labels[i]) continue;

      const id = blobs.length + 1;
      let top = 0;
      stack[top++] = i;
      labels[i] = id;
      let area = 0, sx = 0, sy = 0;

      while (top > 0) {
        const j = stack[--top];
        const jy = (j / w) | 0;
        const jx = j - jy * w;
        area++;
        sx += jx;
        sy += jy;
        const ya = jy > y0 ? jy - 1 : jy, yb = jy < y1 ? jy + 1 : jy;
        const xa = jx > x0 ? jx - 1 : jx, xb = jx < x1 ? jx + 1 : jx;
        for (let ny = ya; ny <= yb; ny++) {
          for (let k = ny * w + xa, end = ny * w + xb; k <= end; k++) {
            if (mask[k] && !labels[k]) {
              labels[k] = id;
              stack[top++] = k;
            }
          }
        }
      }
      blobs.push({ area, cx: sx / area, cy: sy / area });
    }
  }
  return blobs;
}

/** Rellena los huecos interiores (como drawContours con relleno sobre contornos externos). */
function fillHoles(mask, w, h) {
  const n = w * h;
  const outside = new Uint8Array(n);
  const stack = new Int32Array(n);
  let top = 0;
  const push = (i) => {
    if (!mask[i] && !outside[i]) {
      outside[i] = 1;
      stack[top++] = i;
    }
  };
  for (let x = 0; x < w; x++) { push(x); push((h - 1) * w + x); }
  for (let y = 0; y < h; y++) { push(y * w); push(y * w + w - 1); }
  while (top > 0) {
    const i = stack[--top];
    const x = i % w;
    if (x > 0) push(i - 1);
    if (x < w - 1) push(i + 1);
    if (i >= w) push(i - w);
    if (i < n - w) push(i + w);
  }
  for (let i = 0; i < n; i++) if (!mask[i] && !outside[i]) mask[i] = 1;
}

/** Percentil (interpolación lineal, como np.percentile) a partir de un histograma de 256 niveles. */
function percentileFromHist(hist, n, q) {
  const idx = (q / 100) * (n - 1);
  const lo = Math.floor(idx);
  let cum = 0, vLo = -1, vHi = -1;
  for (let v = 0; v < 256; v++) {
    cum += hist[v];
    if (vLo < 0 && cum > lo) vLo = v;
    if (cum > lo + 1) { vHi = v; break; }
  }
  if (vHi < 0) vHi = vLo;
  return vLo + (vHi - vLo) * (idx - lo);
}

/** Máscara de reflejos fijos a partir del acumulador de la calibración inicial. */
function buildStaticMask(acc, minHits, w, h, labels, stack) {
  const n = w * h;
  const raw = new Uint8Array(n);
  for (let i = 0; i < n; i++) raw[i] = acc[i] >= minHits ? 1 : 0;

  const dilated = dilateEllipse9(raw, w, h);
  const blobs = labelBlobs(dilated, w, [0, 0, w - 1, h - 1], labels, stack);
  const maxGlareArea = n * CFG.maxGlareAreaRatio;
  const keep = blobs.map((b) => b.area <= maxGlareArea);

  const mask = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const id = labels[i];
    if (id && keep[id - 1]) mask[i] = 1;
  }
  fillHoles(mask, w, h);
  return { mask, zones: keep.filter(Boolean).length };
}

// ===========================================================================
// Rastreador del puntero de luz (tracker.py)
// ===========================================================================

class LightTracker {
  constructor(w, h) {
    const n = w * h;
    this.w = w;
    this.h = h;
    this.minBrightness = CFG.minBrightness;
    this.staticMask = null;

    this.intensity = new Uint8Array(n);
    this.raw = new Uint8Array(n);
    this.eroded = new Uint8Array(n);
    this.opened = new Uint8Array(n);
    this.clean = new Uint8Array(n);   // válida sólo dentro de this.roi
    this.labels = new Int32Array(n);
    this.stack = new Int32Array(n);
    this.roi = null;

    this.lastCentroid = null;
    this.lastMovementTime = 0;
    this.isDetected = false;
    this.isMoving = false;
  }

  /** Detecta el foco de la linterna en un fotograma RGBA ya espejado. */
  process(data, t) {
    const { w, h, intensity: I, raw, staticMask } = this;
    const n = w * h;

    // 1-3. Intensidad = max(R, G, B) (= max(gris, V de HSV)), sin reflejos fijos, y su máximo
    let maxVal = -1, maxIdx = 0;
    for (let i = 0, p = 0; i < n; i++, p += 4) {
      let v = data[p];
      const g = data[p + 1], b = data[p + 2];
      if (g > v) v = g;
      if (b > v) v = b;
      if (staticMask !== null && staticMask[i]) v = 0;
      I[i] = v;
      if (v > maxVal) { maxVal = v; maxIdx = i; }
    }

    this.roi = null;
    let centroid = null;
    let detected = false;

    // 4. ¿El brillo máximo supera el umbral de la linterna?
    if (maxVal >= this.minBrightness) {
      const thr = Math.max(this.minBrightness, maxVal - 25);
      let x0 = w, y0 = h, x1 = -1, y1 = -1;
      for (let y = 0, i = 0; y < h; y++) {
        for (let x = 0; x < w; x++, i++) {
          if (I[i] > thr) {
            raw[i] = 1;
            if (x < x0) x0 = x;
            if (x > x1) x1 = x;
            if (y < y0) y0 = y;
            y1 = y;
          } else {
            raw[i] = 0;
          }
        }
      }

      let blobs = [];
      if (x1 >= 0) {
        // Apertura + dilatación sólo alrededor de los píxeles brillantes
        const roi = [Math.max(0, x0 - 3), Math.max(0, y0 - 3), Math.min(w - 1, x1 + 3), Math.min(h - 1, y1 + 3)];
        erodeCross(raw, this.eroded, w, roi);
        dilateCross(this.eroded, this.opened, w, roi);
        dilateCross(this.opened, this.clean, w, roi);
        this.roi = roi;
        blobs = labelBlobs(this.clean, w, roi, this.labels, this.stack);
      }

      if (blobs.length > 0) {
        let best = null;
        for (const b of blobs) {
          if (b.area >= CFG.minArea && b.area <= CFG.maxArea && (best === null || b.area > best.area)) best = b;
        }
        if (best !== null) {
          centroid = [Math.floor(best.cx), Math.floor(best.cy)];
          detected = true;
        }
      } else if (maxVal >= this.minBrightness + 5) {
        // Punto muy brillante pero diminuto: usar la posición del máximo
        centroid = [maxIdx % w, (maxIdx / w) | 0];
        detected = true;
      }
    }

    this.isDetected = detected;

    // 5. Detección de movimiento
    if (detected) {
      if (this.lastCentroid !== null) {
        const dist = Math.hypot(centroid[0] - this.lastCentroid[0], centroid[1] - this.lastCentroid[1]);
        this.isMoving = dist >= CFG.movementThresholdPx;
        if (this.isMoving) this.lastMovementTime = t;
      } else {
        this.isMoving = true;
        this.lastMovementTime = t;
      }
      this.lastCentroid = centroid;
    } else {
      this.isMoving = false;
      this.lastCentroid = null;
    }

    return { detected, centroid };
  }

  resetInactivity(t) {
    this.lastMovementTime = t;
  }
}

// ===========================================================================
// Lienzo virtual (canvas.py)
// ===========================================================================

class AirCanvas {
  constructor(w, h, thickness, index = 0) {
    this.el = document.createElement('canvas');
    this.el.width = w;
    this.el.height = h;
    this.ctx = this.el.getContext('2d');
    this.thickness = thickness;
    this.index = index;
    this.prev = null;
    this.hasStrokes = false;
  }

  get color() { return PALETTE[this.index]; }
  get nextColor() { return PALETTE[(this.index + 1) % PALETTE.length]; }

  setThickness(value) {
    this.thickness = Math.max(1, Math.min(60, Math.round(value)));
  }

  setIndex(index) {
    this.index = ((index % PALETTE.length) + PALETTE.length) % PALETTE.length;
  }

  advanceColor() {
    this.setIndex(this.index + 1);
    return this.color.name;
  }

  addPoint([x, y]) {
    if (this.prev !== null) {
      const { ctx } = this;
      ctx.strokeStyle = ctx.fillStyle = this.color.css;
      ctx.lineWidth = this.thickness;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      ctx.moveTo(this.prev[0], this.prev[1]);
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x, y, Math.max(1, this.thickness / 2), 0, Math.PI * 2);
      ctx.fill();
      this.hasStrokes = true;
    }
    this.prev = [x, y];
  }

  stopStroke() {
    this.prev = null;
  }

  clear() {
    this.ctx.clearRect(0, 0, this.el.width, this.el.height);
    this.prev = null;
    this.hasStrokes = false;
  }
}

// ===========================================================================
// Aplicación (main.py)
// ===========================================================================

const S = {
  running: false,
  stream: null,
  w: 0,
  h: 0,
  procCanvas: null,
  procCtx: null,
  viewCtx: null,
  saveCanvas: null,
  saveCtx: null,
  maskImage: null,
  tracker: null,
  air: null,

  calibrating: false,
  calibStart: 0,
  calibFrames: 0,
  maxAmbient: 0,
  calibAcc: null,
  hist: new Uint32Array(256),
  staticMask: null,
  zones: 0,

  cooldownStart: -Infinity,
  cooldownLimit: CFG.baseCooldown,
  recalibNeeded: false,
  recalibMerged: false,
  cdFrames: 0,
  cdAcc: null,
  scratch: null,

  captureTriggered: false,
  showMask: false,
  showSlider: false,
  thickness: CFG.brushThickness,
  colorIndex: 0,

  useRVFC: false,
  frameReq: 0,
  lastFrameAt: 0,
  watchdog: 0,

  captures: [],
  toastTimer: 0,
  memIndex: 1,
  hudKey: '',
};

let els = null;

const nowSec = () => performance.now() / 1000;

function setText(el, text) {
  if (el.textContent !== text) el.textContent = text;
}

// ---------- Cámara ----------

async function startCamera() {
  els.startError.hidden = true;

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showStartError(window.isSecureContext
      ? 'Tu navegador no permite acceder a la cámara.'
      : 'La cámara sólo funciona si la página se abre por HTTPS o desde localhost.');
    return;
  }

  els.startBtn.disabled = true;
  setText(els.startBtn, 'Solicitando cámara…');

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
    });
    els.video.srcObject = stream;
    if (els.video.readyState < 1) {
      await new Promise((resolve) => els.video.addEventListener('loadedmetadata', resolve, { once: true }));
    }
    await els.video.play();
    setup(stream);
  } catch (err) {
    console.error(err);
    const messages = {
      NotAllowedError: 'Permiso de cámara denegado. Actívalo desde el candado de la barra de direcciones y vuelve a intentarlo.',
      SecurityError: 'Permiso de cámara denegado. Actívalo desde el candado de la barra de direcciones y vuelve a intentarlo.',
      NotFoundError: 'No se encontró ninguna cámara. Conecta una y vuelve a intentarlo.',
      OverconstrainedError: 'No se encontró una cámara compatible.',
      NotReadableError: 'La cámara está siendo usada por otra aplicación.',
    };
    showStartError(messages[err && err.name] || `No se pudo iniciar la cámara (${(err && err.name) || err}).`);
    stopStream();
  } finally {
    els.startBtn.disabled = false;
    setText(els.startBtn, 'Activar cámara');
  }
}

function showStartError(message) {
  els.startError.textContent = message;
  els.startError.hidden = false;
}

function stopStream() {
  const stream = S.stream || els.video.srcObject;
  if (stream) stream.getTracks().forEach((track) => track.stop());
  S.stream = null;
  els.video.srcObject = null;
}

function setup(stream) {
  const vw = els.video.videoWidth || 1280;
  const vh = els.video.videoHeight || 720;
  const scale = Math.min(1, CFG.maxProcessSide / Math.max(vw, vh));
  const w = Math.round(vw * scale);
  const h = Math.round(vh * scale);
  const n = w * h;

  S.stream = stream;
  S.w = w;
  S.h = h;

  S.procCanvas = document.createElement('canvas');
  S.procCanvas.width = w;
  S.procCanvas.height = h;
  S.procCtx = S.procCanvas.getContext('2d', { willReadFrequently: true });

  els.view.width = w;
  els.view.height = h;
  S.viewCtx = els.view.getContext('2d');
  S.maskImage = S.viewCtx.createImageData(w, h);

  const k = CFG.saveShortSide / Math.min(w, h);
  S.saveCanvas = document.createElement('canvas');
  S.saveCanvas.width = Math.round(w * k);
  S.saveCanvas.height = Math.round(h * k);
  S.saveCtx = S.saveCanvas.getContext('2d');

  S.tracker = new LightTracker(w, h);
  S.air = new AirCanvas(w, h, S.thickness, S.colorIndex);

  S.calibAcc = new Uint16Array(n);
  S.cdAcc = new Uint16Array(n);
  S.scratch = new Int32Array(n);
  S.staticMask = null;
  S.zones = 0;

  S.calibrating = true;
  S.calibStart = nowSec();
  S.calibFrames = 0;
  S.maxAmbient = 0;

  S.cooldownStart = -Infinity;
  S.cooldownLimit = CFG.baseCooldown;
  S.recalibNeeded = false;
  S.recalibMerged = false;
  S.cdFrames = 0;
  S.captureTriggered = false;
  S.showMask = false;
  S.hudKey = '';
  els.maskCaption.hidden = true;

  els.stage.style.setProperty('--ar', `${w} / ${h}`);
  els.stage.style.setProperty('--arn', String(w / h));

  const [track] = stream.getVideoTracks();
  if (track) track.addEventListener('ended', () => stopCamera('La cámara se desconectó.'));

  console.info(`[INFO] Cámara iniciada: ${vw}x${vh} (procesando a ${w}x${h})`);

  S.running = true;
  S.useRVFC = 'requestVideoFrameCallback' in HTMLVideoElement.prototype;
  S.lastFrameAt = performance.now();
  setPhase('calibrating');
  startWatchdog();
  schedule();
}

function stopCamera(message) {
  if (!S.running) return;
  S.running = false;
  cancelFrame();
  clearInterval(S.watchdog);
  stopStream();
  if (S.air) S.colorIndex = S.air.index;
  S.calibAcc = S.cdAcc = S.scratch = null;
  S.tracker = null;
  S.showMask = S.showSlider = false;
  els.maskCaption.hidden = els.slider.hidden = true;
  hideToast();
  setPhase('idle');
  if (message) showStartError(message);
  console.info('[INFO] Cámara detenida.');
}

// ---------- Bucle de fotogramas ----------

function schedule() {
  if (!S.running) return;
  S.frameReq = S.useRVFC
    ? els.video.requestVideoFrameCallback(onFrame)
    : requestAnimationFrame(onFrame);
}

function cancelFrame() {
  if (S.useRVFC) els.video.cancelVideoFrameCallback(S.frameReq);
  else cancelAnimationFrame(S.frameReq);
}

/** Si requestVideoFrameCallback deja de llegar, se cambia a requestAnimationFrame. */
function startWatchdog() {
  clearInterval(S.watchdog);
  S.watchdog = setInterval(() => {
    if (!S.running || !S.useRVFC || document.visibilityState !== 'visible') return;
    if (performance.now() - S.lastFrameAt > 1500) {
      els.video.cancelVideoFrameCallback(S.frameReq);
      S.useRVFC = false;
      schedule();
    }
  }, 1000);
}

function onFrame() {
  if (!S.running) return;
  S.lastFrameAt = performance.now();
  if (els.video.readyState >= 2) {
    try {
      step();
    } catch (err) {
      console.error(err);
    }
  }
  schedule();
}

function step() {
  const t = nowSec();
  const { w, h, procCtx } = S;

  // Modo espejo para interacción natural
  procCtx.setTransform(-1, 0, 0, 1, w, 0);
  procCtx.drawImage(els.video, 0, 0, w, h);
  procCtx.setTransform(1, 0, 0, 1, 0, 0);
  const data = procCtx.getImageData(0, 0, w, h).data;

  // FASE 1: calibración inicial
  if (S.calibrating) {
    calibrationStep(data, t);
    drawView();
    return;
  }

  // FASE 2: detección, recalibración en espera y dibujo
  const timeInCooldown = t - S.cooldownStart;
  const inCooldown = timeInCooldown < S.cooldownLimit;
  let detected = false;

  if (inCooldown) {
    S.air.stopStroke();
    S.tracker.resetInactivity(t);
    S.tracker.roi = null;
    cooldownStep(data, timeInCooldown);
  } else {
    if (S.recalibNeeded && !S.recalibMerged) mergeNewGlare();
    const result = S.tracker.process(data, t);
    detected = result.detected;
    if (detected) {
      S.air.addPoint(result.centroid);
      S.captureTriggered = false;
    } else {
      S.air.stopStroke();
    }
  }

  const sinceMove = t - S.tracker.lastMovementTime;
  const timerActive = !inCooldown && S.air.hasStrokes && !S.captureTriggered;

  drawView();
  updateHud(t, inCooldown, detected, timerActive, sinceMove);

  // Autoguardado por inactividad
  if (timerActive && sinceMove >= CFG.inactivityLimit) capture(t);
}

function calibrationStep(data, t) {
  const elapsed = t - S.calibStart;
  const remaining = Math.max(0, CFG.calibrationDuration - elapsed);
  const progress = Math.min(1, elapsed / CFG.calibrationDuration);
  const n = S.w * S.h;
  const { hist, calibAcc } = S;

  S.calibFrames++;
  hist.fill(0);
  for (let i = 0, p = 0; i < n; i++, p += 4) {
    let v = data[p];
    const g = data[p + 1], b = data[p + 2];
    if (g > v) v = g;
    if (b > v) v = b;
    hist[v]++;
    if (v >= CFG.calibGlareLevel) calibAcc[i]++; // zonas con brillo persistente
  }

  const frameBright = percentileFromHist(hist, n, 99.5);
  if (frameBright > S.maxAmbient) S.maxAmbient = frameBright;

  setText(els.calibTime, `${remaining.toFixed(1)}s`);
  setText(els.calibBright, String(Math.floor(S.maxAmbient)));
  els.calibFill.style.transform = `scaleX(${progress})`;

  if (elapsed >= CFG.calibrationDuration) finishCalibration(t);
}

function finishCalibration(t) {
  const minHits = Math.max(5, Math.floor(S.calibFrames * CFG.calibMinHitRatio));
  const { mask, zones } = buildStaticMask(S.calibAcc, minHits, S.w, S.h, S.tracker.labels, S.tracker.stack);

  S.staticMask = mask;
  S.zones = zones;
  S.calibAcc = null;
  S.calibrating = false;

  S.tracker.staticMask = mask;
  S.tracker.minBrightness = CFG.minBrightness;
  S.tracker.resetInactivity(t);

  console.info(`[CALIBRACIÓN] Finalizada. Zonas reflectivas neutralizadas: ${zones}`);
  console.info(`[COLOR] Color inicial: ${S.air.color.name}`);
  setPhase('live');
}

/** Durante la espera post-captura busca reflejos nuevos y alarga la espera si hace falta. */
function cooldownStep(data, timeInCooldown) {
  const n = S.w * S.h;
  const { staticMask, cdAcc, scratch } = S;

  S.cdFrames++;
  let count = 0;
  for (let i = 0, p = 0; i < n; i++, p += 4) {
    if (staticMask[i]) continue;
    let v = data[p];
    const g = data[p + 1], b = data[p + 2];
    if (g > v) v = g;
    if (b > v) v = b;
    if (v >= CFG.cooldownGlareLevel) scratch[count++] = i;
  }

  if (count > 10) {
    for (let k = 0; k < count; k++) cdAcc[scratch[k]]++;
    if (!S.recalibNeeded) {
      S.recalibNeeded = true;
      const extra = Math.min(CFG.maxAdditionalRecalib, CFG.recalibExtra);
      S.cooldownLimit = CFG.baseCooldown + extra;
      console.info(`[RECALIBRACIÓN] Cambios detectados en el fondo. Extendiendo espera en ${extra.toFixed(1)}s…`);
    }
  }

  if (S.recalibNeeded && !S.recalibMerged && timeInCooldown >= S.cooldownLimit - 0.15) mergeNewGlare();
}

function mergeNewGlare() {
  S.recalibMerged = true;
  const { w, h, cdAcc, staticMask } = S;
  const n = w * h;
  const minHits = Math.max(3, Math.floor(S.cdFrames * CFG.cooldownMinHitRatio));

  const raw = new Uint8Array(n);
  let count = 0;
  for (let i = 0; i < n; i++) {
    if (cdAcc[i] >= minHits) {
      raw[i] = 1;
      count++;
    }
  }
  if (count <= 5) return;

  const dilated = dilateEllipse9(raw, w, h);
  for (let i = 0; i < n; i++) if (dilated[i]) staticMask[i] = 1;
  S.zones = labelBlobs(staticMask, w, [0, 0, w - 1, h - 1], S.tracker.labels, S.tracker.stack).length;
  console.info(`[RECALIBRACIÓN COMPLETADA] Máscara actualizada. Total zonas neutralizadas: ${S.zones}`);
}

// ---------- Render ----------

function drawView() {
  const ctx = S.viewCtx;
  if (S.showMask && !S.calibrating) {
    renderMask();
    return;
  }
  ctx.globalCompositeOperation = 'source-over';
  ctx.drawImage(S.procCanvas, 0, 0);
  // Suma saturada (como cv2.add): los trazos brillan sin tapar el fondo
  ctx.globalCompositeOperation = 'lighter';
  ctx.drawImage(S.air.el, 0, 0);
  ctx.globalCompositeOperation = 'source-over';
}

/** Vista de máscara: blanco = puntero, rojo = reflejos ignorados. */
function renderMask() {
  const { w, h, staticMask, tracker } = S;
  const px = S.maskImage.data;
  const n = w * h;

  for (let i = 0, p = 0; i < n; i++, p += 4) {
    const s = staticMask[i];
    px[p] = s ? 180 : 0;
    px[p + 1] = s ? 30 : 0;
    px[p + 2] = s ? 30 : 0;
    px[p + 3] = 255;
  }

  if (tracker.roi !== null) {
    const [x0, y0, x1, y1] = tracker.roi;
    for (let y = y0; y <= y1; y++) {
      for (let x = x0, i = y * w + x0; x <= x1; x++, i++) {
        if (tracker.clean[i] && !staticMask[i]) {
          const p = i * 4;
          px[p] = px[p + 1] = px[p + 2] = 255;
        }
      }
    }
  }

  S.viewCtx.putImageData(S.maskImage, 0, 0);
}

function updateHud(t, inCooldown, detected, timerActive, sinceMove) {
  // Indicador de estado
  let mode, label;
  if (inCooldown) {
    const remaining = Math.max(0, S.cooldownLimit - (t - S.cooldownStart));
    mode = 'wait';
    label = `${S.recalibNeeded ? 'RECALIBRANDO' : 'ESPERA'} ${remaining.toFixed(1)}s`;
  } else if (detected) {
    mode = 'rec';
    label = 'REC';
  } else {
    mode = 'standby';
    label = 'STANDBY';
  }
  if (els.status.dataset.mode !== mode) els.status.dataset.mode = mode;
  setText(els.statusLabel, label);

  // Cuenta regresiva de inactividad
  els.timer.hidden = !timerActive;
  if (timerActive) {
    const remaining = Math.max(0, CFG.inactivityLimit - sinceMove);
    const progress = Math.min(1, sinceMove / CFG.inactivityLimit);
    els.timerFill.style.transform = `scaleX(${progress})`;
    els.timerFill.style.setProperty('--fill', `rgb(${Math.round(255 * (1 - progress))}, ${Math.round(200 + 55 * progress)}, 0)`);
    setText(els.timerLabel, `Auto-captura por inactividad: ${remaining.toFixed(1)}s`);
  }

  // Línea inferior y leyenda de máscara
  const key = `${S.air.index}|${S.thickness}|${S.showSlider}|${S.showMask}|${S.zones}`;
  if (key !== S.hudKey) {
    S.hudKey = key;
    els.swatch.style.background = S.air.color.css;
    setText(els.infoText, `Color: ${S.air.color.name} (Sig: ${S.air.nextColor.name}) · Grosor: ${S.thickness}px`);
    setText(els.infoHint, `· [G] ${S.showSlider ? 'Ocultar slider grosor' : 'Modificar grosor de trazo'}`);
    setText(els.maskCaption, `VISTA MÁSCARA: Blanco = Puntero | Rojo = Reflejos ignorados (${S.zones})`);
  }
}

// ---------- Capturas ----------

function capture(t) {
  saveComposite();

  els.flash.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 220, easing: 'ease-out' });
  S.captureTriggered = true;

  // Iniciar espera y preparar el acumulador de recalibración
  S.cooldownStart = t;
  S.cooldownLimit = CFG.baseCooldown;
  S.recalibNeeded = false;
  S.recalibMerged = false;
  S.cdFrames = 0;
  S.cdAcc.fill(0);

  S.air.clear();
  const prev = S.air.color.name;
  const next = S.air.advanceColor();
  console.info(`[ROTACIÓN] Foto guardada en ${prev}. Próximo color: ${next}`);
  S.tracker.resetInactivity(t);
  syncControls();
}

/** Cámara + trazos combinados en 1080p, codificados como JPEG fuera del bucle. */
function saveComposite() {
  const name = nextFileName();
  const { saveCanvas: canvas, saveCtx: ctx } = S;

  ctx.globalCompositeOperation = 'source-over';
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(S.procCanvas, 0, 0, canvas.width, canvas.height);
  ctx.globalCompositeOperation = 'lighter';
  ctx.drawImage(S.air.el, 0, 0, canvas.width, canvas.height);
  ctx.globalCompositeOperation = 'source-over';

  canvas.toBlob((blob) => {
    if (!blob) {
      showToast(`Error al guardar ${name}`);
      return;
    }
    addToGallery(name, blob);
    console.info(`[INFO] Captura guardada: ${name} (${canvas.width}x${canvas.height})`);
  }, 'image/jpeg', CFG.jpegQuality);

  showToast(`Guardado: ${name} (1080p)`);
}

function nextFileName() {
  let index = S.memIndex;
  try {
    const stored = parseInt(localStorage.getItem(COUNTER_KEY), 10);
    if (stored > index) index = stored;
    localStorage.setItem(COUNTER_KEY, String(index + 1));
  } catch {
    // Sin almacenamiento disponible: basta el contador en memoria
  }
  S.memIndex = index + 1;
  return `captura_${String(index).padStart(4, '0')}.jpg`;
}

function addToGallery(name, blob) {
  const url = URL.createObjectURL(blob);
  S.captures.push({ name, url });

  const link = document.createElement('a');
  link.className = 'shot';
  link.href = url;
  link.download = name;
  link.title = `Descargar ${name}`;

  const img = document.createElement('img');
  img.src = url;
  img.alt = name;

  const caption = document.createElement('span');
  caption.textContent = name;

  link.append(img, caption);
  const item = document.createElement('li');
  item.append(link);
  els.gallery.prepend(item);

  els.galleryEmpty.hidden = true;
  els.downloadAll.disabled = false;
  setText(els.count, String(S.captures.length));

  if (els.autoDownload.checked) triggerDownload(url, name);
}

function triggerDownload(url, name) {
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
}

async function downloadAll() {
  els.downloadAll.disabled = true;
  for (const { url, name } of S.captures) {
    triggerDownload(url, name);
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  els.downloadAll.disabled = false;
}

function showToast(message) {
  setText(els.toast, message);
  els.toast.hidden = false;
  clearTimeout(S.toastTimer);
  S.toastTimer = setTimeout(hideToast, CFG.notifyDuration * 1000);
}

function hideToast() {
  clearTimeout(S.toastTimer);
  els.toast.hidden = true;
}

// ---------- Acciones (teclado y botones) ----------

const isLive = () => S.running && !S.calibrating;

function manualSave() {
  if (!isLive()) return;
  const t = nowSec();
  if (t - S.cooldownStart < S.cooldownLimit) return;
  capture(t);
}

function clearCanvas() {
  if (!isLive()) return;
  S.air.clear();
  S.captureTriggered = false;
  console.info('[INFO] Lienzo limpiado.');
}

function toggleMask() {
  if (!isLive()) return;
  S.showMask = !S.showMask;
  els.maskCaption.hidden = !S.showMask;
  syncControls();
}

function toggleSlider() {
  if (!isLive()) return;
  S.showSlider = !S.showSlider;
  els.slider.hidden = !S.showSlider;
  syncControls();
}

function setColor(index) {
  if (!isLive()) return;
  S.air.setIndex(index);
  syncControls();
}

function runAction(action, index) {
  switch (action) {
    case 'save': manualSave(); break;
    case 'clear': clearCanvas(); break;
    case 'mask': toggleMask(); break;
    case 'slider': toggleSlider(); break;
    case 'color': setColor(index); break;
    case 'stop': stopCamera(); break;
  }
}

const KEY_ACTIONS = {
  s: ['save'],
  c: ['clear'],
  m: ['mask'],
  g: ['slider'],
  1: ['color', 0],
  2: ['color', 1],
  3: ['color', 2],
  q: ['stop'],
  escape: ['stop'],
};

function setPhase(phase) {
  els.stage.dataset.phase = phase;
  syncControls();
}

function syncControls() {
  const live = isLive();
  for (const button of els.toolbar.querySelectorAll('button[data-action]')) {
    const { action } = button.dataset;
    button.disabled = action === 'stop' ? !S.running : !live;
    if (action === 'mask') button.setAttribute('aria-pressed', String(S.showMask));
    if (action === 'slider') button.setAttribute('aria-pressed', String(S.showSlider));
    if (action === 'color') {
      const current = S.air ? S.air.index : S.colorIndex;
      button.setAttribute('aria-pressed', String(Number(button.dataset.index) === current));
    }
  }
}

// ---------- Inicio ----------

function init() {
  const $ = (id) => document.getElementById(id);
  els = {
    stage: $('stage'),
    video: $('video'),
    view: $('view'),
    startBtn: $('start-btn'),
    startError: $('start-error'),
    calibTime: $('calib-time'),
    calibBright: $('calib-bright'),
    calibFill: $('calib-fill'),
    timer: $('timer'),
    timerFill: $('timer-fill'),
    timerLabel: $('timer-label'),
    slider: $('slider'),
    thickness: $('thickness'),
    thicknessValue: $('thickness-value'),
    status: $('status'),
    statusLabel: $('status-label'),
    maskCaption: $('mask-caption'),
    toast: $('toast'),
    swatch: $('swatch'),
    infoText: $('info-text'),
    infoHint: $('info-hint'),
    flash: $('flash'),
    toolbar: $('toolbar'),
    count: $('count'),
    autoDownload: $('auto-download'),
    downloadAll: $('download-all'),
    galleryEmpty: $('gallery-empty'),
    gallery: $('gallery'),
  };

  els.startBtn.addEventListener('click', startCamera);

  els.toolbar.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    if (button && !button.disabled) runAction(button.dataset.action, Number(button.dataset.index));
  });

  document.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.repeat || !S.running) return;
    const entry = KEY_ACTIONS[event.key.toLowerCase()];
    if (!entry) return;
    if (S.calibrating && entry[0] !== 'stop') return;
    event.preventDefault();
    runAction(...entry);
  });

  els.thickness.value = String(S.thickness);
  els.thickness.addEventListener('input', () => {
    S.thickness = Number(els.thickness.value);
    if (S.air) S.air.setThickness(S.thickness);
    els.thicknessValue.value = `${S.thickness}px`;
  });

  try {
    const stored = localStorage.getItem(AUTO_DOWNLOAD_KEY);
    if (stored !== null) els.autoDownload.checked = stored === '1';
  } catch {
    // preferencia no disponible: se usa el valor por defecto
  }
  els.autoDownload.addEventListener('change', () => {
    try {
      localStorage.setItem(AUTO_DOWNLOAD_KEY, els.autoDownload.checked ? '1' : '0');
    } catch {
      // sin almacenamiento
    }
  });

  els.downloadAll.addEventListener('click', downloadAll);
  syncControls();
}

if (typeof document !== 'undefined') init();
