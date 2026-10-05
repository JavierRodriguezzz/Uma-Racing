# Escenarios comprables

Cada escenario de la tienda (tabla `items`, tipo `escenario`) se carga desde `escenarios/<codigo>/`
con tres imágenes:

| Archivo      | Uso                        | Tamaño final en el juego          |
|--------------|----------------------------|-----------------------------------|
| `fondo.png`  | paisaje que se desplaza    | alto 425 px, ancho proporcional   |
| `calle.png`  | pista (capa trasera)       | 1200 × 200 px                     |
| `calle2.png` | pista (capa delantera)     | 1200 × 200 px                     |

Si la carpeta no existe, el juego usa el escenario clásico.
`atardecer/` es un ejemplo generado con un filtro de color; reemplácenlo por arte propio.
