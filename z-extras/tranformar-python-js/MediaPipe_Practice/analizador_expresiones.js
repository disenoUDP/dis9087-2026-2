import { botonIniciar, crearRostro, iniciar, distancia, circulo, aPixeles } from "./comun.js";

const info = document.getElementById("info");

// Contadores y estados de activación de cada gesto
const contadores = {
  "Parpadeos": 0, "Habla": 0, "Sonrisas": 0, "Boca fruncida": 0,
  "Tristeza": 0, "Cejas arriba": 0, "Cejas fruncidas": 0,
};
const activos = {};

// Suma 1 solo cuando el gesto pasa de inactivo a activo
function contar(gesto, condicion) {
  if (condicion && !activos[gesto]) contadores[gesto]++;
  activos[gesto] = condicion;
}

function mostrarContadores() {
  info.textContent = Object.entries(contadores)
    .map(([gesto, valor]) => `${gesto}: ${valor}`)
    .join("\n");
}
mostrarContadores();

botonIniciar(async () => {
  const detector = await crearRostro();

  await iniciar(detector, (resultado, ctx, ancho, alto) => {
    const rostro = resultado.faceLandmarks[0];
    if (!rostro) return;

    const puntos = aPixeles(rostro, ancho, alto);
    for (const idx of [159, 145, 0, 17, 61, 291, 105, 334, 70, 468, 234, 454]) {
      circulo(ctx, puntos[idx], 3, "lime");
    }

    const ojoSup = puntos[159], ojoInf = puntos[145];
    const labioSup = puntos[0], labioInf = puntos[17];
    const comisuraIzq = puntos[61], comisuraDer = puntos[291];
    const cejaIzqInt = puntos[105], cejaDerInt = puntos[334];
    const cejaIzqExt = puntos[70], pupilaIzq = puntos[468];
    const rostroIzq = puntos[234], rostroDer = puntos[454];

    // Escala de referencia (ancho del rostro)
    const escala = distancia(rostroIzq, rostroDer) || 1;

    // 1. PARPADEO
    contar("Parpadeos", distancia(ojoSup, ojoInf) / escala < 0.035);

    // 2. HABLA (BOCA ABIERTA)
    const relBocaV = distancia(labioSup, labioInf) / escala;
    contar("Habla", relBocaV > 0.09);

    // 3. SONRISA (BOCA ESTIRADA)
    const relBocaH = distancia(comisuraIzq, comisuraDer) / escala;
    contar("Sonrisas", relBocaH > 0.36);

    // 4. FRUNCIR BOCA (boca de beso)
    contar("Boca fruncida", relBocaH < 0.32 && relBocaV < 0.07);

    // 5. ENTRISTECE BOCA (comisuras hacia abajo)
    const promedioComisurasY = (comisuraIzq[1] + comisuraDer[1]) / 2;
    contar("Tristeza", promedioComisurasY - labioInf[1] > -10);

    // 6. ALZAR LAS CEJAS
    contar("Cejas arriba", distancia(cejaIzqExt, pupilaIzq) / escala > 0.22);

    // 7. FRUNCIR CEJAS (se juntan las cejas)
    contar("Cejas fruncidas", distancia(cejaIzqInt, cejaDerInt) / escala < 0.24);

    mostrarContadores();
  });
});
