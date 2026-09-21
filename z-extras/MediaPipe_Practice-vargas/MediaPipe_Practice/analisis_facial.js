import { botonIniciar, crearRostro, iniciar, distancia, linea, aPixeles } from "./comun.js";

const info = document.getElementById("info");

botonIniciar(async () => {
  const detector = await crearRostro();

  await iniciar(detector, (resultado, ctx, ancho, alto) => {
    const rostro = resultado.faceLandmarks[0];
    if (!rostro) return;

    const puntos = aPixeles(rostro, ancho, alto);

    // Dibujar un punto diminuto para CADA uno de los 478 puntos
    ctx.fillStyle = "yellow";
    for (const [x, y] of puntos) ctx.fillRect(x - 1, y - 1, 2, 2);

    // --- MAPA DE PUNTOS ESPECÍFICOS ---
    const ojoIzqSup = puntos[159], ojoIzqInf = puntos[145];
    const ojoDerSup = puntos[386], ojoDerInf = puntos[374];
    const cejaIzq = puntos[52];
    const bocaSup = puntos[13], bocaInf = puntos[14];
    const bocaIzq = puntos[61], bocaDer = puntos[291];
    const narizAlta = puntos[168], narizBaja = puntos[2];

    // --- CÁLCULO DE DISTANCIAS ---
    const aperturaOjoIzq = distancia(ojoIzqSup, ojoIzqInf);
    const aperturaOjoDer = distancia(ojoDerSup, ojoDerInf);
    const sorpresaIzq = distancia(cejaIzq, ojoIzqSup);
    const aperturaBocaV = distancia(bocaSup, bocaInf);
    const anchoBocaH = distancia(bocaIzq, bocaDer);
    const largoNariz = distancia(narizAlta, narizBaja);

    // --- DIBUJAR LÍNEAS DE MEDICIÓN ---
    linea(ctx, ojoIzqSup, ojoIzqInf, "lime");
    linea(ctx, cejaIzq, ojoIzqSup, "blue");
    linea(ctx, bocaSup, bocaInf, "red");
    linea(ctx, bocaIzq, bocaDer, "red");
    linea(ctx, narizAlta, narizBaja, "cyan");

    info.textContent =
      `Apertura Ojo Izq: ${aperturaOjoIzq.toFixed(1)}px\n` +
      `Apertura Ojo Der: ${aperturaOjoDer.toFixed(1)}px\n` +
      `Dist. Ceja-Ojo: ${sorpresaIzq.toFixed(1)}px\n` +
      `Alto Boca V: ${aperturaBocaV.toFixed(1)}px\n` +
      `Ancho Boca H: ${anchoBocaH.toFixed(1)}px\n` +
      `Largo Nariz: ${largoNariz.toFixed(1)}px`;
  });
});
