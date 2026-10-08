# template portada post

Genera la imagen del **post 1** del carrusel de Instagram. El **post 2** es el video de tu visualización.

## cómo usarlo

1. Abre `index.html` en el navegador.
2. Arrastra tu `datos.json` y la imagen de la portada del álbum (cuadrada, ideal 1000×1000 px o más).
3. Revisa la vista previa y presiona **Descargar PNG**. La imagen sale en 9:16 (1080×1920), igual que el video.

También puedes escribir los datos directamente en el formulario, sin JSON.

## datos.json

```json
{
  "estudiante": "Nombre Apellido",
  "cancion": "Nombre de la canción",
  "artista": "Artista",
  "album": "Nombre del álbum",
  "portada": "portada.jpg"
}
```

- `portada` es el nombre del archivo de imagen que subes junto al JSON.
- `album` es opcional.

Si se arrastran varios JSON con sus imágenes a la vez, se genera una portada por cada uno y aparece el botón **Descargar todas**.
