# tarea-07

## TACTO

Desarrolla tu propia plataforma web en la que un teléfono funcione como control remoto táctil de una experiencia de imagen y sonido. Puedes trabajar de forma individual o en duplas.

El objetivo es entender el tacto como un sentido que se presta a otros. Importa qué gesto de la mano (posición, presión, cantidad de dedos, giro del teléfono) transforma qué cualidad de la imagen o del sonido, y qué relación construyes entre ellos. Te interesa menos que funcione y más que se sienta como tocar la imagen y escuchar ese contacto.

### La herramienta base

Trabajarás a partir de [Tacto](https://github.com/fefeliperoar/tacto) to an external site., que corre en el navegador. El teléfono envía en tiempo real sus datos por MQTT, un protocolo de mensajes que conecta dispositivos a través de un intermediario (broker). La experiencia en el computador los recibe y los lleva a audio e imagen mediante un panel de conexiones.

- Del teléfono: posición del toque (X, Y), cantidad de dedos, presión, diámetro del contacto y giro en tres ejes. Opcionalmente, micrófono y cámara.
- De la experiencia: audio (oscilador o tus propios sonidos), imagen (animación, video o cámara web), física del material (tela, agua, squishy, remolino) y un panel donde conectas cada dato con cada variable.
El README del repositorio explica cada función y cómo agregar variables o materiales propios.

### La plataforma a desarrollar

Tu plataforma es una herramienta especializada en el concepto que elijas. Puedes partir de Tacto o construirla desde cero, siempre que el teléfono se conecte por MQTT.

- Concepto: elige una relación entre gesto, imagen y sonido y detalle (por ejemplo: acariciar recuerdos queridos, desgasta su propia existencia, eliminando rastros de audio y visión).
- Tacto: decide qué gestos usas y qué controla cada uno. Cada conexión debe tener sentido dentro del concepto, no estar ahí solo porque existe.
- Visión y oído: diseña cómo la imagen y el sonido responden al toque. Reúne entre 5 y 15 sonidos propios o de uso libre (indica origen y licencia) y propón una imagen o video que se transforme con el gesto.
- Conexión MQTT: el teléfono debe conectarse a tu plataforma por MQTT y funcionar desde su enlace.
- Gráfica: nombre, tipografía, color y composición deben responder al concepto, como en una pieza de diseño completa.
- Publicación: la plataforma queda publicada en GitHub Pages.
Piensa la plataforma como una herramienta que otra persona podría usar para explorar tu tema, no como una demo técnica.

### El README

Debe incluir tres partes:

1. Concepto. Qué relación propones entre tocar, ver y oír, y qué quieres que la persona sienta o descubra.
2. Funcionamiento. Qué gestos controlan qué variables (incluye una tabla de conexiones), cómo se conecta el teléfono por MQTT y qué sonidos usaste, con autoría declarada.
3. Reflexión. Qué descubriste al traducir el tacto en imagen y sonido, qué queda fuera de tu sistema, y al menos dos mejoras concretas.

### Proceso sugerido

1. Parte por la relación, no por la técnica. Escribe en una frase qué gesto produce qué imagen y qué sonido.
2. Prueba Tacto con tu teléfono y observa qué datos entrega (presión y diámetro varían según el modelo).
3. Reúne sonidos cortos (0,3 a 5 segundos) y un video o animación.
4. Diseña en papel la tabla de conexiones antes de programarla.
5. Desarrolla y prueba seguido; para trabajar rápido, usa el modo local (node server.js) con el teléfono en tu hotspot.
6. Publica en GitHub Pages y documenta mientras el proceso está fresco.

### Criterios de evaluación

- Claridad del concepto.
- Coherencia entre gesto, imagen y sonido.
- Uso del tacto y de las variables del teléfono.
- Conexión MQTT y funcionamiento.
- Gráfica aplicada a la plataforma.
- Calidad del README y de la reflexión.

## Entregables

enlace al repositorio, enlace a la plataforma publicada y un video de 30 a 60 segundos que muestre el teléfono controlando la experiencia.