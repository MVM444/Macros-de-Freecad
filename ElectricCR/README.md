# ElectricCR

## Insertar Tablero

Archivos activos:

- `ElectricCR/Insertar_Tablero.FCMacro`
- `ElectricCR/electriccr/features/tablero_electrico.py`

Respaldo previo a la integracion Eaton:

- `Respaldos/ElectricCR_Tablero_Eaton_20260612_093935/`

## Modos de dimensiones

La macro de tablero ahora tiene dos perfiles:

- `Generico`
- `Eaton CH Plug-on Neutral`

`Generico` mantiene la tabla simplificada original del proyecto.

`Eaton CH Plug-on Neutral` agrega seleccion por catalogo con estos campos:

- `Variante Eaton`
  - `Auto`
  - `Convertible`
- `Amp Eaton`
  - `100`
  - `125`
  - `150`
  - `200`
  - `225`
- `Caja Eaton`
  - `Auto`
  - `X0` a `X9`

## Logica Eaton

Cuando `Caja Eaton = Auto`, el backend intenta resolver la caja usando:

- cantidad de espacios
- `MainBreaker`
- variante Eaton
- amperaje

En `Variante Eaton = Auto`, el backend toma:

- `MainBreaker` si el checkbox principal esta activado
- `MainLug` si el checkbox principal esta desactivado

Si no existe una coincidencia exacta en las reglas cargadas desde el catalogo, la macro devuelve error en vez de adivinar una caja.

Si `Caja Eaton` se fija manualmente en `X0` a `X9`, esa caja domina las dimensiones.

## Fuente catalogo usada

Manual revisado:

- `C:/Users/marco/Desktop/Electric CR/loadcenters-and-circuit-breakers-v1-t1-ca08100002e.pdf`

Tablas usadas:

- Pagina 30: `Plug-on Neutral Loadcenter Box Sizes for X1–X9`
- Paginas 7, 9 y 10: reglas de seleccion por espacios, amperaje y configuracion
- Pagina 29: `X0`, porque la tabla puntual de la pagina 30 inicia en `X1`

## Notas tecnicas

- El objeto final insertado sigue siendo `App::Link`.
- La libreria interna sigue usando masters ocultos.
- `CajaModelo` guarda la caja realmente usada.
- `PerfilDimensiones`, `ConfiguracionCatalogo`, `AmperajeNominal` y `CajaEaton` quedan guardados en el link.
- El perfil por defecto sigue siendo `Generico`.

## Limitacion actual

La automatizacion Eaton se basa solo en las combinaciones que quedaron codificadas desde el catalogo revisado. Si aparece una combinacion no incluida en esas paginas, la macro no inventa una equivalencia.
