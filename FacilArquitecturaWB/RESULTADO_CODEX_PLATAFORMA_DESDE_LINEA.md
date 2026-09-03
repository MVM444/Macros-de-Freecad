# Resultado Codex - plataforma de atencion desde una linea

Fecha: 2026-08-10
Version: `0.10.0`
Build: `2026.08.10.2`
FreeCAD validado: `1.1.3`

## Resultado

`FA_CreateServicePlatformFront` ahora crea una plataforma desde una arista recta o
un Sketch con una sola linea principal. El flujo anterior no se elimino: los
documentos que ya contienen plataformas con seis Sketches siguen usando el builder
historico al ejecutar `FA_UpdateServicePlatformFront`.

## Semantica de la linea

- P0 a P1 define X local, posicion, orientacion y longitud total.
- La perpendicular izquierda define Y local canonica.
- `LadoFuncionario` escoge izquierda/derecha mirando P0 a P1.
- `InvertirDireccion` intercambia P0 y P1 de manera independiente.
- El `Placement` global de un Sketch se aplica al leer sus extremos.
- La longitud se deriva en cada actualizacion; no se guarda como autoridad paralela.
- Se rechazan curvas, Sketches con mas de una linea principal, lineas menores de
  500 mm y lineas con diferencia Z mayor de 1 mm.

## Resultado BIM y arbol

```text
Plataforma de atencion
|-- Cuerpo_Plataforma
`-- Vidrios_Plataforma
```

`Cuerpo_Plataforma` es un compound de panel inferior, mostrador, escritorios,
divisiones y parantes. `Vidrios_Plataforma` agrupa los paños transparentes. Cada
puesto deja un hueco rectangular real al construir piezas de vidrio alrededor de
la abertura; no se agrega un objeto de simulacion ni se altera el arbol. La hoja
de parametros se conserva oculta y las areas de atencion estan desactivadas por
defecto.

Propiedades principales:

- `NumeroPuestos`, `LongitudTotal`, `AlturaMostrador`, `CotaSuperiorVidrio`;
- `MostrarAberturaVidrio`, `AnchoAberturaVidrio`, `AltoAberturaVidrio` y
  `AlturaAberturaVidrio` (cota inferior local);
- `ProfundidadEscritorio`, `LadoFuncionario`, `InvertirDireccion`;
- `MostrarAreasAtencion`, `SourceObject`, `SourceSubelement`, `HostWall`;
- `IfcType = Furniture`, `PredefinedType = USERDEFINED` y `FA_CreateWall = false`;
- aliases `FA_*` y `FA_GeneratedBy` para automatizacion/compatibilidad.

## Host BIM y Puriscal

La herramienta busca un muro Arch/BIM colineal dentro de 250 mm. No crea un muro si
no lo encuentra. En Puriscal se detectaron dos muros geométricamente coincidentes:
`Wall002` y una copia rotulada como auxiliar para referencias electricas. El selector
descarto la copia auxiliar y reutilizo `Wall002`. El modelo mantuvo los dos muros que
ya existian; la herramienta creo cero muros.

## Aberturas del vidrio

- Se genera exactamente una abertura por puesto, centrada en el ancho util del paño.
- El valor inicial es 300 x 300 mm con la base en 740 mm.
- La cota 740 mm del mostrador y la cota superior 1800 mm se leen del detalle
  arquitectonico. El dibujo no aporta una cota inequivoca para el hueco; por eso
  300 x 300 mm es un valor provisional editable y no normativo.
- La actualizacion agrega las cuatro propiedades a plataformas compactas v0.10.0
  que todavia no las tengan.
- Las validaciones rechazan huecos sobre montantes, debajo del mostrador o fuera
  del paño.

## Zonas funcionales

No se generan por defecto. `MostrarAreasAtencion = true` crea una representacion
auxiliar, fuera del grupo compacto y oculta en el arbol; volver a `false` elimina
solamente esa representacion generada. Las zonas de plataformas historicas no se
alteran.

## Pruebas ejecutadas

- 139 pruebas Python del workbench: aprobadas.
- `freecad_service_platform_line_smoke.py`: horizontal/vertical/diagonal mediante
  marco puro, Sketch trasladado y rotado, inversion, lados, 1/3/5 puestos, arista
  directa, huecos reales, cambio de dimensiones, migracion v0.10.0, host/no host,
  zonas, actualizacion estable y reapertura: aprobado.
- `freecad_service_platform_smoke.py`: compatibilidad del generador historico,
  Undo/Redo y reapertura: aprobado.
- `freecad_puriscal_platform_regression.py`: copia de Puriscal, `Wall002`, tres
  puestos de 1000 mm, cero muros nuevos, actualizacion y reapertura: aprobado.
- `freecad_la_cruz_platform_line.py`: copia de La Cruz 2.1, linea de 3000 mm, tres
  puestos de 1000 mm, tres aberturas reales, sin host y sin duplicados: aprobado.

Archivos de prueba generados, sin modificar los originales:

- `.codex_tmp/service_platform_line_smoke.FCStd`
- `.codex_tmp/Puriscal_Plataforma_desde_linea_regression.FCStd`
- `.codex_tmp/La_Cruz_V2_2_Plataforma_desde_linea.FCStd`

## Pendientes reales

- Validar visualmente en la sesion GUI del usuario el lado elegido para el caso
  definitivo de La Cruz antes de considerar esa ubicacion como aprobada.
- Definir, si la CCSS aporta un detalle normativo adicional, espesores/materiales
  finales de paneles, parantes y vidrio. Los valores actuales son editables y no se
  presentan como norma.
- La ventanilla de caja sigue siendo un comando independiente y no forma parte de
  esta plataforma.
