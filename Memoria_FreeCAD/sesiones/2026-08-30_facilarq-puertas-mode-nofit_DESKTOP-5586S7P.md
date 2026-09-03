# Sesion FacilArquitecturaWB - giro nativo y NO_FIT de puertas

Fecha: 2026-08-30
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.8 / build 2026.08.30.1
Estado: verificado_mcp

## Hallazgo generalizable

En `ArchWindow` los metadatos semanticos y `Normal` no determinan por si mismos el
cuadrante de una hoja. La cadena `Mode1/Mode2` dentro de `WindowParts` gobierna el
signo de rotacion. Tomando el eje fisico desde la bisagra hacia la otra jamba,
FreeCAD 1.1.3 usa:

- `Mode1`: normal izquierda del eje;
- `Mode2`: normal derecha del eje.

La traduccion estable debe comparar vectores fisicos. Asi el resultado permanece
igual cuando un mismo segmento se dibuja en sentido START->END o END->START.

## Guardas geometricas

La evidencia de una cara para alinear una jamba no equivale a evidencia para
inferir giro. En un cruce puede aplicarse `JAMB_ONLY` y conservar apertura `AUTO`.
Antes de cualquier snap deben comprobarse las dos jambas contra caras opuestas;
si el ancho no cabe, devolver `NO_FIT` y no reducir ni trasladar el Sketch.

Caso real 1416: 903.036 mm frente a 830.000 mm de luz, penetracion 73.036 mm.

## Validacion

- matriz de ocho casos con vector real de hoja medido en solidos;
- documento 1416 sobre copia: indices 6/1/8/3 aprobados;
- Tabla de Puertas, cambio de tipo, puerta doble, ventanas y aberturas: aprobados;
- Host, corte, idempotencia, Undo/Redo y reapertura: aprobados;
- original: 157 objetos y `isTouched=False`.

Respaldo previo: `FacilArquitecturaWB/Respaldos_2026-08-30_FA_puertas_fase2_pre_build`.
