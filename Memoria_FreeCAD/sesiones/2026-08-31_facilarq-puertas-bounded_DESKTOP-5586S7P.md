# Sesion FacilArquitecturaWB - puertas acotadas BOUNDED

Fecha: 2026-08-31
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.11 / build 2026.08.31.2
Estado: verificado_mcp

## Hallazgo geometrico generalizable

La distancia minima a una cara lateral no basta para decidir un desplazamiento
longitudinal de una abertura. Si el segmento proyectado queda completamente entre
dos caras externas opuestas y cabe con holgura positiva, ambas caras son jambas
geometricamente validas. Elegir la mas cercana traslada silenciosamente la fuente,
aunque ancho, Host y corte continuen siendo validos.

Regla estable: calcular las posiciones de ambas caras sobre el eje del vano. Si una
queda estrictamente antes del START, la otra despues del END y la separacion supera
el ancho, devolver un estado conservador `BOUNDED`. El Sketch conserva posicion y
ancho; la mejor candidata puede seguir aportando bisagra y cuadrante, pero no
autoriza una traslacion. Evaluar `NO_FIT` antes de `BOUNDED`.

Este patron exige separar dos resultados del planificador: `applied` para movimiento
y `swing_resolved` para orientacion. Los consumidores no deben asumir que orientar
una puerta obliga a mover su eje.

## Evidencia real 1416

- GeometryIndex 1: dos caras opuestas, luz `830.000 mm`, ancho `663.851 mm`,
  holgura `166.149 mm`; el algoritmo anterior desplazaba `56.342 mm`.
- GeometryIndex 6: una sola cara externa; snap unico de `53.441 mm`.
- La geometria CAD de ambos casos coincidia con el Sketch antes del snap, por lo
  que no aportaba una autoridad distinta para decidir el movimiento.
- A/B en copia exacta: neutralizar solo el movimiento del indice 1 lo devolvio al
  buque; el indice 6 no cambio.

## Validacion

- copia real: 10 puertas, Hosts y cortes positivos;
- indice 1 `BOUNDED`, `START/RIGHT/Mode2`, sin shift;
- indice 6 `SNAPPED`, `START/LEFT/Mode1`;
- indices 8, 3 y 9 conservaron `NO_FIT`/`JAMB_ONLY`;
- reejecucion, Undo/Redo y guardar/reabrir aprobados;
- E2E de esquinas, Tabla de Puertas y puerta doble aprobados;
- E2E compartido de puertas/ventanas y Tabla de Ventanas aprobados;
- suite focal 62/62.

El original ya estaba tocado al inicio con 137 objetos. No se modifico ni se
guardo. Respaldo previo:
`FacilArquitecturaWB/Respaldos_2026-08-31_FA_puertas_bounded_pre_build2/`.
