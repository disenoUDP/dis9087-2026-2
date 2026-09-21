"""
Módulo de Guardado Asíncrono de Capturas.
Permite exportar imágenes en resolución 1080p (formato .jpg) en un hilo secundario
para garantizar que la captura de video en vivo nunca sufra caídas de FPS o congelamientos.
"""

import os
import re
import cv2
import queue
import threading
from typing import Optional, Callable


class AsyncImageSaver:
    """Administrador de guardado secuencial y asíncrono en disco."""

    def __init__(
        self,
        output_dir: str,
        target_width: int = 1920,
        target_height: int = 1080,
        jpeg_quality: int = 92,
    ):
        self.output_dir = output_dir
        self.target_width = target_width
        self.target_height = target_height
        self.jpeg_quality = jpeg_quality

        os.makedirs(self.output_dir, exist_ok=True)
        self.lock = threading.Lock()
        self.current_index = self._scan_next_index()

        self.save_queue: queue.Queue = queue.Queue()
        self.is_running = True

        self.worker_thread = threading.Thread(
            target=self._worker, name="ImageSaverWorker", daemon=True
        )
        self.worker_thread.start()

    def _scan_next_index(self) -> int:
        """Busca en el directorio de capturas el número secuencial más alto existente."""
        pattern = re.compile(r"^captura_(\d+)\.(?:jpg|jpeg)$", re.IGNORECASE)
        max_id = 0
        if os.path.exists(self.output_dir):
            for fname in os.listdir(self.output_dir):
                match = pattern.match(fname)
                if match:
                    try:
                        val = int(match.group(1))
                        if val > max_id:
                            max_id = val
                    except ValueError:
                        pass
        return max_id + 1

    def save_async(
        self, image, callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Encola una imagen para guardarse en disco sin bloquear el hilo principal.
        Retorna la ruta del archivo programado.
        """
        with self.lock:
            filename = f"captura_{self.current_index:04d}.jpg"
            self.current_index += 1
            filepath = os.path.join(self.output_dir, filename)

        # Clonación de la matriz de imagen para evitar condiciones de carrera
        image_copy = image.copy()
        self.save_queue.put((filepath, image_copy, callback))
        return filepath

    def _worker(self):
        """Hilo en segundo plano que procesa la cola de escritura a disco."""
        while self.is_running or not self.save_queue.empty():
            try:
                item = self.save_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            filepath, img, callback = item
            try:
                h, w = img.shape[:2]
                # Redimensionado de alta calidad a 1080p
                if (w, h) != (self.target_width, self.target_height):
                    interp = (
                        cv2.INTER_AREA
                        if (w > self.target_width or h > self.target_height)
                        else cv2.INTER_CUBIC
                    )
                    resized = cv2.resize(
                        img,
                        (self.target_width, self.target_height),
                        interpolation=interp,
                    )
                else:
                    resized = img

                # Parámetros de compresión JPEG optimizados
                encode_params = [
                    int(cv2.IMWRITE_JPEG_QUALITY),
                    self.jpeg_quality,
                    int(cv2.IMWRITE_JPEG_OPTIMIZE),
                    1,
                ]

                cv2.imwrite(filepath, resized, encode_params)
                print(f"[INFO] Captura guardada con éxito: {filepath} (1080p)")

                if callback:
                    callback(filepath)
            except Exception as exc:
                print(f"[ERROR] Error al guardar {filepath}: {exc}")
            finally:
                self.save_queue.task_done()

    def get_queue_size(self) -> int:
        """Retorna la cantidad de imágenes pendientes de escritura."""
        return self.save_queue.qsize()

    def stop(self):
        """Finaliza de forma segura el hilo de guardado esperando a que termine la cola."""
        self.is_running = False
        self.save_queue.join()
