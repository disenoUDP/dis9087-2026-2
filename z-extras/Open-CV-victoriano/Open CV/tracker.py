"""
Módulo de Detección y Seguimiento del Puntero de Luz (Linterna).
Optimizado con detección de picos de intensidad lumínica y neutralización
espacial de reflejos del fondo.
"""

import cv2
import numpy as np
import time
from typing import Tuple, Optional


class LightTracker:
    """Rastreador de puntero virtual ultra-sensible y robusto."""

    def __init__(
        self,
        min_brightness: int = 215,
        min_area: int = 3,
        max_area: int = 50000,
        movement_threshold_px: float = 5.0,
    ):
        self.min_brightness = min_brightness
        self.min_area = min_area
        self.max_area = max_area
        self.movement_threshold_px = movement_threshold_px

        self.last_centroid: Optional[Tuple[int, int]] = None
        self.last_movement_time: float = time.perf_counter()
        self.is_detected: bool = False
        self.is_moving: bool = False

        # Máscara de exclusión de reflejos estáticos de fondo
        self.static_exclusion_mask: Optional[np.ndarray] = None

        # Kernel 3x3 para preservar fuentes de luz pequeñas o distantes
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    def set_min_brightness(self, value: int):
        """Actualiza el umbral mínimo de brillo asegurando un rango funcional (180-245)."""
        self.min_brightness = max(150, min(245, int(value)))

    def set_static_exclusion_mask(self, mask: Optional[np.ndarray]):
        """Establece la máscara de zonas fijas a ignorar."""
        self.static_exclusion_mask = mask

    def process_frame(
        self, frame_bgr: np.ndarray
    ) -> Tuple[bool, Optional[Tuple[int, int]], np.ndarray]:
        """
        Detecta el foco de la linterna usando el pico de brillo máximo
        sustrayendo los reflejos fijos del entorno.
        """
        now = time.perf_counter()

        # 1. Extraer canal de máxima intensidad (Grayscale vs V de HSV)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        v_chan = hsv[:, :, 2]
        intensity = cv2.max(gray, v_chan)

        # 2. Anular reflejos estáticos del fondo si existen
        if self.static_exclusion_mask is not None:
            not_static = cv2.bitwise_not(self.static_exclusion_mask)
            search_intensity = cv2.bitwise_and(intensity, not_static)
        else:
            search_intensity = intensity

        # 3. Localizar el punto más brillante de la escena
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(search_intensity)

        current_centroid: Optional[Tuple[int, int]] = None
        detected = False
        clean_mask = np.zeros_like(gray)

        # 4. Verificar si el brillo máximo supera el umbral de la linterna
        if max_val >= self.min_brightness:
            # Umbral dinámico enfocado en el núcleo brillante de la luz
            local_thresh = max(int(self.min_brightness), int(max_val - 25))
            _, raw_mask = cv2.threshold(search_intensity, local_thresh, 255, cv2.THRESH_BINARY)

            # Filtrado morfológico con kernel suave (3x3)
            clean_mask = cv2.morphologyEx(raw_mask, cv2.MORPH_OPEN, self.kernel)
            clean_mask = cv2.dilate(clean_mask, self.kernel, iterations=1)

            # Buscar contornos
            contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                valid_contours = [
                    c for c in contours if self.min_area <= cv2.contourArea(c) <= self.max_area
                ]

                if valid_contours:
                    # Seleccionar el contorno más grande o más cercano al punto de brillo máximo
                    largest_c = max(valid_contours, key=cv2.contourArea)
                    moments = cv2.moments(largest_c)

                    if moments["m00"] > 0:
                        cx = int(moments["m10"] / moments["m00"])
                        cy = int(moments["m01"] / moments["m00"])
                    else:
                        (cx_f, cy_f), _ = cv2.minEnclosingCircle(largest_c)
                        cx, cy = int(cx_f), int(cy_f)

                    current_centroid = (cx, cy)
                    detected = True
            elif max_val >= (self.min_brightness + 5):
                # Si el punto es intensamente brillante pero muy pequeño (<3px), usar max_loc directamente
                current_centroid = max_loc
                detected = True

        self.is_detected = detected

        # 5. Detección de movimiento
        if detected and current_centroid is not None:
            if self.last_centroid is not None:
                dx = current_centroid[0] - self.last_centroid[0]
                dy = current_centroid[1] - self.last_centroid[1]
                distance = (dx * dx + dy * dy) ** 0.5

                if distance >= self.movement_threshold_px:
                    self.is_moving = True
                    self.last_movement_time = now
                else:
                    self.is_moving = False
            else:
                self.is_moving = True
                self.last_movement_time = now

            self.last_centroid = current_centroid
        else:
            self.is_moving = False
            self.last_centroid = None

        return detected, current_centroid, clean_mask

    def get_time_since_movement(self) -> float:
        """Tiempo transcurrido en segundos desde el último movimiento detectado."""
        return time.perf_counter() - self.last_movement_time

    def reset_inactivity(self):
        """Reinicia el temporizador de inactividad."""
        self.last_movement_time = time.perf_counter()
