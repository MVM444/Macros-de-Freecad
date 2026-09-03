# Sesion FacilArquitecturaWB - GeometryIndex 9 y aviso de build

Fecha: 2026-08-30
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.8 / build 2026.08.30.2
Estado: verificado_mcp

## Hallazgo geometrico generalizable

En un cruce, una cara perpendicular unica puede quedar dentro del propio segmento
de abertura. Esa cara no representa una jamba exterior segura. Si el giro tampoco
esta resuelto (`JAMB_ONLY`), trasladar toda la puerta hasta esa cara desplaza el vano
respecto de su fuente.

Regla estable: expresar la cara candidata sobre el eje de la abertura. Cuando
`0 < target_axis_mm < opening_length`, con tolerancia en ambos extremos, conservar
los endpoints proyectados y mantener el candidato solo como diagnostico. Las caras
antes o despues del tramo siguen siendo candidatas para alinear la jamba.

La prueba A/B es obligatoria para regresiones de este tipo: misma copia, Sketch,
Host y ruta de creacion; primero algoritmo actual y despues neutralizar solo el
resolver nuevo en memoria. En el caso 1416, la diferencia fue `64.386719 mm` y la
variante neutralizada recupero visual y numericamente la posicion pre-snap.

## Avisos de instalacion

Un aviso basado solo en version semantica no detecta builds nuevos que mantienen la
misma version. Persistir por separado `LastNotifiedVersion` y `LastNotifiedBuild`
permite comparar la identidad completa, migrar el parametro heredado y mostrar un
solo aviso por build. Persistir antes de abrir el dialogo evita repeticiones si la
interfaz se reactiva.

## Validacion

- documento real 1416 sobre copia exacta: indices 9/6/8/3 aprobados;
- 10 puertas con Host y corte, reejecucion, Undo/Redo y reapertura;
- E2E de esquina y Tabla de Puertas aprobados;
- transicion Qt real build `.1 -> .2`: un dialogo; segunda activacion: ninguno;
- original: 157 objetos, guardado y `isTouched=False`.

Respaldo previo:
`FacilArquitecturaWB/Respaldos_2026-08-30_FA_geom9_build_notice_pre_build2/`.
