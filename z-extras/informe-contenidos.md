# Informe de contenidos

**DIS9087 · Dispositivos Periféricos y Plataformas para la Interacción Digital**
Semestre 2026-2 · Escuela de Diseño UDP · Docente: Felipe Roa · Ayudante: Santiago Gaete

El curso fue un panorama de las tecnologías disponibles hoy para diseñar interacción: visión computacional, video, sonido, sensores, web e IA. El objetivo no era dominar cada una, sino conocerlas lo suficiente para saber que existen, entender qué permiten y poder recurrir a ellas más adelante. Se recorrieron a través de los sentidos (vista, tiempo, oído y tacto), y cada encargo terminó como una plataforma publicada y documentada en GitHub. El examen reúne todo en un portafolio personal. En total hubo 13 sesiones, 7 tareas, 2 invitados y un examen.

## Síntesis

| Fase | Eje | Tecnologías aplicadas en encargos | Tecnologías revisadas en clase | Encargo |
| - | - | - | - | - |
| 1 | Percepción | — (análisis de sensores en objetos cotidianos) | sensores de temperatura, presión, luz y movimiento | T01 |
| 2 | Vista | Python, OpenCV, MediaPipe (manos, rostro, postura), Git y GitHub | NumPy, pandas, Matplotlib, SciPy, PyTorch, TensorFlow, scikit-learn, Transformers; LLM y herramientas de IA de contexto acotado (NotebookLM, Consensus, Claude Cowork, Antigravity) | T02, T03 |
| 2 | Web | VS Code, HTML, CSS, JavaScript, MediaPipe y OpenCV en el navegador, GitHub Pages | servidor local (`py -m http.server`) | T03 |
| 3 | Tiempo | Slit Scan (frames apilados en 3D, keyframes), editores de video (CapCut, Premiere, DaVinci Resolve) | — | T04 |
| 4 | Oído | Sketch Tools (audioreactividad: amplitud, bandas de frecuencia, detección de golpes), Web Audio (síntesis, envolventes, filtros, reverb), herramienta *Oír la luz*, bancos de sonido libres (Freesound) | MIDI, LFO, API, TypeScript, Supabase, Stripe, Ko-fi, Figma Make (charla de Sketch); CLO3D y automatización en moda (charla de Matías Pezoa) | T05, T06 |
| 5 | Tacto | MQTT y brokers (EMQX), sensores del teléfono (posición, multitouch, presión, giroscopio), herramienta *Tacto*, Node.js en modo local | sensado táctil capacitivo | T07 |
| Cierre | Portafolio | GitHub Pages, librerías de componentes (21st.dev, Aceternity UI, Motion Primitives, Shaders), React y Tailwind en web sin framework | Three.js y WebGL (mesh3d), galerías de referencia (Designeer, save.design, Sitereel) | Examen |

## Cronología

| Sesión | Fecha | Contenidos | Encargo |
| - | - | - | - |
| 01 | 13 ago | Fenómeno ≠ experiencia perceptual, antropocentrismo, semiótica, política de los artefactos (Merleau-Ponty, Winner) | **T01 · Dispositivos de realidad:** analizar un objeto cotidiano como sensor → dato → interpretación |
| 02 | 20 ago | Fundamentos de programación, Python, OpenCV, MediaPipe, introducción a GitHub | — |
| 03 | 27 ago | IA: sesgos, alucinaciones, LLM y método C.R.E.A. para escribir instrucciones | **T02 · Gatos:** modificar un detector de gestos (6 gestos, 6 imágenes) |
| 04 | 3 sep | MediaPipe y OpenCV por separado, en el navegador | **T03 · MediaPipe y OpenCV:** proyecto web con reflexión semiótica |
| 05 | 10 sep | VS Code, HTML, CSS y JavaScript | — |
| — | 17 sep | *Receso de Fiestas Patrias* | — |
| 06 | 24 sep | Slit scan, el video como volumen de frames, dimensiones | **T04 · Slit Scan:** video de 30 a 45 s sobre el paso del tiempo, con texto |
| 07 | 1 oct | *Paro.* Charla de Benjamín, creador de Sketch Tools (visuales audioreactivas) | — |
| 08 | 8 oct | Taller en Sketch | **T05 · Audioreactividad:** reel 9:16 con canción chilena y herramienta HTML propia; concurso en Instagram |
| 09 | 15 oct | *Paro.* Teoría del sonido: acusmática, frecuencia, amplitud, efecto McGurk, Cage | **T06 · Sonidos:** plataforma web que traduce imagen en sonido |
| 10 | 22 oct | Charla de Matías Pezoa (moda y tecnología, CLO3D) | — |
| 11 | 29 oct | Presentación de la T06. MQTT y sensado táctil | **T07 · Tacto:** el teléfono como control táctil por MQTT de una experiencia audiovisual |
| 12 | 5 nov | Trabajo en clase sobre la T07 | — |
| 13 | 12 nov | Entrega de la T07 | **Examen:** portafolio personal |

## Examen

Portafolio web publicado en GitHub Pages, con landing de gráfica propia (integra componentes externos acreditados), página *About me* y una subpágina por proyecto: T03, T06, T07 y al menos 2 proyectos externos al curso. Se exige además el GitHub personal ordenado y un README con los conceptos técnicos explicados con código propio, más una reflexión del semestre escrita sin IA.

Ponderación: gráfica 30% · narrativa 30% · web funcional 20% · repositorios 10% · README 10%.

## Competencias transversales

Pasar de un concepto a una relación entre interacción y medio, publicar en la web, documentar en README, declarar fuentes, licencias y uso de IA, y reflexionar críticamente sobre lo que cada sistema percibe y lo que deja fuera.

Material completo en [disenoUDP/dis9087-2026-2](https://github.com/disenoUDP/dis9087-2026-2).
