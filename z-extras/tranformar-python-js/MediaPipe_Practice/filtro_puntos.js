import { botonIniciar, crearManos, iniciar, circulo } from "./comun.js";

// Canvas auxiliar para reducir la resolución de la zona
const temporal = document.createElement("canvas");
const tctx = temporal.getContext("2d");

botonIniciar(async () => {
  const detector = await crearManos(0.7);

  await iniciar(detector, (resultado, ctx, ancho, alto) => {
    // Punto 4 = punta del pulgar, punto 8 = punta del índice
    const puntosControl = [];
    for (const mano of resultado.landmarks) {
      puntosControl.push([mano[4].x * ancho, mano[4].y * alto]);
      puntosControl.push([mano[8].x * ancho, mano[8].y * alto]);
    }

    // Solo se activa el filtro cuando se ven los 4 dedos (2 manos)
    if (puntosControl.length === 4) {
      const xs = puntosControl.map((p) => p[0]);
      const ys = puntosControl.map((p) => p[1]);
      const xMin = Math.floor(Math.max(0, Math.min(...xs)));
      const yMin = Math.floor(Math.max(0, Math.min(...ys)));
      const xMax = Math.floor(Math.min(ancho, Math.max(...xs)));
      const yMax = Math.floor(Math.min(alto, Math.max(...ys)));
      const w = xMax - xMin, h = yMax - yMin;

      // Evitar cálculos si los dedos están demasiado pegados
      if (w > 20 && h > 20) {
        // Tamaño de bloque: sube el 15 a 30 o 40 para píxeles más grandes
        const bloquesAncho = Math.max(1, Math.floor(w / 15));
        const bloquesAlto = Math.max(1, Math.floor(h / 15));

        // Reducir la resolución de la zona y volver a escalarla sin suavizado
        temporal.width = bloquesAncho;
        temporal.height = bloquesAlto;
        tctx.drawImage(ctx.canvas, xMin, yMin, w, h, 0, 0, bloquesAncho, bloquesAlto);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(temporal, 0, 0, bloquesAncho, bloquesAlto, xMin, yMin, w, h);
        ctx.imageSmoothingEnabled = true;

        ctx.strokeStyle = "cyan";
        ctx.lineWidth = 2;
        ctx.strokeRect(xMin, yMin, w, h);
      }
    }

    for (const p of puntosControl) circulo(ctx, p, 6, "yellow");
  });
});
