# FacilArquitectura - cierre de buques opening-first

Fecha: 2026-08-28
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.7 / build 2026.08.28.2

## Hallazgo reusable

Para reconstruir continuidad de muros desde ejes de puertas/ventanas no conviene
enumerar primero pares globales de pared y filtrar despues por abertura. Ese
orden elimina antes de tiempo:

- aberturas reales mayores que el limite generico de busqueda;
- cadenas consecutivas puerta+ventana;
- puertas junto a esquina/T, donde un lado del buque es una pared de apoyo y no
  otro tramo colineal.

El modo de seleccion explicita tampoco debe compensar ese descarte con una zona
demasiado permisiva: puede reasignar la abertura a otro buque cercano.

## Patron validado

1. Transformar cada linea de abertura al sistema local del Sketch de muro.
2. Conservar Sketch, Label, `GeometryIndex` y `FA_CenterlineKind`.
3. Agrupar solo aberturas consecutivas, colineales y sobre el mismo eje.
4. Buscar primero tramos de muro paralelos a ambos lados de la region.
5. Permitir que la longitud real de la region amplie localmente el limite
   generico; no aumentar tolerancias globales.
6. Si solo existe un tramo colineal, permitir extenderlo hasta la interseccion
   finita de una pared de apoyo, sin modificar esa pared.
7. Rechazar cierres atravesados por una tercera pared.
8. Deduplicar candidatos fisicamente equivalentes y no aplicar si los dos
   mejores cierres distintos tienen score equivalente.
9. Mantener un fallback separado para representaciones historicas
   perpendiculares/oblicuas.
10. Exponer el plan como JSON-compatible antes de escribir el documento.

## Evidencia 1416

- muro fuente: 37 lineas;
- aberturas: 14 ventanas + 10 puertas + 1 puerta principal;
- regiones: 23, por dos cadenas consecutivas;
- cierres: 18 merges + 5 extensiones a pared de apoyo;
- resultado: 19 lineas, 44 restricciones;
- ambiguas/rechazadas: 0/0;
- muro Arch: un solido valido y paramétrico;
- cortes BIM posteriores: ventana y puerta con `Hosts` y reduccion real de
  volumen;
- Undo/Redo, repeticion sin duplicados y guardar/reabrir: aprobados.

## API

- `diagnose_wall_gap_closures(...)`: nucleo puro/dry-run.
- `diagnose_closed_wall_sketches(...)`: adaptador FreeCAD de lectura.
- `bridge_wall_gaps(...)`: aplica el mismo plan en memoria.

El documento real usado para diagnostico no se guardo ni modifico. La regresion
queda en `FacilArquitecturaWB/tests/fixtures/close_wall_gaps_1416.json`.
