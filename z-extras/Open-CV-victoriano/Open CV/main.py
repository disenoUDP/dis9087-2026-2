"""
=============================================================================
Aplicación: Air Canvas / Light Painting con Realidad Aumentada y OpenCV
Autor: Universidad Daniel - E02
=============================================================================
Características:
1. Detección de puntero de alta sensibilidad por pico de brillo.
2. Calibración ambiental inicial de 5s para aislar reflejos fijos del entorno.
3. RECALIBRACIÓN ADAPTATIVA durante el tiempo de espera post-captura:
   - Revisa si han aparecido nuevos reflejos o elementos brillantes en la escena.
   - Si detecta cambios, extiende la espera hasta un máximo de 3s adicionales
     para integrarlos a la máscara de exclusión y evitar falsos positivos al entrar a STANDBY.
4. Grosor fijo en 13px por defecto, con sliders superiores ocultos.
5. Tecla [G]: Muestra / oculta el slider de grosor bajo demanda.
6. Rotación automática de color en cada captura: Amarillo -> Azul -> Rojo -> ...
7. Superposición exacta de cámara y dibujo en 1080p (.jpg) en segundo plano.
8. Autoguardado por inactividad de 3s.
9. Indicador visual: Círculo verde (REC) mientras se dibuja, círculo rojo durante espera/recalibración.
10. Flash blanco de obturador al realizar la captura.
=============================================================================
"""

import cv2
import numpy as np
import time
import os
import sys

from tracker import LightTracker
from canvas import AirCanvas, ROTATION_PALETTE
from saver import AsyncImageSaver


def dummy_trackbar(val):
    """Callback vacío requerido por OpenCV para trackbars."""
    pass


