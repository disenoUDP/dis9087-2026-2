# tarea-06

Desarrolla tu propia plataforma web que permita explorar la relación entre el sonido y la imagen en movimiento. Para esto, elige un concepto y genera u obtén un banco de sonidos que funcione en conjunto con un disparador visual. Puedes trabajar de forma individual o en duplas.

El objetivo es entender el sonido no solo como algo que acompaña una imagen, sino como una traducción que tú diseñas: qué fenómeno de la imagen escuchamos, con qué sonido lo representamos y qué relación construimos entre ambos. Te interesa menos reproducir lo que se ve y más proponer una forma nueva de escucharlo.

## La herramienta base

Trabajarás a partir de [Oír la luz](https://github.com/fefeliperoar/oir-la-luz), que corre en el navegador. Tus videos no se suben a ningún servidor: todo se procesa en tu equipo.

La herramienta divide la imagen en zonas y hace sonar cada zona cuando detecta un cambio entre fotogramas. Sobre esa base puedes trabajar con:

- Fuente: cámara web, archivo de video o una escena de ejemplo.
- Teclas: cantidad de zonas (columnas y filas), escala y nota base.
- Detección: umbral por píxel, sensibilidad por zona y tiempo entre repeticiones.
- Sonido: forma de onda, attack, release, filtro pasa-bajos, reverb y volumen.
- Mapping: qué dato de la imagen controla qué cualidad del sonido (intensidad → volumen, posición → pan).
- Visualización: forma de onda, armónicos, envolvente y partitura, en tiempo real.
- Grabar y MIDI: descargar lo que suena y conectar un controlador a los parámetros.

El README del repositorio explica cada función. La sección Usar otros sonidos indica cómo reemplazar las notas sintetizadas por grabaciones propias.

## La plataforma

Tu plataforma es una herramienta especializada en la temática que elijas. Puedes tomar como base Oír la luz o construir la tuya desde cero..

- Concepto: elige una relación entre imagen y sonido y defiéndela. En el README hay ejemplos: videos de la ciudad que generan sonidos de bosque, videos de migración que generan cantos de pájaros, olas que suenan como respiración, una multitud que suena como lluvia. Puedes partir de uno o proponer el tuyo.
- Banco de sonidos: reúne entre 5 y 15 sonidos, grabados por ti, generados o descargados de bancos de uso libre (por ejemplo freesound.org). Indica el origen y la licencia de cada uno.
- Disparador visual: define qué fenómeno de la imagen hace sonar la plataforma: movimiento, posición, color, cantidad de cambio u otro. Usa uno o más videos, grabados por ti o de uso libre, o la cámara en vivo.
- Parámetros: elige cuáles cualidades del sonido se pueden modificar (altura, volumen, attack, release, filtro, reverb, pan, velocidad de reproducción u otras) y por qué. Cada parámetro tiene que tener sentido dentro de tu concepto, no estar ahí solo porque existe.
- Gráfica: en esta oportunidad, la gráfica aplicada sobre la plataforma es parte de la evaluación. Nombre, tipografía, color, composición de la interfaz y forma de visualizar el sonido deben responder al concepto, como en una pieza de diseño completa.
- Publicación: la plataforma tiene que quedar publicada en GitHub Pages y funcionar desde el enlace.

Piensa la plataforma como una herramienta que otra persona podría usar para explorar tu tema, no como una demo técnica.

## El README

El repositorio debe incluir un README, organizado en cuatro partes:

1. Concepto y relación imagen–sonido. ¿Qué relación propones y por qué? ¿Es de semejanza, de contraste o de traducción? ¿Qué quieres que la persona escuche que antes no escuchaba?
2. Banco de sonidos y disparador. Qué sonidos usaste, de dónde vienen y cómo los elegiste o grabaste. Qué fenómeno de la imagen los dispara y con qué regla (el mapping). Incluye una tabla con los sonidos, su autor y su licencia.
3. Parámetros y gráfica. Qué parámetros del sonido se pueden modificar y por qué esos y no otros. Qué decisiones gráficas tomaste (tipografía, color, visualización) y cómo se relacionan con el concepto. Incluye dos o tres capturas.
4. Reflexión. ¿Qué descubriste al traducir imagen en sonido? ¿Qué queda fuera de la escucha de tu sistema? Propón al menos dos mejoras concretas para tu plataforma.

## Proceso sugerido

1. Elige el concepto. Parte por la relación, no por la técnica. Escribe en una frase qué imagen suena a qué y por qué.
2. Reúne el banco de sonidos. Graba con el celular o descarga sonidos cortos (de 0,3 a 5 segundos), sin silencio al inicio. Anota autor y licencia de cada uno.
3. Elige o graba tus videos. Funcionan mejor los clips con cámara fija y movimiento claro. Si usas la cámara en vivo, prueba con distintas luces y distancias.
4. Diseña la regla en papel. Sobre un fotograma impreso, dibuja las zonas, qué dato produce cada una y qué sonido genera.
5. Desarrolla. Modifica Oír la luz o crea tu plataforma con vibecoding. Prueba seguido en localhost con py -m http.server.
6. Diseña la gráfica. Define nombre, tipografía, paleta y la forma de visualizar el sonido. Revisa que la interfaz se entienda sin explicación.
7. Publica y documenta. Sube todo a GitHub, activa GitHub Pages y escribe el README mientras el proceso está fresco.

La cámara y el MIDI solo funcionan desde localhost o desde GitHub Pages (https). Haz commits seguidos: si algo se rompe, puedes volver a la versión anterior.

## Criterios de evaluación

- Claridad y solidez del concepto.
- Coherencia entre banco de sonidos, disparador y parámetros.
- Calidad del diseño sonoro.
- Gráfica aplicada a la plataforma.
- Funcionamiento y publicación.
- Profundidad del README y la reflexión.

## Entregables

enlace al repositorio en GitHub, enlace a la plataforma publicada en GitHub Pages, README con las cuatro partes y un video de 30 a 60 segundos que muestre los resultados en uso.
