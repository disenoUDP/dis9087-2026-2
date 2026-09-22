import { botonIniciar, crearRostro, iniciar, distancia, interp, linea, circulo, aPixeles } from "./comun.js";

let frecuenciaActual = 440;
let volumenActual = 0;

botonIniciar(async () => {
  // --- AUDIO: onda senoidal continua ---
  const audio = new AudioContext();
  const oscilador = audio.createOscillator();
  const ganancia = audio.createGain();
  oscilador.type = "sine";
  ganancia.gain.value = 0;
  oscilador.connect(ganancia).connect(audio.destination);
  oscilador.start();

  const detector = await crearRostro();

  await iniciar(detector, (resultado, ctx, ancho, alto) => {
    const rostro = resultado.faceLandmarks[0];

    if (rostro) {
      const puntos = aPixeles(rostro, ancho, alto);

      // Calibración dinámica por iris (constante biométrica ~1.17 cm)
      const irisPx = distancia(puntos[469], puntos[471]);
      const cmPorPixel = 1.17 / (irisPx || 1);

      const bocaSup = puntos[13], bocaInf = puntos[14];
      const ojoSup = puntos[159], ojoInf = puntos[145];

      const bocaCm = distancia(bocaSup, bocaInf) * cmPorPixel;
      const ojoCm = distancia(ojoSup, ojoInf) * cmPorPixel;

      linea(ctx, bocaSup, bocaInf, "red", 2);
      linea(ctx, ojoSup, ojoInf, "yellow", 2);
      circulo(ctx, bocaSup, 3, "red");
      circulo(ctx, ojoSup, 3, "yellow");

      // --- MAPEO A PARÁMETROS MUSICALES ---
      // Boca de 0.1 a 3.5 cm → 200 Hz (grave) a 1000 Hz (agudo)
      const frecuenciaObjetivo = interp(bocaCm, [0.1, 3.5], [200, 1000]);
      // Ojo de 0.2 a 1.1 cm → volumen de 0.0 a 0.4
      const volumenObjetivo = interp(ojoCm, [0.2, 1.1], [0, 0.4]);

      // Suavizado para evitar cambios bruscos
      frecuenciaActual = frecuenciaActual * 0.7 + frecuenciaObjetivo * 0.3;
      volumenActual = volumenActual * 0.6 + volumenObjetivo * 0.4;
    } else {
      // Si no hay rostro, apagar el sonido gradualmente
      volumenActual *= 0.5;
    }

    oscilador.frequency.setTargetAtTime(frecuenciaActual, audio.currentTime, 0.02);
    ganancia.gain.setTargetAtTime(volumenActual, audio.currentTime, 0.02);

    document.getElementById("tono").textContent = Math.round(frecuenciaActual);
    document.getElementById("barraTono").value = frecuenciaActual;
    document.getElementById("volumen").textContent = Math.round(volumenActual * 250);
    document.getElementById("barraVolumen").value = volumenActual;
  });
});