def main():
    # 1. Rutas de guardado y configuración
    base_dir = os.path.dirname(os.path.abspath(__file__))
    capturas_dir = os.path.join(base_dir, "capturas")

    # Guardador asíncrono en 1080p
    image_saver = AsyncImageSaver(
        output_dir=capturas_dir,
        target_width=1920,
        target_height=1080,
        jpeg_quality=94,
    )

    # 2. Inicialización de la cámara web
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] No se pudo acceder a ninguna cámara web. Conecta una cámara y reintenta.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    ret, sample_frame = cap.read()
    if not ret or sample_frame is None:
        print("[ERROR] No se pudo leer el primer fotograma de la cámara.")
        cap.release()
        sys.exit(1)

    frame_h, frame_w = sample_frame.shape[:2]
    print(f"[INFO] Cámara iniciada con resolución base: {frame_w}x{frame_h}")

    # 3. Inicialización de módulos (Grosor 13px y umbral base sensible 215)
    current_brush_thickness = 13
    tracker = LightTracker(min_brightness=215, movement_threshold_px=5.0)
    canvas = AirCanvas(width=frame_w, height=frame_h, brush_thickness=current_brush_thickness)

    # 4. Interfaz Gráfica de OpenCV (Limpia sin sliders iniciales)
    window_name = "Air Canvas - Light Painting (OpenCV)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, min(1280, frame_w), min(720, frame_h))

    show_thickness_slider = False

    # 5. Variables de estado
    show_mask_view = False
    flash_intensity = 0.0
    last_saved_name = ""
    last_save_notification_time = 0.0
    capture_already_triggered = False
    inactivity_limit_seconds = 3.0

    # Variables de tiempo de espera y recalibración adaptativa post-captura
    base_cooldown_seconds = 2.0
    max_additional_recalib = 3.0  # Alarga la espera no más de 3 segundos si es necesario
    current_cooldown_limit = base_cooldown_seconds
    cooldown_start_time = 0.0
    is_in_cooldown = False
    recalib_needed = False
    cooldown_frame_count = 0
    cooldown_glare_accumulator = np.zeros((frame_h, frame_w), dtype=np.int32)

    # Variables de calibración inicial de 5 segundos
    calibration_duration = 5.0
    calibration_start_time = time.perf_counter()
    is_calibrating = True
    max_ambient_brightness = 0.0
    calibration_frame_count = 0
    static_glare_accumulator = np.zeros((frame_h, frame_w), dtype=np.int32)
    dilated_static_mask = np.zeros((frame_h, frame_w), dtype=np.uint8)
    num_static_zones = 0

    print("==========================================================")
    print(" Air Canvas iniciado con calibración adaptativa.")
    print(" Grosor del trazo: 13 px (fijo por defecto).")
    print(" Sliders superiores ocultos. Presiona [G] para ajustar grosor.")
    print("==========================================================")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[AVISO] Fotograma no disponible.")
                break

            now = time.perf_counter()

            # Modo espejo para interacción natural
            frame = cv2.flip(frame, 1)

            # Si el slider de grosor está activo, sincronizar valor
            if show_thickness_slider:
                val = cv2.getTrackbarPos("Grosor Pincel", window_name)
                if val >= 1:
                    current_brush_thickness = val
                    canvas.set_brush_thickness(current_brush_thickness)

            # ==========================================================
            # FASE 1: CALIBRACIÓN INICIAL (5 Segundos)
            # ==========================================================
            if is_calibrating:
                elapsed_calib = now - calibration_start_time
                remaining_calib = max(0.0, calibration_duration - elapsed_calib)
                calib_progress = min(1.0, elapsed_calib / calibration_duration)
                calibration_frame_count += 1

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                intensity = cv2.max(gray, hsv[:, :, 2])

                frame_bright = float(np.percentile(intensity, 99.5))
                if frame_bright > max_ambient_brightness:
                    max_ambient_brightness = frame_bright

                # Mapear zonas con brillo persistente
                persistent_bright = intensity >= 225
                static_glare_accumulator[persistent_bright] += 1

                # Renderizar tarjeta informativa
                display_frame = frame.copy()
                overlay = display_frame.copy()

                card_w, card_h = 640, 240
                card_x = (frame_w - card_w) // 2
                card_y = (frame_h - card_h) // 2

                cv2.rectangle(overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), (20, 20, 25), -1)
                display_frame = cv2.addWeighted(overlay, 0.78, display_frame, 0.22, 0)
                cv2.rectangle(display_frame, (card_x, card_y), (card_x + card_w, card_y + card_h), (0, 220, 255), 2)

                cv2.putText(
                    display_frame,
                    "CALIBRANDO Y AISLANDO REFLEJOS DEL FONDO (5s)",
                    (card_x + 25, card_y + 40),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.65,
                    (0, 235, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    display_frame,
                    "Manten apagada tu linterna durante este proceso.",
                    (card_x + 25, card_y + 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (220, 220, 220),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    display_frame,
                    "Aislando muebles reflectantes y luces fijas del fondo...",
                    (card_x + 25, card_y + 105),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (180, 255, 180),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    display_frame,
                    f"Tiempo restante: {remaining_calib:.1f}s | Brillo ambiente medido: {int(max_ambient_brightness)}/255",
                    (card_x + 25, card_y + 138),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (255, 255, 200),
                    1,
                    cv2.LINE_AA,
                )

                pb_x, pb_y, pb_w, pb_h = card_x + 25, card_y + 165, card_w - 50, 20
                cv2.rectangle(display_frame, (pb_x, pb_y), (pb_x + pb_w, pb_y + pb_h), (45, 45, 45), -1)
                fill_w = int(pb_w * calib_progress)
                cv2.rectangle(display_frame, (pb_x, pb_y), (pb_x + fill_w, pb_y + pb_h), (0, 235, 255), -1)
                cv2.rectangle(display_frame, (pb_x, pb_y), (pb_x + pb_w, pb_y + pb_h), (255, 255, 255), 1)

                cv2.imshow(window_name, display_frame)

                if elapsed_calib >= calibration_duration:
                    is_calibrating = False

                    min_hits = max(5, int(calibration_frame_count * 0.60))
                    raw_static_mask = np.uint8((static_glare_accumulator >= min_hits) * 255)

                    dil_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
                    dilated = cv2.dilate(raw_static_mask, dil_kernel, iterations=1)

                    contours_glare, _ = cv2.findContours(
                        dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                    )
                    filtered_mask = np.zeros_like(dilated)
                    num_static_zones = 0
                    max_glare_area = (frame_w * frame_h) * 0.08

                    for cg in contours_glare:
                        if cv2.contourArea(cg) <= max_glare_area:
                            cv2.drawContours(filtered_mask, [cg], -1, 255, -1)
                            num_static_zones += 1

                    dilated_static_mask = filtered_mask
                    tracker.set_static_exclusion_mask(dilated_static_mask)

                    calibrated_threshold = 215
                    tracker.set_min_brightness(calibrated_threshold)
                    tracker.reset_inactivity()

                    print(f"[CALIBRACIÓN] Finalizada. Zonas reflectivas neutralizadas: {num_static_zones}")
                    print(f"[CALIBRACIÓN] Umbral de puntero fijado en {calibrated_threshold}.")
                    print(f"[COLOR] Color inicial: {canvas.get_current_color_name()}")

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    break
                continue

            # ==========================================================
            # FASE 2: DETECCIÓN, RECALIBRACIÓN EN ESPERA Y DIBUJO
            # ==========================================================
            time_in_cooldown = now - cooldown_start_time
            is_in_cooldown = time_in_cooldown < current_cooldown_limit

            detected = False
            centroid = None
            mask = None

            if is_in_cooldown:
                # --- RECALIBRACIÓN DURANTE EL TIEMPO DE ESPERA ---
                canvas.stop_stroke()
                tracker.reset_inactivity()
                mask = np.zeros((frame_h, frame_w), dtype=np.uint8)
                cooldown_frame_count += 1

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                intensity = cv2.max(gray, hsv[:, :, 2])

                # Buscar puntos brillantes que NO estén ya en la máscara de exclusión
                not_in_mask = cv2.bitwise_not(dilated_static_mask)
                unmasked_bright = cv2.bitwise_and(np.uint8(intensity >= 220), not_in_mask)
                bright_pixels_count = np.count_nonzero(unmasked_bright)

                # Si aparecen nuevos elementos brillantes estáticos (muebles movidos, reflejos nuevos)
                if bright_pixels_count > 10:
                    cooldown_glare_accumulator[unmasked_bright > 0] += 1

                    # Si aún no hemos extendido la espera, ampliar no más de 3 segundos
                    if not recalib_needed:
                        recalib_needed = True
                        extra_wait = min(max_additional_recalib, 1.8)
                        current_cooldown_limit = base_cooldown_seconds + extra_wait
                        print(f"[RECALIBRACIÓN] Cambios detectados en el fondo. Extendiendo espera en {extra_wait:.1f}s para recalibrar...")

                # Si la espera está concluyendo y se detectaron cambios, incorporar los nuevos reflejos
                if time_in_cooldown >= (current_cooldown_limit - 0.15) and recalib_needed:
                    min_hits_cd = max(3, int(cooldown_frame_count * 0.40))
                    new_glare_raw = np.uint8((cooldown_glare_accumulator >= min_hits_cd) * 255)

                    if np.count_nonzero(new_glare_raw) > 5:
                        dil_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
                        new_dilated = cv2.dilate(new_glare_raw, dil_kernel, iterations=1)

                        # Fusionar con la máscara previa
                        dilated_static_mask = cv2.bitwise_or(dilated_static_mask, new_dilated)
                        tracker.set_static_exclusion_mask(dilated_static_mask)

                        cnts, _ = cv2.findContours(dilated_static_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        num_static_zones = len(cnts)
                        print(f"[RECALIBRACIÓN COMPLETADA] Máscara actualizada. Total zonas neutralizadas: {num_static_zones}")
            else:
                # Detección normal cuando no estamos en tiempo de espera
                detected, centroid, mask = tracker.process_frame(frame)
                if detected and centroid is not None:
                    canvas.add_point(centroid)
                    capture_already_triggered = False
                else:
                    canvas.stop_stroke()

            blended = canvas.blend(frame)

            # Disparador de inactividad de 3 segundos
            time_since_move = tracker.get_time_since_movement()

            if (
                not is_in_cooldown
                and canvas.has_strokes
                and not capture_already_triggered
            ):
                if time_since_move >= inactivity_limit_seconds:
                    saved_path = image_saver.save_async(blended)
                    last_saved_name = os.path.basename(saved_path)
                    last_save_notification_time = now

                    flash_intensity = 1.0
                    capture_already_triggered = True

                    # Iniciar tiempo de espera y preparar acumulador de recalibración
                    cooldown_start_time = now
                    current_cooldown_limit = base_cooldown_seconds
                    recalib_needed = False
                    cooldown_frame_count = 0
                    cooldown_glare_accumulator.fill(0)

                    canvas.clear()
                    prev_col = canvas.get_current_color_name()
                    next_col = canvas.advance_to_next_rotation_color()
                    print(f"[ROTACIÓN] Foto guardada en {prev_col}. Próximo color: {next_col}")

                    tracker.reset_inactivity()

            # Renderizado de vista
            if show_mask_view and mask is not None:
                mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                if dilated_static_mask is not None:
                    mask_bgr[dilated_static_mask > 0] = [30, 30, 180]
                display_frame = mask_bgr
                cv2.putText(
                    display_frame,
                    f"VISTA MASCARA: Blanco = Puntero | Rojo = Reflejos ignorados ({num_static_zones})",
                    (20, frame_h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
            else:
                display_frame = blended.copy()

            # --- Indicador de Estado en la Esquina Superior Derecha ---
            circle_center = (frame_w - 40, 40)

            if is_in_cooldown:
                # TIEMPO DE ESPERA / RECALIBRACIÓN: CÍRCULO ROJO
                remaining_cd = max(0.0, current_cooldown_limit - (now - cooldown_start_time))
                cv2.circle(display_frame, circle_center, 14, (0, 0, 255), -1, cv2.LINE_AA)
                cv2.circle(display_frame, circle_center, 16, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(display_frame, (frame_w - 44, 36), 4, (255, 255, 255), -1, cv2.LINE_AA)

                label_cd = f"RECALIBRANDO {remaining_cd:.1f}s" if recalib_needed else f"ESPERA {remaining_cd:.1f}s"
                offset_x = 240 if recalib_needed else 180
                cv2.putText(
                    display_frame,
                    label_cd,
                    (frame_w - offset_x, 46),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.55,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
            elif detected:
                # DETECCIÓN ACTIVA / DIBUJANDO: CÍRCULO VERDE (REC)
                cv2.circle(display_frame, circle_center, 14, (0, 255, 0), -1, cv2.LINE_AA)
                cv2.circle(display_frame, circle_center, 16, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(display_frame, (frame_w - 44, 36), 4, (255, 255, 255), -1, cv2.LINE_AA)
                cv2.putText(
                    display_frame,
                    "REC",
                    (frame_w - 95, 46),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
            else:
                # EN ESPERA: CÍRCULO GRIS (STANDBY)
                cv2.circle(display_frame, circle_center, 12, (90, 90, 90), 2, cv2.LINE_AA)
                cv2.putText(
                    display_frame,
                    "STANDBY",
                    (frame_w - 135, 46),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.5,
                    (160, 160, 160),
                    1,
                    cv2.LINE_AA,
                )

            # --- Barra de Cuenta Regresiva de Inactividad (3s) ---
            if (
                not is_in_cooldown
                and canvas.has_strokes
                and not capture_already_triggered
            ):
                remaining_time = max(0.0, inactivity_limit_seconds - time_since_move)
                progress = min(1.0, time_since_move / inactivity_limit_seconds)

                bar_x, bar_y, bar_w, bar_h = 20, 20, 260, 16
                cv2.rectangle(display_frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1)
                fill_w = int(bar_w * progress)
                fill_color = (0, int(200 + 55 * progress), int(255 * (1 - progress)))
                cv2.rectangle(display_frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), fill_color, -1)
                cv2.rectangle(display_frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), 1)

                cv2.putText(
                    display_frame,
                    f"Auto-captura inactividad: {remaining_time:.1f}s",
                    (bar_x, bar_y + 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

            # --- Línea Inferior ---
            color_box_x = 20
            color_box_y = frame_h - 40
            cv2.rectangle(
                display_frame,
                (color_box_x, color_box_y),
                (color_box_x + 24, color_box_y + 24),
                canvas.current_color,
                -1,
            )
            cv2.rectangle(
                display_frame,
                (color_box_x, color_box_y),
                (color_box_x + 24, color_box_y + 24),
                (255, 255, 255),
                1,
            )

            next_rot_idx = (canvas.rotation_idx + 1) % len(ROTATION_PALETTE)
            next_rot_name = ROTATION_PALETTE[next_rot_idx][0]

            slider_status_txt = "[G] Ocultar slider grosor" if show_thickness_slider else "[G] Modificar grosor de trazo"
            bottom_info_text = (
                f"Color: {canvas.get_current_color_name()} (Sig: {next_rot_name}) | "
                f"Grosor: {current_brush_thickness}px | {slider_status_txt}"
            )

            cv2.putText(
                display_frame,
                bottom_info_text,
                (color_box_x + 35, color_box_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (220, 220, 220),
                1,
                cv2.LINE_AA,
            )

            # --- Notificación Flotante de Imagen Guardada ---
            if (now - last_save_notification_time) < 2.5 and last_saved_name:
                notify_text = f"Guardado: {last_saved_name} (1080p)"
                text_size = cv2.getTextSize(notify_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                text_x = (frame_w - text_size[0]) // 2
                text_y = frame_h - 70

                cv2.rectangle(
                    display_frame,
                    (text_x - 15, text_y - 25),
                    (text_x + text_size[0] + 15, text_y + 10),
                    (20, 20, 20),
                    -1,
                )
                cv2.rectangle(
                    display_frame,
                    (text_x - 15, text_y - 25),
                    (text_x + text_size[0] + 15, text_y + 10),
                    (0, 255, 100),
                    2,
                )
                cv2.putText(
                    display_frame,
                    notify_text,
                    (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 100),
                    2,
                    cv2.LINE_AA,
                )

            # --- Destello Visual de Flash Blanco ---
            if flash_intensity > 0.0:
                white_overlay = np.full_like(display_frame, 255)
                display_frame = cv2.addWeighted(
                    display_frame,
                    1.0 - flash_intensity,
                    white_overlay,
                    flash_intensity,
                    0,
                )
                flash_intensity = max(0.0, flash_intensity - 0.2)

            # Mostrar fotograma
            cv2.imshow(window_name, display_frame)

            # 10. Gestión de teclas
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), ord("Q"), 27):
                break
            elif key in (ord("g"), ord("G")):
                show_thickness_slider = not show_thickness_slider
                if show_thickness_slider:
                    cv2.createTrackbar("Grosor Pincel", window_name, current_brush_thickness, 40, dummy_trackbar)
                    cv2.setTrackbarMin("Grosor Pincel", window_name, 1)
                    print(f"[INFO] Slider de grosor activado: {current_brush_thickness}px")
                else:
                    cv2.destroyWindow(window_name)
                    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(window_name, min(1280, frame_w), min(720, frame_h))
                    print(f"[INFO] Slider de grosor ocultado: {current_brush_thickness}px")
            elif key in (ord("c"), ord("C")):
                canvas.clear()
                capture_already_triggered = False
                print("[INFO] Lienzo limpiado.")
            elif key in (ord("s"), ord("S")):
                if not is_in_cooldown:
                    saved_path = image_saver.save_async(blended)
                    last_saved_name = os.path.basename(saved_path)
                    last_save_notification_time = now
                    flash_intensity = 1.0
                    cooldown_start_time = now
                    current_cooldown_limit = base_cooldown_seconds
                    recalib_needed = False
                    cooldown_frame_count = 0
                    cooldown_glare_accumulator.fill(0)
                    capture_already_triggered = True

                    canvas.clear()
                    prev_col = canvas.get_current_color_name()
                    next_col = canvas.advance_to_next_rotation_color()
                    print(f"[ROTACIÓN MANUAL] Foto guardada en {prev_col}. Próximo color: {next_col}")

                    tracker.reset_inactivity()
            elif key in (ord("m"), ord("M")):
                show_mask_view = not show_mask_view
                print(f"[INFO] Vista de máscara: {'Activada' if show_mask_view else 'Desactivada'}")
            elif key in (ord("1"), ord("2"), ord("3")):
                canvas.set_rotation_color_index(key - ord("1"))
                print(f"[INFO] Color fijado manualmente: {canvas.get_current_color_name()}")

    except KeyboardInterrupt:
        print("[INFO] Detenido por el usuario.")
    finally:
        print("[INFO] Cerrando recursos...")
        cap.release()
        cv2.destroyAllWindows()
        image_saver.stop()
        print("[INFO] Aplicación finalizada correctamente.")


if __name__ == "__main__":
    main()
