import {
  FilesetResolver,
  HandLandmarker,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs";

const boton = document.getElementById("iniciar");
const canvas = document.getElementById("lienzo");
const ctx = canvas.getContext("2d");

let frecuenciaActual = 440;
let volumenActual = 0.2;
let efectoMix = 0;      // Qué tanto eco se escucha (0 = nada, 1 = máximo)
let efectoFeedback = 0; // Cuántas veces se repite el eco

function distancia(p1, p2) {
  return Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
}

// Igual que np.interp: mapea x de [x0, x1] a [y0, y1] limitando a los extremos
function interp(x, [x0, x1], [y0, y1]) {
  if (x <= x0) return y0;
  if (x >= x1) return y1;
  return y0 + ((x - x0) * (y1 - y0)) / (x1 - x0);
}

function circulo(p, radio, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(p[0], p[1], radio, 0, Math.PI * 2);
  ctx.fill();
}

function linea(p1, p2, color, grosor) {
  ctx.strokeStyle = color;
  ctx.lineWidth = grosor;
  ctx.beginPath();
  ctx.moveTo(p1[0], p1[1]);
  ctx.lineTo(p2[0], p2[1]);
  ctx.stroke();
}

boton.onclick = async () => {
  boton.disabled = true;
  boton.textContent = "Cargando...";

  try {
    // --- AUDIO CON ECO (DELAY) ---
    // oscilador → volumen → seco ───────────────→ salida
    //                     └→ delay (0.4 s) → mojado → salida
    //                          ↑__ feedback __|
    const audio = new AudioContext();
    const oscilador = audio.createOscillator();
    const volumen = audio.createGain();
    const seco = audio.createGain();
    const mojado = audio.createGain();
    const delay = audio.createDelay(1.0);
    const feedback = audio.createGain();

    delay.delayTime.value = 0.4;
    oscilador.connect(volumen);
    volumen.connect(seco).connect(audio.destination);
    volumen.connect(delay);
    delay.connect(mojado).connect(audio.destination);
    delay.connect(feedback).connect(delay);
    oscilador.start();

    // --- MEDIAPIPE HANDS ---
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm"
    );
    const detector = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numHands: 2,
      minHandDetectionConfidence: 0.5,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });

    // --- CÁMARA ---
    const video = document.createElement("video");
    video.playsInline = true;
    video.muted = true;
    video.srcObject = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "user" },
    });
    await video.play();

    const ancho = (canvas.width = video.videoWidth);
    const alto = (canvas.height = video.videoHeight);
    let ultimoTiempo = -1;

    function cuadro() {
      // Dibujar la cámara en espejo
      ctx.save();
      ctx.translate(ancho, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, ancho, alto);
      ctx.restore();

      const tiempo = Math.max(performance.now(), ultimoTiempo + 1);
      ultimoTiempo = tiempo;
      const resultado = detector.detectForVideo(canvas, tiempo);

      let manoDerDetectada = false;

      resultado.landmarks.forEach((mano, i) => {
        const etiqueta = resultado.handedness[i][0].categoryName; // "Left" o "Right"
        const pulgar = [mano[4].x * ancho, mano[4].y * alto];
        const indice = [mano[8].x * ancho, mano[8].y * alto];

        linea(pulgar, indice, "white", 2);
        circulo(pulgar, 6, "lime");
        circulo(indice, 6, "blue");

        const distPx = distancia(pulgar, indice);

        if (etiqueta === "Right") {
          // MANO DERECHA: controla el tono
          manoDerDetectada = true;
          const frecuenciaObjetivo = interp(distPx, [20, 180], [200, 800]);
          frecuenciaActual = frecuenciaActual * 0.7 + frecuenciaObjetivo * 0.3;
        } else {
          // MANO IZQUIERDA: controla el eco
          const mixObjetivo = interp(distPx, [20, 180], [0, 0.85]);
          const feedbackObjetivo = interp(distPx, [20, 180], [0, 0.8]);
          efectoMix = efectoMix * 0.6 + mixObjetivo * 0.4;
          efectoFeedback = efectoFeedback * 0.6 + feedbackObjetivo * 0.4;
        }
      });

      // Sin mano derecha el volumen baja gradualmente
      volumenActual = volumenActual * 0.8 + (manoDerDetectada ? 0.2 : 0) * 0.2;

      const t = audio.currentTime;
      oscilador.frequency.setTargetAtTime(frecuenciaActual, t, 0.02);
      volumen.gain.setTargetAtTime(volumenActual, t, 0.02);
      seco.gain.setTargetAtTime(1 - efectoMix, t, 0.02);
      mojado.gain.setTargetAtTime(efectoMix, t, 0.02);
      feedback.gain.setTargetAtTime(efectoFeedback, t, 0.02);

      document.getElementById("nota").textContent = Math.round(frecuenciaActual);
      document.getElementById("barraNota").value = frecuenciaActual;
      document.getElementById("espacio").textContent = Math.round(efectoMix * 100);
      document.getElementById("barraEspacio").value = efectoMix;

      requestAnimationFrame(cuadro);
    }
    requestAnimationFrame(cuadro);

    boton.hidden = true;
  } catch (error) {
    console.error(error);
    boton.textContent = "Error: " + error.message;
  }
};
