import { botonIniciar, crearManos, iniciar, distancia, interp, linea, circulo, aPixeles } from "./comun.js";

let frecuenciaActual = 440;
let volumenActual = 0.2;
let efectoMix = 0;      // Qué tanto eco se escucha (0 = nada, 1 = máximo)
let efectoFeedback = 0; // Cuántas veces se repite el eco

botonIniciar(async () => {
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

  const detector = await crearManos(0.5);

  await iniciar(detector, (resultado, ctx, ancho, alto) => {
    let manoDerDetectada = false;

    resultado.landmarks.forEach((mano, i) => {
      const etiqueta = resultado.handedness[i][0].categoryName; // "Left" o "Right"
      const puntos = aPixeles(mano, ancho, alto);
      const pulgar = puntos[4], indice = puntos[8];

      linea(ctx, pulgar, indice, "white", 2);
      circulo(ctx, pulgar, 6, "lime");
      circulo(ctx, indice, 6, "blue");

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
  });
});
