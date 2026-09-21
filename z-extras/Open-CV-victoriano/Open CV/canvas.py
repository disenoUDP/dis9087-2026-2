"""
Módulo del Lienzo Virtual (Air Canvas).
Gestiona la superficie de dibujo en memoria, el trazado continuo anti-aliased,
el grosor por defecto en 13px, la rotación automática de colores (Amarillo -> Azul -> Rojo),
y la fusión por adición sobre el fotograma de la cámara (Realidad Aumentada).
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List, Dict


# Secuencia de colores principal para capturas consecutivas:
# 1. Amarillo -> 2. Azul -> 3. Rojo (BGR para OpenCV)
ROTATION_PALETTE: List[Tuple[str, Tuple[int, int, int]]] = [
    ("Amarillo", (0, 235, 255)),
    ("Azul", (255, 130, 0)),
    ("Rojo", (20, 20, 255)),
]


class AirCanvas:
    """Superficie de dibujo digital para pintura de luz."""

    def __init__(self, width: int, height: int, brush_thickness: int = 13):
        self.width = width
        self.height = height
        # Grosor fijo en 13 por defecto
        self.brush_thickness = brush_thickness
        self.canvas = np.zeros((height, width, 3), dtype=np.uint8)

        # Iniciar en el primer color de la secuencia: Amarillo (índice 0)
        self.rotation_idx = 0
        self.current_color_name = ROTATION_PALETTE[0][0]
        self.current_color = ROTATION_PALETTE[0][1]

        self.prev_point: Optional[Tuple[int, int]] = None
        self.has_strokes: bool = False
        self.total_points_drawn: int = 0

    def set_brush_thickness(self, thickness: int):
        """Ajusta el grosor del trazo."""
        self.brush_thickness = max(1, min(60, int(thickness)))

    def advance_to_next_rotation_color(self) -> str:
        """
        Avanza al siguiente color en la rotación:
        Amarillo -> Azul -> Rojo -> Amarillo ...
        """
        self.rotation_idx = (self.rotation_idx + 1) % len(ROTATION_PALETTE)
        self.current_color_name, self.current_color = ROTATION_PALETTE[self.rotation_idx]
        return self.current_color_name

    def set_rotation_color_index(self, index: int):
        """Fija un color específico de la lista de rotación."""
        self.rotation_idx = index % len(ROTATION_PALETTE)
        self.current_color_name, self.current_color = ROTATION_PALETTE[self.rotation_idx]

    def get_current_color_name(self) -> str:
        """Retorna el nombre del color activo."""
        return self.current_color_name

    def add_point(self, point: Tuple[int, int]):
        """
        Agrega un nuevo punto y dibuja una línea continua desde el punto anterior.
        """
        if self.prev_point is not None:
            # Trazar línea continua suavizada con anti-aliasing
            cv2.line(
                self.canvas,
                self.prev_point,
                point,
                self.current_color,
                self.brush_thickness,
                lineType=cv2.LINE_AA,
            )
            # Relleno de esquinas para evitar bordes dentados
            cv2.circle(
                self.canvas,
                point,
                max(1, self.brush_thickness // 2),
                self.current_color,
                -1,
                lineType=cv2.LINE_AA,
            )
            self.has_strokes = True
            self.total_points_drawn += 1

        self.prev_point = point

    def stop_stroke(self):
        """
        Llamado cuando el puntero desaparece o se apaga la linterna,
        evitando que se trace una línea hasta el siguiente encendido.
        """
        self.prev_point = None

    def clear(self):
        """Borra por completo los trazos del lienzo."""
        self.canvas.fill(0)
        self.prev_point = None
        self.has_strokes = False
        self.total_points_drawn = 0

    def blend(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Fusiona el video de la cámara con el lienzo digital.
        Al ser una suma matricial saturada (cv2.add), los trazos de luz
        resplandecen en el aire sin alterar las partes oscuras del fondo.
        """
        return cv2.add(frame_bgr, self.canvas)
