# Auditoria de puertas y ventanas BIM: Puriscal

Fecha: 2026-08-09  
FreeCAD verificado: 1.1.3

## Alcance de la busqueda

Se revisaron el repositorio completo, el directorio principal de macros, el historial
Git y las ramas disponibles. La busqueda incluyo Puriscal, puertas, ventanas,
openings, hosts, `Arch.makeWindow`, presets BIM y propiedades `FA_*`.

El arbol de trabajo ya contenia cambios locales de FacilArquitecturaWB y ElectricCR.
Esta tarea conserva esos cambios y no modifica GameEngineExportWB ni ElectricCR.

## Hallazgos recuperados de Puriscal

La solucion anterior si existe y no debe reescribirse desde cero:

- `Scripts Varios/FacilArquitectura_BIM/InsertarPuertasBIMDesdeRecintos.FCMacro`
  crea el preset nativo `Simple door`, proyecta cada eje sobre el muro, escoge una
  bisagra segun el recinto y asigna `Hosts = [wall]`.
- `Scripts Varios/FacilArquitectura_BIM/InsertarVentanasBIMDesdeRecintos.FCMacro`
  crea presets nativos de ventana, soporta tramos de muro colineales, usa antepecho y
  altura configurables y asigna el mismo alojamiento nativo.
- `Scripts Varios/FacilArquitectura_BIM/Puriscal/AgregarPuertasFrentePuriscal.FCMacro`
  resuelve el caso particular de una puerta sencilla y una puerta frontal de doble
  hoja. Esta logica especifica no debe entrar en el nucleo general.
- La documentacion consolidada registra 18 vanos logicos de puerta, 19 hojas BIM y
  8 ventanas. Antes de las adiciones frontales, la macro general creo 16 puertas.
- El muro anfitrion autoritativo fue `Wall002`, basado en `FA_GridWallTrace`, con
  espesor 120 mm y altura 3000 mm.
- La reduccion documentada del volumen del muro confirma que los huecos fueron cortes
  reales y no solo geometria visual.

El modelo actual localizado es:

`2026/08-Agosto-2026/Puriscal/Puriscal Depurado.FCStd`

Se inspeccionara unicamente una copia temporal. El original no sera modificado.

## Codigo de GameEngineExport revisado

`GameEngineExportWB/macros/bim_from_selected_sketch.py` aporta referencias utiles:

- construccion de perfiles verticales desde ejes 2D;
- listas `WindowParts` para marco, vidrio y panel de puerta;
- llamada a `Arch.makeWindow`;
- transformacion de Placement para muros diagonales.

No es una implementacion reutilizable directamente porque usa metadatos `GEE_*`,
grupos con marcas temporales y no resuelve ni asigna un muro anfitrion. Los comandos
Quick Example dependen ademas de objetos `GEE_QuickExample`.

## Historial Git

Los commits `a3c271a`, `3164dfb`, `05bc309`, `25a5b12` y `f40217f` contienen la
evolucion de las macros genericas de GameEngineExport. Ninguna rama contiene los
comandos `FA_CreateDoorsBIM` o `FA_CreateWindowsBIM`. FacilArquitecturaWB y las
macros de Puriscal entraron al historial como familias separadas; no hay un comando
nativo eliminado que pueda restaurarse sin adaptacion.

## API nativa confirmada en el codigo instalado

El codigo fuente incluido con FreeCAD 1.1.3 confirma:

- `Arch.makeWindow(baseobj, width, height, parts, name)` crea el objeto nativo
  `Part::FeaturePython` con proxy `ArchWindow._Window`.
- La misma clase representa puertas y ventanas mediante `IfcType` y componentes.
- `ArchWindowPresets.makeWindowPreset` crea `Simple door`, `Open 1-pane`,
  `Sliding 2-pane` y otros presets usando internamente `Arch.makeWindow`.
