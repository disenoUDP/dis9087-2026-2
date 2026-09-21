import cv2
import mediapipe as mp
import numpy as np
import pygame

# 1. Inicializar el sistema de audio de Pygame
pygame.mixer.init(frequency=44100, size=-16, channels=2)

def generar_tono_synth(frecuencia, duracion=0.3):
    sample_rate = 44100
    n_samples = int(sample_rate * duracion)
    t = np.linspace(0, duracion, n_samples, endpoint=False)
    wave = np.sign(np.sin(2 * np.pi * frecuencia * t))
    audio_data = (wave * 12000).astype(np.int16)
    stereo_audio = np.vstack((audio_data, audio_data)).T.copy()
    return pygame.mixer.Sound(buffer=stereo_audio)

def generar_ruido_percusión(tipo, duracion=0.15):
    sample_rate = 44100
    n_samples = int(sample_rate * duracion)
    t = np.linspace(0, duracion, n_samples, endpoint=False)
    
    if tipo == "bombo":
        freqs = 150 * np.exp(-40 * t)
        wave = np.sin(2 * np.pi * freqs * t)
        audio_data = (wave * 25000).astype(np.int16)
    elif tipo == "tarola":
        ruido = np.random.uniform(-1, 1, n_samples)
        tono = np.sin(2 * np.pi * 180 * t) * np.exp(-20 * t)
        wave = (ruido * 0.7) + (tono * 0.3)
        audio_data = (wave * 18000).astype(np.int16)
    else:
        ruido = np.random.uniform(-1, 1, n_samples)
        decaimiento = np.exp(-80 * t)
        wave = ruido * decaimiento
        audio_data = (wave * 15000).astype(np.int16)
        
    stereo_audio = np.vstack((audio_data, audio_data)).T.copy()
    return pygame.mixer.Sound(buffer=stereo_audio)

# Pre-cargar sonidos
sonidos = {
    "RITMO": {1: generar_ruido_percusión("bombo"), 2: generar_ruido_percusión("tarola"), 3: generar_ruido_percusión("hihat"), 4: generar_ruido_percusión("hihat", duracion=0.3)},
    "MELODIA": {1: generar_tono_synth(261.63), 2: generar_tono_synth(329.63), 3: generar_tono_synth(392.00), 4: generar_tono_synth(493.88)},
    "SAMPLES": {1: generar_tono_synth(130.81, duracion=0.6), 2: generar_tono_synth(164.81, duracion=0.6), 3: generar_tono_synth(196.00, duracion=0.6), 4: generar_tono_synth(220.00, duracion=0.6)},
    "EFECTOS_VOZ": {1: generar_tono_synth(523.25), 2: generar_tono_synth(659.25), 3: generar_tono_synth(783.99), 4: generar_tono_synth(987.77)}
}

# 2. Inicializar MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

MODO_MANO_IZQUIERDA = "RITMO"
MODO_MANO_DERECHA   = "MELODIA"
estados_anteriores = {"LEFT": [False]*5, "RIGHT": [False]*5}

def procesar_musica_y_audio(mano, pulgar_arriba, resto_dedos):
    global MODO_MANO_IZQUIERDA, MODO_MANO_DERECHA, estados_anteriores
    
    if mano == "LEFT":
        MODO_MANO_IZQUIERDA = "SAMPLES" if pulgar_arriba else "RITMO"
        modo_actual = MODO_MANO_IZQUIERDA
    else:
        MODO_MANO_DERECHA = "EFECTOS_VOZ" if pulgar_arriba else "MELODIA"
        modo_actual = MODO_MANO_DERECHA

    for i, esta_levantado in enumerate(resto_dedos):
        num_dedo = i + 1
        if esta_levantado and not estados_anteriores[mano][num_dedo]:
            print(f"[{mano} - {modo_actual}] Disparando canal del dedo {num_dedo}")
            sonidos[modo_actual][num_dedo].play()
        estados_anteriores[mano][num_dedo] = esta_levantado

# 3. Captura de Cámara
cap = cv2.VideoCapture(0)
print("--- SINTETIZADOR DE MANOS OPERATIVO ---")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    
    frame = cv2.flip(frame, 1)
    h, w, c = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    
    manos_detectadas = []
    
    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            
            # CORRECCIÓN DE LA API: Extracción correcta en versiones nuevas de MediaPipe
            label = handedness.classification[0].label # "Left" o "Right"
            
            # Invertimos la etiqueta debido al espejo del flip para que coincida con tu cuerpo real
            mano_clave = "RIGHT" if label == "Left" else "LEFT"
            manos_detectadas.append(mano_clave)
            
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # Detectar estado del pulgar (Landmark 4 vs Landmark 2 en eje X)
            if mano_clave == "LEFT":
                pulgar = hand_landmarks.landmark[4].x < hand_landmarks.landmark[2].x
            else:
                pulgar = hand_landmarks.landmark[4].x > hand_landmarks.landmark[2].x
                
            # Otros 4 dedos (Punta por encima del nudillo medio en eje Y)
            puntas = [8, 12, 16, 20]
            resto_dedos = []
            for p in puntas:
                abierto = hand_landmarks.landmark[p].y < hand_landmarks.landmark[p-2].y
                resto_dedos.append(abierto)
                
            procesar_musica_y_audio(mano_clave, pulgar, resto_dedos)
            
            # Interfaz gráfica en pantalla
            modo_txt = MODO_MANO_IZQUIERDA if mano_clave == "LEFT" else MODO_MANO_DERECHA
            pos_y = 50 if mano_clave == "LEFT" else 100
            cv2.putText(frame, f"{mano_clave}: {modo_txt}", (20, pos_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
    # Resetear estados de manos que salieron de la cámara
    for m in ["LEFT", "RIGHT"]:
        if m not in manos_detectadas:
            estados_anteriores[m] = [False]*5

    cv2.imshow("Mini Estudio Electropop - Audio Activo", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
