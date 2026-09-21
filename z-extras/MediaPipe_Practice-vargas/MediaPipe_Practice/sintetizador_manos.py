import cv2
import mediapipe as mp
import numpy as np
import sounddevice as sd
import math

# --- CONFIGURACIÓN DE AUDIO CON ECO (DELAY/REVERB) ---
SAMP_RATE = 44100
frecuencia_actual = 440.0
volumen_actual = 0.2  # Volumen base fijo para enfocarnos en los efectos

# Configuración del Delay
DELAY_MAX_SEGUNDOS = 1.0
BUFFER_DELAY_SIZE = int(SAMP_RATE * DELAY_MAX_SEGUNDOS)
buffer_delay = np.zeros(BUFFER_DELAY_SIZE, dtype=np.float32)
ptr_lectura = 0
ptr_escritura = 0

# Parámetros que controlará tu mano izquierda
efecto_mix = 0.0      # Qué tanto eco se escucha (0.0 = nada, 1.0 = máximo)
efecto_feedback = 0.0 # Cuántas veces se repite el eco (0.0 = una vez, 0.9 = infinito)

def audio_callback(outdata, frames, time, status):
    global frecuencia_actual, volumen_actual, efecto_mix, efecto_feedback, ptr_escritura, buffer_delay
    
    # 1. Generar la onda pura de la nota actual
    t = (np.arange(frames) + audio_callback.index) / SAMP_RATE
    onda_pura = volumen_actual * np.sin(2 * np.pi * frecuencia_actual * t)
    audio_callback.index += frames
    
    # 2. Procesador de Efectos (Delay/Reverb Line) en tiempo real
    onda_procesada = np.zeros(frames, dtype=np.float32)
    
    # Tiempo de retraso fijo (~0.4 segundos para un eco rítmico agradable)
    retraso_samples = int(SAMP_RATE * 0.4)
    
    for i in range(frames):
        # Calcular de dónde leer el eco en el pasado
        ptr_lectura = (ptr_escritura - retraso_samples + BUFFER_DELAY_SIZE) % BUFFER_DELAY_SIZE
        sello_eco = buffer_delay[ptr_lectura]
        
        # Mezclar el sonido limpio con el eco del pasado
        onda_procesada[i] = (1.0 - efecto_mix) * onda_pura[i] + (efecto_mix * sello_eco)
        
        # Guardar en el buffer para la siguiente repetición (sonido actual + feedback del eco)
        buffer_delay[ptr_escritura] = onda_pura[i] + (sello_eco * efecto_feedback)
        ptr_escritura = (ptr_escritura + 1) % BUFFER_DELAY_SIZE
        
    outdata[:] = onda_procesada.reshape(-1, 1)

audio_callback.index = 0

stream = sd.OutputStream(channels=1, callback=audio_callback, samplerate=SAMP_RATE)
stream.start()

# --- CONFIGURACIÓN DE MEDIAPIPE HANDS ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)

def calcular_distancia(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

cap = cv2.VideoCapture(0)
print("¡Sintetizador de Manos Iniciado! Presiona 'q' para salir.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
        
    frame = cv2.flip(frame, 1)
    alto, ancho, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    
    # Panel limpio para visualizar valores de efectos
    panel_efectos = np.zeros((160, 420, 3), dtype=np.uint8)
    
    # Valores de control por defecto si no hay manos en pantalla
    mano_der_detectada = False
    mano_izq_detectada = False
    
    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            # Obtener si es mano izquierda o derecha (MediaPipe lo detecta invertido por el espejo)
            etiqueta_mano = handedness.classification[0].label # "Left" o "Right"
            
            puntos = []
            for lm in hand_landmarks.landmark:
                puntos.append((int(lm.x * ancho), int(lm.y * alto)))
            
            # Índices de MediaPipe Hands: Pulgar punta = 4 | Índice punta = 8
            p_pulgar = puntos[4]
            p_indice = puntos[8]
            
            # Dibujar los puntos y una línea de conexión entre los dedos activos
            cv2.circle(frame, p_pulgar, 6, (0, 255, 0), -1)
            cv2.circle(frame, p_indice, 6, (255, 0, 0), -1)
            cv2.line(frame, p_pulgar, p_indice, (255, 255, 255), 2)
            
            # Calcular distancia en píxeles entre índice y pulgar
            dist_px = calcular_distancia(p_pulgar, p_indice)
            
            # --- MANO DERECHA: CONTROLA EL TONO (FRECUENCIA) ---
            if etiqueta_mano == "Right":
                mano_der_detectada = True
                # Mapear distancia de 20px a 180px a frecuencias de 200Hz a 800Hz
                frec_target = np.interp(dist_px, [20, 180], [200.0, 800.0])
                frecuencia_actual = frecuencia_actual * 0.7 + frec_target * 0.3
                
            # --- MANO IZQUIERDA: CONTROLA EL DELAY / REVERB ---
            elif etiqueta_mano == "Left":
                mano_izq_detectada = True
                # Mapear distancia a porcentaje de mezcla (Mix) y repetición (Feedback)
                mix_target = np.interp(dist_px, [20, 180], [0.0, 0.85])
                feed_target = np.interp(dist_px, [20, 180], [0.0, 0.80])
                
                efecto_mix = efecto_mix * 0.6 + mix_target * 0.4
                efecto_feedback = efecto_feedback * 0.6 + feed_target * 0.4

    # Si sacas la mano derecha de la pantalla, bajamos el volumen gradualmente
    if not mano_der_detectada:
        volumen_actual = volumen_actual * 0.8 + 0.0 * 0.2
    else:
        volumen_actual = volumen_actual * 0.8 + 0.2 * 0.2 # Recupera volumen base
        
    # --- DIBUJAR VALORES EN LA PANTALLA SECUNDARIA ---
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    
    # Línea 1: Frecuencia de la nota (Mano Derecha)
    cv2.putText(panel_efectos, f"Nota: {int(frecuencia_actual)} Hz", (20, 50), fuente, 0.5, (255, 0, 0), 1)
    cv2.rectangle(panel_efectos, (150, 38), (150 + int(np.interp(frecuencia_actual, [200, 800], [0, 240])), 50), (255, 0, 0), -1)
    
    # Línea 2: Nivel de Eco/Espacio (Mano Izquierda)
    cv2.putText(panel_efectos, f"Espacio: {int(efecto_mix * 100)}%", (20, 110), fuente, 0.5, (0, 255, 0), 1)
    cv2.rectangle(panel_efectos, (150, 98), (150 + int(efecto_mix * 240), 110), (0, 255, 0), -1)

    cv2.imshow('Camara - Control Aereo', frame)
    cv2.imshow('Valores de Sintesis', panel_efectos)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): break

stream.stop()
stream.close()
cap.release()
cv2.destroyAllWindows()