- La relacion real de alojamiento es `Hosts`, una `App::PropertyLinkList`.
- `MoveWithHost` se activa por defecto.
- `HoleDepth` controla la profundidad del volumen de corte; con valor cero intenta
  usar el espesor del anfitrion.
- `Opening` controla el porcentaje de apertura de hojas.
- La definicion geometrica de componentes se guarda en `WindowParts`.
- El muro descubre ventanas/puertas en sus enlaces entrantes y sustrae el resultado
  de `getSubVolume()` durante el recompute.
- No existe `ArchWindow.AllowedHosts` en esta instalacion; no se debe depender de ese
  simbolo historico.

La prueba ejecutada contra objetos reales confirmo:

- `TypeId = Part::FeaturePython` y proxy `ArchWindow._Window`.
- `Hosts` es `App::PropertyLinkList`, `MoveWithHost = true` y el `Base` es Sketcher.
- Una puerta 900 x 2100 en muro de 200 mm redujo 378,000,000 mm3.
- Una ventana 1200 x 1200 en el mismo espesor redujo 288,000,000 mm3.
- Los enlaces, cortes y tipos IFC persistieron al guardar, cerrar y reabrir.

## Inspeccion de la copia actual de Puriscal

Se creo la copia temporal
`.codex_tmp/Puriscal_Depurado_openings_audit_20260809.FCStd`. El original no se
modifico. La inspeccion read-only encontro:

- 19 objetos con `FA_Role = door`;
- 8 objetos con `FA_Role = window`;
- 27 objetos nativos reconocidos por Draft como `Window`;
- `IfcType = Door` o `IfcType = Window` segun corresponde;
- Sketch Base y `Hosts = [Wall002]` en los 27 objetos.

La prueba de compatibilidad ejecuto el nuevo nucleo sobre otra copia derivada. Los 19
indices de puerta y 8 indices de ventana historicos fueron reconocidos mediante los
aliases `FA_SourceDoorAxes` y `FA_SourceWindowAxes`; se crearon cero duplicados y el
conteo se conservo al guardar y reabrir.

## Codigo que se reutilizara

- Proyeccion, distancia, compatibilidad angular y soporte colineal de las macros de
  Puriscal.
- Presets y Placement nativos ya validados.
- `make_arch_window` y las utilidades Arch/BIM existentes en `core/bim_utils.py`.
- Estructura de proyecto, parametros, mensajes, transacciones y propiedades del
  workbench actual.
- Metadatos de trazabilidad `FA_SourceGeometryIndex`, fuente, host, medidas y
  confianza.

## Codigo que no se copiara

- Dependencias `GEE_*` o Quick Example.
- Busqueda de un unico `Wall002` por nombre o puntuacion global.
- Dependencia obligatoria de rectangulos de recinto para crear una abertura.
- Eliminacion completa de todos los resultados anteriores al reejecutar.
- Regla particular de indices 0, 17 y 18 de las puertas frontales de Puriscal.

## Lo que falta realmente

- Nucleo general `opening_utils.py` para varios sketches y varios muros.
- Seleccion de anfitrion por distancia, proyeccion, orientacion y ambiguedad.
- Idempotencia por fuente, indice geometrico y tipo de abertura.
- Parametros pequenos de interfaz para puertas y ventanas.
- Comandos estables `FA_CreateDoorsBIM` y `FA_CreateWindowsBIM`.
- Grupos no destructivos dentro de `03_BIM`.
- Pruebas puras, prueba integral en FreeCAD y validacion sobre copia de Puriscal.

## Decision de arquitectura

La autoridad semantica sera el objeto nativo Arch Window con `IfcType = Door` o
`IfcType = Window`. El Sketch de perfil sera su `Base`; el muro sera un enlace real
en `Hosts` y tambien se expondra como `FA_HostWall` para el contrato Facil
Arquitectura. Los ejes DXF seguiran siendo fuentes autoritativas y no se modificaran.
