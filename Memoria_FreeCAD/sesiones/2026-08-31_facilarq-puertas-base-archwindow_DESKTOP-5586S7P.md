# Sesion FacilArquitecturaWB - Base ArchWindow de puerta BOUNDED

Fecha: 2026-08-31
Equipo: DESKTOP-5586S7P
FreeCAD: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.11 / build 2026.08.31.3
Estado: verificado_mcp / verificado_visual / validacion_manual_pendiente

## Hallazgo generalizable

En el preset nativo `Simple door`, el ancho de entrada describe `Wire0`, marco
exterior. La hoja se genera desde `Wire1`, que aplica los margenes `Frame2` y
`Frame3`. Por ello, que el contorno exterior del Base coincida con el segmento no
demuestra que la hoja, bisagra o arco visible coincidan.

Para una abertura `BOUNDED`, el Sketch es el segmento de hoja autoritativo y no hay
un snap longitudinal que absorba el marco. La adaptacion correcta es de Base:

1. leer los margenes nombrados reales del preset;
2. mover el origen exterior hacia atras por `Frame2`;
3. aumentar la restriccion Width del Base en `Frame2 + Frame3`;
4. mantener `Window.Width`, `FA_Width_mm` y `FA_Projected*` sin cambios;
5. dejar que el Host corte el marco exterior ampliado.

No modificar el planificador geometrico para corregir una divergencia de preset.
Separar siempre Sketch, proyeccion, Wire0, Wire1, Shape y subvolumen en el
diagnostico.

## Evidencia 1416

GeometryIndex 1 antes:

- Sketch/FA: `0..663.850602 mm`;
- Wire0/corte: `0..663.850602 mm`;
- Wire1: `50..613.850602 mm`;
- bisagra fisica: `t=50`, CAD: `t=0`;
- hoja: `563.850602 mm`, CAD: `663.851993 mm`.

Despues:

- Wire1/hoja: `0..663.850602 mm`;
- marco/corte: `-50..713.850602 mm`;
- caras delimitadoras: `-56.341660..773.658340 mm`;
- residuo Wall/subvolumen: `0 mm3`;
- Width publico: `663.850602 mm`.

GeometryIndex 6 no cambia. Su bisagra CAD queda en `t=53.440599`, muy cerca del
retranqueo nativo `t=50`, lo que explicaba por que funcionaba como control visual.

## Validacion

- copia real abierta `FA_Geom1_Downstream`: 10 puertas, visual superior correcto;
- reejecucion, Undo/Redo y reapertura aprobados;
- prueba focal 63/63;
- E2E de esquina con caso BOUNDED: aprobado, 9 puertas;
- Tabla de Puertas, puerta doble, ventanas y Tabla de Ventanas: aprobadas;
- original intacto, 137 objetos, estado previo `isTouched=True`.

Respaldo:
`FacilArquitecturaWB/Respaldos_2026-08-31_FA_puertas_base_archwindow_pre_build3/`.
