import cv2
import mediapipe as mp
import numpy as np
import sounddevice as sd
import math

# --- CONFIGURACIÓN DE AUDIO SINTETIZADO ---
SAMP_RATE = 44100  # Frecuencia de muestreo estándar
frecuencia_actual = 440.0
volumen_actual = 0.0

# Generador de onda senoidal continua en tiempo real
def audio_callback(outdata, frames, time, status):
    global frecuencia_actual, volumen_actual
    # Crear un índice de tiempo para los frames solicitados
    t = (np.arange(frames) + audio_callback.index) / SAMP_RATE
    # Generar la onda senoidal pura basada en los gestos faciales
    wave = volumen_actual * np.sin(2 * np.pi * frecuencia_actual * t)
    outdata[:] = wave.reshape(-1, 1)
    audio_callback.index += frames

audio_callback.index = 0

# Inicializar flujo de audio de baja latencia
stream = sd.OutputStream(channels=1, callback=audio_callback, samplerate=SAMP_RATE)
stream.start()

# --- CONFIGURACIÓN DE MEDIAPIPE ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

def calcular_distancia(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

# Iniciar cámara
cap = cv2.VideoCapture(0)

print("¡Instrumento iniciado! Gesticula frente a la cámara para generar sonido. Presiona 'q' para salir.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
        
    frame = cv2.flip(frame, 1)
    alto, ancho, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    # Crear panel visual para ver las ondas del instrumento
    panel_instrumento = np.zeros((250, 450, 3), dtype=np.uint8)
    
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            puntos = []
            for lm in face_landmarks.landmark:
                puntos.append((int(lm.x * ancho), int(lm.y * alto)))
            
            # Calibración dinámica por Iris (Constante biométrica ~1.17cm)
            iris_px = calcular_distancia(puntos[469], puntos[471])
            cm_per_pixel = 1.17 / (iris_px if iris_px > 0 else 1)
            
            # Puntos clave (Boca vertical y Ojo izquierdo vertical)
            p_boca_sup, p_boca_inf = puntos[13], puntos[14]
            p_ojo_sup, p_ojo_inf = puntos[159], puntos[145]
            
            # Calcular centímetros reales
            boca_v_cm = calcular_distancia(p_boca_sup, p_boca_inf) * cm_per_pixel
            ojo_v_cm = calcular_distancia(p_ojo_sup, p_ojo_inf) * cm_per_pixel
            
            # Dibujar líneas visuales de "tensión musical" en la cara
            cv2.line(frame, p_boca_sup, p_boca_inf, (0, 0, 255), 2)
            cv2.line(frame, p_ojo_sup, p_ojo_inf, (0, 255, 255), 2)
            cv2.circle(frame, p_boca_sup, 3, (0, 0, 255), -1)
            cv2.circle(frame, p_ojo_sup, 3, (0, 255, 255), -1)
            
            # --- MAPEO A PARÁMETROS MUSICALES ---
            # Interpolar (Mapear) rangos de cm a rangos de audio
            # Boca de 0cm a 3.5cm mapea a frecuencias de 200Hz (Grave) a 1000Hz (Agudo)
            frecuencia_target = np.interp(boca_v_cm, [0.1, 3.5], [200.0, 1000.0])
            # Ojo de 0.2cm (cerrado) a 1.2cm (muy abierto) mapea a volumen de 0.0 a 0.4 (suave para no saturar)
            volumen_target = np.interp(ojo_v_cm, [0.2, 1.1], [0.0, 0.4])
            
            # Suavizado de señal para evitar chasquidos bruscos en el audio
            frecuencia_actual = frecuencia_actual * 0.7 + frecuencia_target * 0.3
            volumen_actual = volumen_actual * 0.6 + volumen_target * 0.4
            
            fuente = cv2.FONT_HERSHEY_SIMPLEX

            # Barra de Frecuencia (Boca)
            cv2.putText(panel_instrumento, f"Tono (Boca): {int(frecuencia_actual)} Hz", (20, 100), fuente, 0.5, (0, 0, 255), 1)
            cv2.rectangle(panel_instrumento, (200, 85), (int(200 + (frecuencia_actual-200)/3), 100), (0, 0, 255), -1)
            
            # Barra de Volumen (Ojos)
            cv2.putText(panel_instrumento, f"Volumen (Ojos): {int(volumen_actual * 250)}%", (20, 160), fuente, 0.5, (0, 255, 255), 1)
            cv2.rectangle(panel_instrumento, (200, 145), (200 + int(volumen_actual * 500), 160), (0, 255, 255), -1)
            
    else:
        # Si no hay rostro, apagar el sonido gradualmente
        volumen_actual *= 0.5

    cv2.imshow('Camara - Interprete', frame)
    cv2.imshow('Consola del Sintetizador', panel_instrumento)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): break

# Apagar limpiamente el audio y ventanas
stream.stop()
stream.close()
cap.release()
cv2.destroyAllWindows()
