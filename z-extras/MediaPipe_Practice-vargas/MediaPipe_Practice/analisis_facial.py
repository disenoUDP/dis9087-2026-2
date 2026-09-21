import cv2
import mediapipe as mp
import math

# Inicializar MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True, # Activa los puntos ultra-precisos del iris y párpados
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Función rápida para calcular distancia en píxeles
def calcular_distancia(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

# Iniciar la cámara web
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break
        
    frame = cv2.flip(frame, 1)
    alto, ancho, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            # Convertir todos los puntos a coordenadas de píxeles (X, Y)
            puntos = []
            for lm in face_landmarks.landmark:
                x, y = int(lm.x * ancho), int(lm.y * alto)
                puntos.append((x, y))
                # Dibujar un punto diminuto para CADA uno de los más de 460 puntos
                cv2.circle(frame, (x, y), 1, (0, 255, 255), -1)
            
            # --- MAPA DE PUNTOS ESPECÍFICOS ---
            # Ojo Izquierdo (Párpado superior e inferior)
            p_ojo_izq_sup = puntos[159]
            p_ojo_izq_inf = puntos[145]
            
            # Ojo Derecho (Párpado superior e inferior)
            p_ojo_der_sup = puntos[386]
            p_ojo_der_inf = puntos[374]
            
            # Cejas y Ojos (Distancia vertical para sorpresa/enojo)
            p_ceja_izq = puntos[52]
            p_ceja_der = puntos[282]
            
            # Boca (Apertura vertical y ancho horizontal)
            p_boca_sup = puntos[13]
            p_boca_inf = puntos[14]
            p_boca_izq = puntos[61]
            p_boca_der = puntos[291]
            
            # Nariz (Longitud del tabique)
            p_nariz_alta = puntos[168] # Entre las cejas
            p_nariz_baja = puntos[2]   # Punta de la nariz

            # --- CÁLCULO DE DISTANCIAS ---
            apertura_ojo_izq = calcular_distancia(p_ojo_izq_sup, p_ojo_izq_inf)
            apertura_ojo_der = calcular_distancia(p_ojo_der_sup, p_ojo_der_inf)
            sorpresa_izq = calcular_distancia(p_ceja_izq, p_ojo_izq_sup)
            apertura_boca_v = calcular_distancia(p_boca_sup, p_boca_inf)
            ancho_boca_h = calcular_distancia(p_boca_izq, p_boca_der)
            largo_nariz = calcular_distancia(p_nariz_alta, p_nariz_baja)

            # --- DIBUJAR LÍNEAS DE MEDICIÓN ---
            cv2.line(frame, p_ojo_izq_sup, p_ojo_izq_inf, (0, 255, 0), 1)
            cv2.line(frame, p_ceja_izq, p_ojo_izq_sup, (255, 0, 0), 1)
            cv2.line(frame, p_boca_sup, p_boca_inf, (0, 0, 255), 1)
            cv2.line(frame, p_boca_izq, p_boca_der, (0, 0, 255), 1)
            cv2.line(frame, p_nariz_alta, p_nariz_baja, (255, 255, 0), 1)

            # --- RENDERIZAR TEXTO (OpenCV Nativo) ---
            # Usamos un texto compacto en la esquina superior izquierda para no obstruir la cara
            fuente = cv2.FONT_HERSHEY_SIMPLEX
            escala = 0.5
            color_txt = (255, 255, 255)
            grosor = 1
            
            cv2.putText(frame, f"Apertura Ojo Izq: {apertura_ojo_izq:.1f}px", (20, 30), fuente, escala, color_txt, grosor)
            cv2.putText(frame, f"Apertura Ojo Der: {apertura_ojo_der:.1f}px", (20, 55), fuente, escala, color_txt, grosor)
            cv2.putText(frame, f"Dist. Ceja-Ojo: {sorpresa_izq:.1f}px", (20, 80), fuente, escala, color_txt, grosor)
            cv2.putText(frame, f"Alto Boca V: {apertura_boca_v:.1f}px", (20, 105), fuente, escala, color_txt, grosor)
            cv2.putText(frame, f"Ancho Boca H: {ancho_boca_h:.1f}px", (20, 130), fuente, escala, color_txt, grosor)
            cv2.putText(frame, f"Largo Nariz: {largo_nariz:.1f}px", (20, 155), fuente, escala, color_txt, grosor)
            
    cv2.imshow('Analisis Facial Especifico - Distancias', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
