# Air Canvas / Light Painting con OpenCV y Realidad Aumentada

Aplicación interactiva desarrollada en Python con OpenCV que permite utilizar una linterna o fuente de luz pequeña como puntero virtual para dibujar en el aire sobre el video en tiempo real de tu cámara web (Realidad Aumentada).

El sistema cuenta con **recalibración adaptativa en el tiempo de espera**, **aislamiento dinámico de reflejos y muebles brillantes**, **calibración inicial de 5s**, **grosor fijo en 13px**, **slider bajo demanda con tecla [G]**, **rotación secuencial de colores (Amarillo -> Azul -> Rojo)**, **superposición exacta en 1080p (.jpg)** y **autoguardado por inactividad de 3s**.

---

## Características Principales

- **Recalibración Adaptativa en Tiempo de Espera:** Durante la pausa post-captura (indicada con círculo rojo), el sistema escanea activamente la escena para detectar si algún mueble se movió, se encendió una luz o apareció un nuevo reflejo brillante. Si detecta cambios, **extiende automáticamente el tiempo de espera hasta un máximo de 3 segundos adicionales** para aislar el nuevo reflejo e incorporarlo a la máscara de exclusión antes de pasar a modo `STANDBY`.
- **Neutralización de Reflejos del Fondo:** Mapeo inicial (5s) y continuo de zonas brillantes fijas para garantizar que ningún mueble o reflejo sea confundido con el puntero virtual.
- **Grosor del Trazo en 13px por Defecto:** Trazo visible, uniforme y suave desde el primer momento.
- **Control de Grosor a Demanda (`[G]`):** Presiona **`G`** para mostrar el slider de grosor en la parte superior; presiona **`G`** nuevamente para ocultarlo y mantener la pantalla libre de distracciones.
- **Rotación Automática de Colores por Captura:**
  - 1ª imagen: **Amarillo Eléctrico**
  - 2ª imagen: **Azul Neón**
  - 3ª imagen: **Rojo Brillante**
  - Ciclo continuo (Amarillo -> Azul -> Rojo), garantizando variedad cromática entre capturas.
- **Superposición Cámara + Puntero (AR):** Guardado en resolución $1920 \times 1080$ (.jpg) con el fotograma de video y los trazos de luz combinados limpiamente en segundo plano sin caídas de FPS.
- **Autoguardado por Inactividad (3s):** Se dispara automáticamente tras 3 segundos continuos sin movimiento del puntero.
- **Indicadores en la Esquina Superior Derecha:**
  - 🟢 **Círculo Verde (`REC`):** Linterna detectada activamente y dibujando.
  - 🔴 **Círculo Rojo (`ESPERA` / `RECALIBRANDO`):** Período de espera/recalibración adaptativa.
  - ⚪ **Círculo Gris (`STANDBY`):** En reposo esperando el encendido de la linterna.

---

## Cómo Ejecutar la Aplicación mediante PowerShell

Abre PowerShell y ejecuta:

```powershell
cd "C:\Universidad_Daniel\E02\Open CV"
python main.py
```

### Controles de Teclado
| Tecla | Acción |
| :---: | :--- |
| **`G`** | **Slider de Grosor:** Muestra u oculta el control deslizante para ajustar el grosor del trazo. |
| **`S`** | **Guardado Manual:** Fuerza una captura instantánea en 1080p, activa la espera/recalibración y avanza al siguiente color. |
| **`C`** | **Limpiar Lienzo:** Borra todos los trazos actuales de la pantalla. |
| **`M`** | **Modo Máscara:** Alterna la vista de calibración (muestra el puntero en blanco y los reflejos ignorados en rojo). |
| **`1`, `2`, `3`** | **Seleccionar Color:** 1 = Amarillo, 2 = Azul, 3 = Rojo. |
| **`Q` / `ESC`** | **Salir:** Cierra la aplicación de forma segura. |
