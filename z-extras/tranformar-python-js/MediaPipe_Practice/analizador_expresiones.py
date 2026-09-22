import cv2
import mediapipe as mp
import math

# Inicializar MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1, 
    refine_landmarks=True, 
    min_detection_confidence=0.5, 
    min_tracking_confidence=0.5
)

# Variables de conteo y estados de activación
contadores = {
    "parpadeos": 0, "habla": 0, "sonrisas": 0,
    "boca_fruncida": 0, "tristeza": 0, "cejas_arriba": 0, "cejas_fruncidas": 0
}

estados = {
    "parpadeo": False, "habla": False, "sonrisa": False,
    "boca_fruncida": False, "tristeza": False, "cejas_arriba": False, "cejas_fruncidas": False
}

def calcular_distancia(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, image = cap.read()
    if not success: break

    image = cv2.flip(image, 1)
    height, width, _ = image.shape
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_image)
    puntos = {}

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            # Índices clave fijos de MediaPipe
            indices_clave = [159, 145, 0, 17, 61, 291, 105, 334, 70, 468, 234, 454]
            
            for idx in indices_clave:
                if idx < len(face_landmarks.landmark):
                    lk = face_landmarks.landmark[idx]
                    puntos[idx] = (int(lk.x * width), int(lk.y * height))
                    cv2.circle(image, puntos[idx], 3, (0, 255, 0), -1)

            if len(puntos) < len(indices_clave): continue

            # --- ASIGNACIÓN EXPLÍCITA DE PUNTOS PARA EVITAR ERRORES ---
            ojo_sup, ojo_inf = puntos[159], puntos[145]
            labio_sup, labio_inf = puntos[0], puntos[17]
            comisura_izq, comisura_der = puntos[61], puntos[291]
            ceja_izq_int, ceja_der_int = puntos[105], puntos[334]
            ceja_izq_ext, pupila_izq = puntos[70], puntos[468]
            rostro_izq, rostro_der = puntos[234], puntos[454]

            # Escala de referencia (Ancho del rostro)
            escala = calcular_distancia(rostro_izq, rostro_der)
            if escala == 0: escala = 1

            # 1. PARPADEO
            rel_ojo = calcular_distancia(ojo_sup, ojo_inf) / escala
            if rel_ojo < 0.035:
                if not estados["parpadeo"]:
                    contadores["parpadeos"] += 1
                    estados["parpadeo"] = True
            else: estados["parpadeo"] = False

            # 2. HABLA (BOCA ABIERTA)
            rel_boca_v = calcular_distancia(labio_sup, labio_inf) / escala
            if rel_boca_v > 0.09:
                if not estados["habla"]:
                    contadores["habla"] += 1
                    estados["habla"] = True
            else: estados["habla"] = False

            # 3. SONRISA (BOCA ESTIRADA)
            rel_boca_h = calcular_distancia(comisura_izq, comisura_der) / escala
            if rel_boca_h > 0.36:
                if not estados["sonrisa"]:
                    contadores["sonrisas"] += 1
                    estados["sonrisa"] = True
            else: estados["sonrisa"] = False

            # 4. FRUNCIR BOCA (Boca de beso - Umbral más amplio para tus facciones: 0.32)
            if rel_boca_h < 0.32 and rel_boca_v < 0.07:
                if not estados["boca_fruncida"]:
                    contadores["boca_fruncida"] += 1
                    estados["boca_fruncida"] = True
            else: estados["boca_fruncida"] = False

            # 5. ENTRISTECE BOCA (Comisuras hacia abajo - Mucho más sensible)
            promedio_comisuras_y = (comisura_izq[1] + comisura_der[1]) / 2
            if (promedio_comisuras_y - labio_inf[1]) > -10: 
                if not estados["tristeza"]:
                    contadores["tristeza"] += 1
                    estados["tristeza"] = True
            else: estados["tristeza"] = False

            # 6. ALZAR LAS CEJAS
            rel_ceja_arriba = calcular_distancia(ceja_izq_ext, pupila_izq) / escala
            if rel_ceja_arriba > 0.22:
                if not estados["cejas_arriba"]:
                    contadores["cejas_arriba"] += 1
                    estados["cejas_arriba"] = True
            else: estados["cejas_arriba"] = False

            # 7. FRUNCIR CEJAS (Se juntan las cejas - Umbral ajustado según tu foto a 0.24)
            rel_cejas_juntas = calcular_distancia(ceja_izq_int, ceja_der_int) / escala
            if rel_cejas_juntas < 0.24:
                if not estados["cejas_fruncidas"]:
                    contadores["cejas_fruncidas"] += 1
                    estados["cejas_fruncidas"] = True
            else: estados["cejas_fruncidas"] = False

    # --- PANEL VISUAL DE CONTADORES ---
    cv2.rectangle(image, (10, 10), (340, 270), (20, 20, 20), -1)
    y_offset = 40
    for g, valor in contadores.items():
        texto = f"{g.replace('_', ' ').capitalize()}: {valor}"
        cv2.putText(image, texto, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 32

    cv2.imshow('Analizador Completo de Rostro', image)
    if cv2.waitKey(5) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()