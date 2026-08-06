# ElectricCR

## Barra de herramientas compacta

ElectricCR arranca en modo compacto: muestra una barra principal con el
panel de macros y recarga, mientras el catalogo completo de macros queda
en los menus del workbench.

Opciones en `ElectricCR/config.json`:

- `macro_toolbar_mode: "compact"` muestra solo los grupos listados en
  `macro_toolbar_groups`.
- `macro_toolbar_mode: "full"` restaura una barra por cada grupo de macros.
- `macro_toolbar_mode: "menu_only"` deja todas las macros solo en menus.
- `show_bim_toolbar: true` muestra una barra BIM/Arch minima, separada de Draft.
- `show_draft_toolbars: true` vuelve a mostrar las barras Draft dentro del
  workbench.

## Registro de uso

ElectricCR mantiene dos registros:

- `ElectricCR/logs/tool_usage.json`: acumulado rapido por herramienta.
- `ElectricCR/logs/tool_events.jsonl`: historial evento por evento para
  analizar sesiones, cambios de flujo, grupos usados consecutivamente y
  herramientas que se usan juntas.

Cada evento guarda sesion, timestamp, herramienta anterior, grupo anterior,
segundos desde el evento anterior, grupo/barra inferido, macro relativa,
documento activo y workbench activo cuando FreeCAD expone esos datos.

## Prototipo de modos manuales

`interface_mode: "modes_prototype"` activa una prueba reversible de modos
manuales dentro del mismo workbench ElectricCR. El panel `ElectricCR Modos`
permite elegir:

- `Areas`
- `Iluminacion`
- `Tomacorrientes`
- `Conexiones`
- `Personalizado`

El modo se puede cambiar desde una lista desplegable en la barra `ElectricCR`
o desde el panel acoplable. El modo seleccionado se guarda en parametros de
FreeCAD. Para volver al comportamiento anterior, cambiar `interface_mode` a
`"legacy"` en `ElectricCR/config.json`.

`Objetos` y `Draft compacto` son barras permanentes. El modo `Personalizado`
lee su seleccion desde `custom_mode_toolbars` en `config.json`.

## Insertar Tablero

## Luminarias sobre cielo modular

`Iluminación/ColocarLuminarias_Link.FCMacro` ofrece la opcion `Alinear a cielo
modular`, activa por defecto con modulo de 600 mm. En ese modo conserva la
cantidad de filas y columnas calculada por ElectricCR, pero elige centros de
celdas completas y equilibradas dentro del recinto en vez de dividir el largo y
el ancho proporcionalmente.

Cada `App::Link` creado guarda el contrato que consume Facil Arquitectura:

- `ECR_CeilingModule`
- `ECR_CeilingRow`
- `ECR_CeilingColumn`
- `ECR_CeilingRoom`
- `ECR_CeilingAligned`

Si el recinto no contiene suficientes celdas completas para la cantidad pedida,
la macro informa la incompatibilidad y conserva para ese recinto la distribucion
proporcional anterior.

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
