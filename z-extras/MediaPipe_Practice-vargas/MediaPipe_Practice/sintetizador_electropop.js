import { botonIniciar, crearManos, iniciar, HandLandmarker, DrawingUtils } from "./comun.js";

const info = document.getElementById("info");
const MUESTREO = 44100;

// Crea un buffer de audio llenándolo con fn(t) para cada muestra
function crearSonido(audio, duracion, fn) {
  const buffer = audio.createBuffer(1, Math.floor(MUESTREO * duracion), MUESTREO);
  const datos = buffer.getChannelData(0);
  for (let i = 0; i < datos.length; i++) datos[i] = fn(i / MUESTREO);
  return buffer;
}

// Onda cuadrada tipo synth
function tonoSynth(audio, frecuencia, duracion = 0.3) {
  return crearSonido(audio, duracion, (t) => Math.sign(Math.sin(2 * Math.PI * frecuencia * t)) * 0.37);
}

function percusion(audio, tipo, duracion = 0.15) {
  return crearSonido(audio, duracion, (t) => {
    const ruido = Math.random() * 2 - 1;
    if (tipo === "bombo") return Math.sin(2 * Math.PI * 150 * Math.exp(-40 * t) * t) * 0.76;
    if (tipo === "tarola") return (ruido * 0.7 + Math.sin(2 * Math.PI * 180 * t) * Math.exp(-20 * t) * 0.3) * 0.55;
    return ruido * Math.exp(-80 * t) * 0.46; // hihat
  });
}

botonIniciar(async () => {
  const audio = new AudioContext();

  // Pre-cargar sonidos (índice 1 a 4 = índice, medio, anular, meñique)
  const sonidos = {
    RITMO: [null, percusion(audio, "bombo"), percusion(audio, "tarola"), percusion(audio, "hihat"), percusion(audio, "hihat", 0.3)],
    MELODIA: [null, tonoSynth(audio, 261.63), tonoSynth(audio, 329.63), tonoSynth(audio, 392.0), tonoSynth(audio, 493.88)],
    SAMPLES: [null, tonoSynth(audio, 130.81, 0.6), tonoSynth(audio, 164.81, 0.6), tonoSynth(audio, 196.0, 0.6), tonoSynth(audio, 220.0, 0.6)],
    EFECTOS_VOZ: [null, tonoSynth(audio, 523.25), tonoSynth(audio, 659.25), tonoSynth(audio, 783.99), tonoSynth(audio, 987.77)],
  };

  function tocar(buffer) {
    const fuente = audio.createBufferSource();
    fuente.buffer = buffer;
    fuente.connect(audio.destination);
    fuente.start();
  }

  const estadosAnteriores = { LEFT: [false, false, false, false, false], RIGHT: [false, false, false, false, false] };

  const detector = await crearManos(0.7);
  let dibujo;

  await iniciar(detector, (resultado, ctx) => {
    dibujo ??= new DrawingUtils(ctx);
    const manosDetectadas = [];
    const textos = [];

    resultado.landmarks.forEach((mano, i) => {
      const etiqueta = resultado.handedness[i][0].categoryName; // "Left" o "Right"
      // Invertimos la etiqueta por el efecto espejo para que coincida con tu cuerpo real
      const manoClave = etiqueta === "Left" ? "RIGHT" : "LEFT";
      manosDetectadas.push(manoClave);

      dibujo.drawConnectors(mano, HandLandmarker.HAND_CONNECTIONS, { color: "white", lineWidth: 2 });
      dibujo.drawLandmarks(mano, { color: "red", radius: 2 });

      // Pulgar: punta (4) vs nudillo (2) en el eje X
      const pulgarArriba = manoClave === "LEFT" ? mano[4].x < mano[2].x : mano[4].x > mano[2].x;

      const modo = manoClave === "LEFT"
        ? (pulgarArriba ? "SAMPLES" : "RITMO")
        : (pulgarArriba ? "EFECTOS_VOZ" : "MELODIA");

      // Otros 4 dedos: punta por encima del nudillo medio en el eje Y
      [8, 12, 16, 20].forEach((punta, j) => {
        const numDedo = j + 1;
        const levantado = mano[punta].y < mano[punta - 2].y;
        if (levantado && !estadosAnteriores[manoClave][numDedo]) {
          tocar(sonidos[modo][numDedo]);
        }
        estadosAnteriores[manoClave][numDedo] = levantado;
      });

      textos.push(`${manoClave}: ${modo}`);
    });

    // Resetear estados de manos que salieron de la cámara
    for (const m of ["LEFT", "RIGHT"]) {
      if (!manosDetectadas.includes(m)) estadosAnteriores[m] = [false, false, false, false, false];
    }

    info.textContent = textos.sort().join("\n") || "Sin manos detectadas";
  });
});
