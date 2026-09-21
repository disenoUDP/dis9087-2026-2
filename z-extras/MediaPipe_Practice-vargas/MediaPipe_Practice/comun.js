// Código compartido por todas las páginas: MediaPipe, cámara y bucle de dibujo
import {
  FilesetResolver,
  FaceLandmarker,
  HandLandmarker,
  DrawingUtils,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs";

export { HandLandmarker, DrawingUtils };

const WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm";
const MODELOS = "https://storage.googleapis.com/mediapipe-models";

// Equivalente a mp.solutions.face_mesh con refine_landmarks=True (478 puntos, incluye iris)
export async function crearRostro() {
  const vision = await FilesetResolver.forVisionTasks(WASM);
  return FaceLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: `${MODELOS}/face_landmarker/face_landmarker/float16/1/face_landmarker.task`,
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numFaces: 1,
    minFaceDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
}

// Equivalente a mp.solutions.hands
export async function crearManos(confianza) {
  const vision = await FilesetResolver.forVisionTasks(WASM);
  return HandLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: `${MODELOS}/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`,
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numHands: 2,
    minHandDetectionConfidence: confianza,
    minHandPresenceConfidence: confianza,
    minTrackingConfidence: confianza,
  });
}

// Conecta el botón "Iniciar". El código antes del primer await corre dentro del clic
// (necesario para crear un AudioContext).
export function botonIniciar(configurar) {
  const boton = document.getElementById("iniciar");
  boton.onclick = async () => {
    boton.disabled = true;
    boton.textContent = "Cargando...";
    try {
      await configurar();
      boton.hidden = true;
    } catch (error) {
      console.error(error);
      boton.textContent = "Error: " + error.message;
    }
  };
}

// Abre la cámara y en cada cuadro: dibuja el video en espejo (cv2.flip),
// detecta con MediaPipe y llama a procesar(resultado, ctx, ancho, alto)
export async function iniciar(detector, procesar) {
  const video = document.createElement("video");
  video.playsInline = true;
  video.muted = true;
  video.srcObject = await navigator.mediaDevices.getUserMedia({
    video: { width: 640, height: 480, facingMode: "user" },
  });
  await video.play();

  const canvas = document.getElementById("lienzo");
  const ancho = (canvas.width = video.videoWidth);
  const alto = (canvas.height = video.videoHeight);
  const ctx = canvas.getContext("2d");
  let ultimoTiempo = -1;

  function cuadro() {
    ctx.save();
    ctx.translate(ancho, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, ancho, alto);
    ctx.restore();

    const tiempo = Math.max(performance.now(), ultimoTiempo + 1);
    ultimoTiempo = tiempo;
    procesar(detector.detectForVideo(canvas, tiempo), ctx, ancho, alto);
    requestAnimationFrame(cuadro);
  }
  requestAnimationFrame(cuadro);
}

// --- Utilidades de dibujo y cálculo ---

export function distancia(p1, p2) {
  return Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
}

// Igual que np.interp: mapea x de [x0, x1] a [y0, y1] limitando a los extremos
export function interp(x, [x0, x1], [y0, y1]) {
  if (x <= x0) return y0;
  if (x >= x1) return y1;
  return y0 + ((x - x0) * (y1 - y0)) / (x1 - x0);
}

export function circulo(ctx, p, radio, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(p[0], p[1], radio, 0, Math.PI * 2);
  ctx.fill();
}

export function linea(ctx, p1, p2, color, grosor = 1) {
  ctx.strokeStyle = color;
  ctx.lineWidth = grosor;
  ctx.beginPath();
  ctx.moveTo(p1[0], p1[1]);
  ctx.lineTo(p2[0], p2[1]);
  ctx.stroke();
}

// Convierte los puntos normalizados (0-1) de MediaPipe a píxeles
export function aPixeles(landmarks, ancho, alto) {
  return landmarks.map((lm) => [lm.x * ancho, lm.y * alto]);
}
