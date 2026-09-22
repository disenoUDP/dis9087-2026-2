import cv2
import mediapipe as mp
import numpy as np

# Inicializar el detector de manos de MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=2,               # Detectar hasta 2 manos simultáneamente
    min_detection_confidence=0.7, 
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)
print("Programa listo. Usa los índices y pulgares de ambas manos para crear el marco pixelado.")
print("Presiona 'q' para salir.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    # Efecto espejo intuitivo
    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape
    output_frame = frame.copy()
    
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    puntos_control = []

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # PUNTOS ESPECÍFICOS DE MEDIAPIPE:
            #punto 4 = Punta del pulgar (Thumb tip)
            #punto 8 = Punta del índice (Index finger tip)
            pulgar = hand_landmarks.landmark[4]
            indice = hand_landmarks.landmark[8]
            
            # Convertir coordenadas decimales a píxeles de la pantalla
            px, py = int(pulgar.x * width), int(pulgar.y * height)
            ix, iy = int(indice.x * width), int(indice.y * height)
            
            # Guardar únicamente estos dedos en la lista de control
            puntos_control.append((px, py))
            puntos_control.append((ix, iy))
            
            # Dibujar un pequeño punto brillante sobre los dedos usados para que sepa cuáles son
            cv2.circle(output_frame, (px, py), 6, (0, 255, 255), -1) # Pulgar (Amarillo neón)
            cv2.circle(output_frame, (ix, iy), 6, (0, 255, 255), -1) # Índice (Amarillo neón)

    # Solo activamos el filtro pixelado cuando el código ve los 4 dedos (2 manos en pantalla)
    if len(puntos_control) == 4:
        arr_puntos = np.array(puntos_control)
        
        # Encontrar el área rectangular exacta uniendo solo los 4 dedos
        x_min = max(0, np.min(arr_puntos[:, 0]))
        y_min = max(0, np.min(arr_puntos[:, 1]))
        x_max = min(width, np.max(arr_puntos[:, 0]))
        y_max = min(height, np.max(arr_puntos[:, 1]))

        # Evitar cálculos si los dedos están demasiado pegados
        if (x_max - x_min) > 20 and (y_max - y_min) > 20:
            # 1. Recortar solo el espacio que queda atrapado entre tus 4 dedos
            zona_interes = frame[y_min:y_max, x_min:x_max]

            # 2. EFECTO PIXELADO RETRO
            # Dividimos por 15 para definir el "grosor" de los bloques. 
            # Si subes este número a 30 o 40, los píxeles se verán mucho más gigantes y abstractos.
            bloques_ancho = max(1, int((x_max - x_min) / 15))
            bloques_alto = max(1, int((y_max - y_min) / 15))
            
            # Reducir drásticamente la resolución de la zona
            temporal = cv2.resize(zona_interes, (bloques_ancho, bloques_alto), interpolation=cv2.INTER_LINEAR)
            # Re-escalar usando "INTER_NEAREST" para fijar los bloques cuadrados sin desenfocarlos
            zona_pixelada = cv2.resize(temporal, (x_max - x_min, y_max - y_min), interpolation=cv2.INTER_NEAREST)

            # 3. Pegar los píxeles gigantes en la imagen final
            output_frame[y_min:y_max, x_min:x_max] = zona_pixelada

            # 4. Dibujar una sutil línea cian que enmarca tu zona pixelada interactiva
            cv2.rectangle(output_frame, (x_min, y_min), (x_max, y_max), (255, 255, 0), 2)

    # Mostrar la transmisión final en la ventana
    cv2.imshow('Filtro Pixelado - Solo Pulgar e Indice', output_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()

