# RESULTADO CODEX - ElectricCR / RoomResolver fase 2A

Fecha: 2026-09-01 America/Costa_Rica
FreeCAD: `1.1.3`, revision `20260725`
Estado: **IMPLEMENTADO / PROBADO / VERIFICADO MCP**.

ElectricCR adopto RoomResolver solamente en el calculo de iluminacion. Space
tiene prioridad sobre Area legacy; AMBIGUOUS y NOT_FOUND son seguros;
`DatosRecintos` conserva 12 columnas; no se modificaron Spaces ni dispositivos.
El contrato `relaciones -> arbol` quedo documentado en
`ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md` sin migracion de objetos ni
reorganizacion de modelos originales.

Evidencia detallada: `ElectricCR/RESULTADO_CODEX.md`.

---

# RESULTADO CODEX - RoomResolver comun fase 1 read-only

Fecha: 2026-09-01 America/Costa_Rica
Equipo: `DESKTOP-5586S7P`
FreeCAD verificado: `1.1.3`, revision `20260725`
Componente nuevo: `CRBIMCore 0.1.0`
Estado: **IMPLEMENTADO / PROBADO / VERIFICADO MCP / READ-ONLY CONFIRMADO**.

## Diagnostico previo

No existia `RoomResolver` ni un paquete neutral compartido. Se auditaron las fuentes reales antes de programar:

- deteccion parcial de Spaces y Areas en `FacilArquitecturaWB/core/ceiling_utils.py`;
- metadatos de `FA_RectangularAreaAnalysis`;
- `AreaPorClick` y `PoligonosRecintosDesdeArchWalls`;
- geometria 2D neutral ya probada en el modulo sanitario MEP;
- contrato y seguimiento `HVACSpace.BaseSpace` en MEPWorkbenchCR;
- API real de `Arch.makeSpace` en FreeCAD 1.1.3.

La prueba MCP confirmo que un Space BIM manual es `Part::FeaturePython`, con `IfcType=Space`, `Proxy.Type=Space` y Base nativa, sin necesitar propiedades `FA_*`.

## Implementacion

Se creo el paquete neutral de raiz `CRBIMCore`:

- `room_resolver_core.py`: contrato puro JSON-compatible, normalizacion de poligonos, contencion por punto y resolucion `RESOLVED/AMBIGUOUS/NOT_FOUND`;
- `freecad_room_adapter.py`: deteccion read-only de Spaces, Areas heredadas, Level, geometria y enlaces HVAC;
- `README.md`: contrato, API, fuentes admitidas, prioridad y limitaciones;
- `tests/test_room_resolver_core.py`: 11 pruebas puras;
- `tests/freecad_room_resolver_smoke.py`: smoke real y persistencia.

Reglas verificadas:

- Space nativo tiene prioridad sobre Area superpuesta;
- dos Spaces plausibles producen `AMBIGUOUS`, nunca "gana el mas pequeno";
- Areas heredadas requieren geometria valida y metadatos, no basta el nombre del grupo;
- `HVACSpace.BaseSpace` se sigue hasta la fuente fisica;
- HVAC convertido sin `BaseSpace` y `SubArea` no ascienden a identidad arquitectonica;
- el contrato puro no contiene referencias a objetos FreeCAD.

## Smoke FreeCAD 1.1.3

Resultado: `ROOM_RESOLVER_FREECAD_SMOKE_OK`.

- candidatos fisicos: 8;
- objetos del documento temporal: 17;
- Space manual sin FA: resuelto;
- Space sobre Area: gano Space;
- `ElectricCRTipo=Area`: fallback aprobado;
- `FA_RectangularAreaAnalysis`: fallback aprobado;
- poligono desde muros y Draft cerrado con metadatos: aprobados;
- dos Spaces: `AMBIGUOUS` con 2 alternativas;
- punto sin recinto: `NOT_FOUND`;
- HVAC enlazado: resolvio `Space`;
- HVAC convertido: `NOT_FOUND`;
- SubArea: `NOT_FOUND`;
- objeto por Placement: resolvio `Space`;
- firma documental antes/despues: identica;
- guardar/cerrar/reabrir: estable;
- documentos y archivos temporales: cerrados/eliminados.

La primera ejecucion del smoke detecto un cambio en `_Part_ShapeCache`, causado por el propio comparador al leer `Shape` en un grupo. Se corrigio solamente el arnes para no inspeccionar Shape donde no es una propiedad real; el resolver nunca habia mutado el documento.

## Pruebas y no-regresion

- pruebas puras RoomResolver: **11/11**;
- importacion de adaptador fuera de FreeCAD: aprobada;
- compilacion Python: aprobada;
- contratos focales de Spaces/demo FA: **22/22**;
- E2E de identidad persistente FA en FreeCAD real: aprobado (`changed=1`, `new_spaces=1`, `stale=3`, `ambiguous=1`, reapertura estable).

No se modificaron `space_utils.py`, ElectricCR, MEPWorkbenchCR ni modelos originales. FacilArquitecturaWB permanece en `0.14.11 / 2026.09.01.14`; el componente comun se versiona independientemente como `CRBIMCore 0.1.0`.

## Conclusion

RoomResolver fase 1 cumple el criterio de cierre. No se agrego UI, no se escribieron propiedades y no se migraron consumidores. Las fases de adopcion por ElectricCR/HVAC/MEP requieren autorizacion posterior.

---

# RESULTADO CODEX - FA Espacios BIM / identidad persistente

Fecha: 2026-09-01 America/Costa_Rica
Equipo: `DESKTOP-5586S7P`
FreeCAD verificado: `1.1.3`, revision `20260725`
Workbench DEV: `FacilArquitecturaWB 0.14.11 / 2026.09.01.14`
Estado: **IMPLEMENTADO / VERIFICADO MCP / SMOKE INTEGRAL APROBADO**.

## Resultado

La actualizacion de recintos conserva la identidad de los `Arch Space` cuando el matching es seguro. El smoke real demostro:

- 3 Spaces iniciales y 3 `App::PropertyLink` externos;
- 1 recinto modificado: `CAMBIO=1`, `MATCH=2`, nuevos `0`;
- mismo `Name`, `FA_RoomID`, `FA_RoomUID`, Base y enlaces despues de actualizar;
- Undo y Redo aprobados;
- 1 recinto nuevo: `NO_MATCH=1` y exactamente 1 Space nuevo;
- 3 Spaces `stale` conservados sin borrar;
- 1 caso deliberadamente duplicado: `AMBIGUO=1`, escrituras `0`;
- guardar, cerrar y reabrir: 5 Spaces y 16 objetos restaurados sin duplicacion por recompute;
- `GameExportExclude=True` conservado en cada Space y Base;
- los probes reabiertos continuaron enlazando los mismos Spaces.

El quinto Space del archivo final es el candidato duplicado creado deliberadamente para demostrar el rechazo ambiguo; no es una duplicacion producida por la sincronizacion.

## Incidencias corregidas

1. FreeCAD 1.1.3 conserva instancias antiguas de comandos cuando no existe `removeCommand`. `FA_DetectRooms2D` y `FA_CreateBIMSpaces` usan ahora `ReloadableCommandProxy`.
2. `FA Detectar recintos 2D` actualiza el unico Sketch documental generado en sitio. Esto evita romper `FA_SourceRoomSketch` de Spaces existentes.
3. La demo generaba Spaces mediante el mismo servicio pero con `FA_GeneratedBy=FA_DemoBuilding`. La recoleccion admite ahora Spaces FA con el mismo Sketch fuente y esquema versionado, sin admitir Spaces Arch ajenos.
4. El arnes E2E cierra por ruta cualquier copia temporal guardada/reabierta antes de reutilizar el archivo y conserva los nombres de los probes antes de cerrar el documento.

## Archivos funcionales y de regresion

- `core/constants.py`: build `2026.09.01.14`.
- `commands/cmd_detect_rooms_2d.py`.
- `commands/cmd_create_bim_spaces.py`.
- `core/room_utils.py`.
- `core/space_utils.py`.
- `tests/test_demo_building_contract.py`.
- `tests/test_space_gameexport_contract.py`.
- `tests/freecad_space_identity_end_to_end.py`.

No se modifico ElectricCR, MEPWorkbenchCR ni el algoritmo de puertas. No se implemento `RoomResolver`.

## Evidencia real FreeCAD/MCP

- Rutas cargadas: `FacilArquitecturaWB/core/space_utils.py` y `core/room_utils.py` desde la copia DEV sincronizada.
- Deteccion real sobre `FA_Demo_Casa_123456`: 2 recintos, mismo `Sketch_Recintos_Cerrados` y enlaces de Spaces preservados.
- Sincronizacion real de la demo: `Space`, `Space001` antes y despues; nuevos `0`, actualizados `0`, ambiguos `0`.
- E2E: `FA_SPACE_IDENTITY_E2E_OK` con `initial_spaces=3`, `changed=1`, `new_spaces=1`, `stale_preserved=3`, `ambiguous=1`, `restored_spaces=5`, `restored_objects=16`.
- FreeCAD permanecio abierto; no se modifico ningun FCStd original del usuario.
- Al cerrar el smoke se cerraron solo los documentos temporales y se eliminaron cuatro artefactos creados por la prueba dentro de `.codex_tmp`; FreeCAD quedo abierto y sin documentos temporales.

## Pruebas locales

- Compilacion Python de los modulos y pruebas tocados: aprobada.
- Contratos focales: **22/22** aprobados.
- El Python local 3.11 no dispone de `pytest`; las 22 funciones focales sin fixtures se ejecutaron directamente y todas aprobaron.

## Conclusion

La tarea **FA Espacios BIM - identidad persistente y sincronizacion no destructiva** cumple sus criterios de aceptacion y queda cerrada. El siguiente desarrollo posible es `RoomResolver`, pero queda expresamente fuera de esta pasada.

---

# CIERRE TEMPORAL - FA Puertas BIM / GeometryIndex 1

Fecha: 2026-08-31 America/Costa_Rica
Version/build conservado: `0.14.11 / 2026.08.31.3`
Estado: **CIERRE TEMPORAL CON LIMITACION CONOCIDA**.

La validacion manual del usuario sobre `FA_Geom1_Downstream` no acepto la posicion visual de GeometryIndex 1. Esto prevalece sobre la validacion MCP/captura previa: el caso **no se considera corregido**.

Se detiene deliberadamente la cadena de nuevas heuristicas. El build `.3` se conserva como baseline tecnico porque las pruebas focales y E2E aprobaron y no se observaron regresiones en los casos que funcionan. La excepcion de GeometryIndex 1 queda documentada como deuda tecnica localizada, no como bloqueo del Workbench.

Decision de arquitectura para el futuro: separar resolucion automatica segura de excepciones persistentes (`AUTO_OK`, `AUTO_AMBIGUOUS`, `MANUAL_OVERRIDE`) antes de intentar nuevas correcciones geometricas globales. No agregar otra tolerancia/score/caso especial al resolvedor solo por esta puerta.

## Cierre tecnico ejecutado

Se verifico en FreeCAD real 1.1.3 revision 20260725 que la sesion carga desde la
ruta DEV esperada, con `0.14.11 / 2026.08.31.3` y `FA_CreateDoorsBIM` registrado.
No se modificaron `opening_utils.py`, `door_corner_utils.py`, `constants.py` ni el
algoritmo de puertas durante este cierre.

Resultados finales:

- compilacion en memoria de los modulos relevantes: aprobada;
- pruebas focales: **63/63**;
- smoke MCP: una puerta BIM de 900 mm, host nativo correcto, subvolumen positivo
  y corte real de `283500000 mm3`;
- el E2E grande de nueve puertas excedio 90 s en esta corrida, por lo que no se
  presenta como una nueva aprobacion; se mantienen las validaciones E2E previas;
- GeometryIndex 1 queda explicitamente **no resuelto** y sujeto a revision/manual;
- se cerraron solo el documento temporal `FA_Geom1_Downstream` y el documento
  sintetico del smoke;
- se eliminaron un `FCStd`, dos `FCBak` y una captura PNG, todos con prefijo
  `FA_Geom1_Downstream` dentro del directorio temporal del sistema;
- el original quedo como unico documento abierto y permanecio identico antes y
  despues: 157 objetos, guardado, `isTouched()==False`;
- se conservaron todos los respaldos del Workbench.

La huella SHA-256 de cierre fue
`548E6D3D03A0B570B926D4E65ABA33A573AC320BEBC143B189449E554A3AE034`
para `opening_utils.py` y
`256EAD081EA7637AEFDE7706FAE60C1AA41080CA7FA09242A521855B336444FE`
para `door_corner_utils.py`.

---

# RESULTADO CODEX - GeometryIndex 1 downstream - Base ArchWindow

Fecha: 2026-08-31 America/Costa_Rica
FreeCAD probado: 1.1.3 revision 20260725
Workbench candidato: FacilArquitecturaWB 0.14.11 / build 2026.08.31.3
Estado: IMPLEMENTADO / VERIFICADO MCP / VERIFICADO VISUAL / PRUEBA MANUAL PENDIENTE

## Causa raiz capa por capa

Se recrearon las diez puertas en `FA_Geom1_Downstream`, copia exacta del documento
1416. `door_corner_utils.py` no se modifico.

| Capa | GeometryIndex 1 | GeometryIndex 6 |
|---|---|---|
| Sketch | `0..663.850602`, bisagra CAD `t=0` | ancho `629.668593`, bisagra CAD `t=53.440599` despues del snap |
| `FA_Projected` | `0..663.850602`, correcto | `0..629.668593`, correcto |
| Base `Wire0` anterior | `0..663.850602` | `0..629.668593` |
| Base `Wire1`/hoja anterior | `50..613.850602` | `50..579.668593` |
| Shape de hoja anterior | bisagra `t=50`, largo `563.850602` | bisagra `t=50`, a `3.440599 mm` de la bisagra CAD |
| Corte anterior | `0..663.850602` | `0..629.668593` |

La primera divergencia real era el Base del preset nativo. `Simple door` interpreta
el ancho entregado como `Wire0` del marco exterior, pero `WindowParts` crea la hoja
desde `Wire1`, retranqueada 50 mm por `Frame2` y `Frame3`. Por eso el log BOUNDED y
`FA_Projected` eran correctos mientras la hoja visible seguia desplazada/acortada.

## Correccion limitada a esa capa

`opening_utils.py` adapta solo puertas con `FA_CornerStatus=BOUNDED`:

- desplaza el origen exterior hacia atras por el margen `Frame2` real del preset;
- aumenta solo la restriccion `Width` del Sketch Base en `Frame2 + Frame3`;
- conserva `Window.Width`, `FA_Width_mm` y `FA_Projected*` como ancho/segmento de
  hoja autoritativo;
- conserva Host, bisagra, `Mode1/Mode2`, Tabla de Puertas y el preset ArchWindow.

Resultado GeometryIndex 1:

- hoja/Wire1: `0..663.850602 mm`, coincidente con Sketch y arco CAD;
- marco exterior: `-50..713.850602 mm`, ancho `763.850602 mm`;
- caras laterales: `-56.341660` y `773.658340 mm`, ambas fuera del marco;
- corte: `-50..713.850602 mm`, volumen `240612939.631 mm3`;
- interseccion residual Wall/subvolumen: `0 mm3`;
- `START/RIGHT/Mode2`, `Hosts=[Wall]`.

GeometryIndex 6 no cambio: `SNAPPED`, `START/LEFT/Mode1`, ancho
`629.668593 mm`, corte `198345606.696 mm3`. Los indices 8, 3 y 9 conservaron
`NO_FIT`/`JAMB_ONLY` y sus posiciones anteriores.

## Validacion

- captura superior MCP antes/despues y despues de reabrir: el marco ocupa el
  buque y la hoja/bisagra coinciden con el segmento autoritativo;
- copia real: 10 puertas, cero rechazos, reejecucion 10/10 sin duplicados;
- Undo/Redo y guardar/cerrar/reabrir: aprobados;
- prueba pura focal: 63/63;
- E2E de esquinas ampliado con caso BOUNDED realista: 9 puertas, aprobado;
- Tabla de Puertas, puerta doble, puertas/ventanas compartidas y Tabla de
  Ventanas: aprobadas en FreeCAD real.

La suite global ejecuto 232 pruebas: permanece la falla ajena de rotulos de
recintos y dos errores de carga por falta de `pytest` en Python 3.9 para techo y
distribucion de ejes.

La copia corregida permanece abierta y guardada en el directorio temporal para la
prueba manual. El original permanece abierto con 137 objetos y su estado previo
`isTouched()==True`; no fue guardado ni modificado. Respaldo:
`Respaldos_2026-08-31_FA_puertas_base_archwindow_pre_build3/`.

---

# RESULTADO CODEX - GeometryIndex 1 vs 6 - vano acotado BOUNDED

Fecha: 2026-08-31 America/Costa_Rica
FreeCAD probado: 1.1.3 revision 20260725
Workbench final: FacilArquitecturaWB 0.14.11 / build 2026.08.31.2
Estado: IMPLEMENTADO / VALIDADO MEDIANTE MCP / TAREA CERRADA

## Diferencia geometrica demostrada antes de editar

La prueba se hizo sobre una copia exacta creada con `Document.saveCopy()` del
documento real `1416 Levantamiento 250424 Depurado`. El original no se guardo ni
se modifico. Tanto el indice 1 como el 6 coinciden con el centro y radio del arco
CAD original antes del snap; por tanto, el simbolo CAD no permite elegir una
jamba distinta de la indicada por el Sketch.

| Dato | GeometryIndex 1, incorrecto | GeometryIndex 6, correcto |
|---|---:|---:|
| Sketch | `(3919.003,9174.346) -> (3255.152,9174.346)` | `(3435.827,13583.441) -> (3435.827,14213.109)` |
| Proyeccion transversal previa | `y=9175`, ancho `663.851` | `x=3431.344`, ancho `629.669` |
| Candidatas de cara | dos, START y END, en lados opuestos | una, START |
| Luz entre caras opuestas | `830.000 mm` | no aplica |
| Holgura del eje dentro de la luz | `166.149 mm` | no aplica |
| Shift elegido por la ruta anterior | `-56.342 mm` a START | `-53.441 mm` a START |
| Resultado anterior | puerta trasladada fuera de su buque dibujado | ajuste correcto a una jamba unica |

La primera diferencia reusable es topologica: el indice 1 ya queda completamente
acotado por dos caras externas opuestas y cabe con holgura positiva. Elegir la cara
mas cercana desplaza silenciosamente un dato autoritativo y no resuelve ninguna
ambiguedad. El indice 6 tiene una sola cara externa candidata; su snap es unico.
En los diez ejes reales, el indice 1 es el unico caso con esta condicion. El indice
8 tambien tiene dos caras, pero la contraria cae dentro del tramo y continua siendo
`NO_FIT` antes de evaluar `BOUNDED`.

## A/B controlado

Variante A, codigo anterior: el indice 1 termino en
`(3975.344,9175) -> (3311.494,9175)`, `SNAPPED`, y la vista superior mostro la
puerta desplazada respecto al buque. Variante B, neutralizando exclusivamente el
snap del indice 1 en memoria y restaurando obligatoriamente el resolvedor: se
conservaron `(3919.003,9175) -> (3255.152,9175)` y la puerta quedo dentro del
buque. El indice 6 fue identico en A y B. Ancho, `Hosts=[Wall]` y volumen de corte
no cambiaron.

## Correccion minima

`core/door_corner_utils.py` devuelve `BOUNDED` sin traslacion cuando dos caras
externas opuestas contienen completamente el eje con holgura positiva. La regla
no usa indices, coordenadas ni una nueva tolerancia. Conserva como diagnostico la
mejor candidata y permite inferir bisagra/apertura.

`core/opening_utils.py` y `core/door_table_utils.py` separan ahora dos decisiones:
aplicar una traslacion y aplicar una orientacion resuelta. Por eso el indice 1
mantiene su posicion y conserva `START/RIGHT/OpensInward=True/Mode2`; el indice 6
continua `SNAPPED`, `START/LEFT/Mode1` y en contacto exacto con su jamba.

Resultado real de los diez ejes:

- indice 1: `BOUNDED`, sin shift, ancho `663.850602 mm`, corte
  `209112939.631 mm3`, Host `Wall`;
- indice 6: `SNAPPED`, shift `-53.440599 mm`, ancho `629.668593 mm`, corte
  `198345606.696 mm3`, Host `Wall`;
- indice 8: `NO_FIT`, sin desplazamiento, ancho `903.035889 mm`;
- indice 3: `JAMB_ONLY` aplicado y seguro;
- indice 9: `JAMB_ONLY` sin desplazamiento, como la regresion anterior;
- total: 10 puertas, cero rechazos, 6 snaps aplicados, 6 `JAMB_ONLY`, 1 `NO_FIT`.

## Pruebas

- prueba pura nueva con las coordenadas reales del indice 1: aprobada;
- suite focal (`door_corner_utils`, `opening_utils`, `element_data_core`,
  `freecad_compat`): 62/62;
- copia real: reejecucion reemplazo 10/10 sin duplicar; Undo/Redo y guardar,
  cerrar y reabrir conservaron estados, Hosts y cortes;
- `freecad_door_corner_snap_end_to_end.py`: aprobado;
- `freecad_door_table_end_to_end.py`: aprobado;
- `freecad_double_door_bim_smoke.py`: aprobado;
- `freecad_openings_end_to_end.py` y `freecad_window_table_end_to_end.py`:
  aprobados; ventanas, Hosts, idempotencia y persistencia sin regresion.

La suite global ejecuto 231 pruebas: la regresion nueva aprobo. Permanecen fuera
de alcance la falla conocida de `test_room_label_utils` y dos errores de carga por
falta de `pytest` en el Python 3.9 del sistema (`axis_distribution` y
`roof_system_core`). No afectan los archivos modificados en esta tarea.

Respaldo previo:
`FacilArquitecturaWB/Respaldos_2026-08-31_FA_puertas_bounded_pre_build2/`.
No hubo commit ni push. Al inicio, el original ya tenia 137 objetos y estado
`isTouched()==True`; ese estado previo se preservo y nunca se guardo.

---

# RESULTADO CODEX - GeometryIndex 9 y aviso por build

Fecha: 2026-08-30 America/Costa_Rica
FreeCAD probado: 1.1.3 revision 20260725
Workbench final: FacilArquitecturaWB 0.14.8 / build 2026.08.30.2
Estado: IMPLEMENTADO / VALIDADO MEDIANTE MCP / TAREA CERRADA

## A/B obligatorio antes de editar

Se uso una copia exacta del documento real `1416 Levantamiento 250424 Depurado`,
creada con `Document.saveCopy()`. Las dos variantes usaron el mismo Sketch, el
mismo `Wall`, la misma geometria 9 y `create_openings_from_centerlines()`:

| Variante | `FA_ProjectedFirst` | `FA_ProjectedSecond` | Resultado |
|---|---|---|---|
| A, snap actual | `(6590.344424, 11920.000000)` | `(6590.344424, 11100.790039)` | `JAMB_ONLY`, desplazamiento `64.386719 mm` |
| B, resolver neutralizado en memoria | `(6590.344424, 11984.386719)` | `(6590.344424, 11165.176758)` | posicion pre-snap conservada |

El ancho, Host y subvolumen fueron identicos en A y B. La inspeccion visual de B
mostro nuevamente la coincidencia del extremo inferior con el simbolo CAD. Por
tanto, la afirmacion anterior de que bastaba corregir el Sketch queda sustituida:
la nueva capa de snap si introducia la regresion de posicion.

La primera diferencia geometrica fue precisa: el indice 9 era el unico de los seis
`JAMB_ONLY` cuya cara candidata quedaba dentro del propio segmento de puerta
(`target_axis=64.386719 mm`, entre 0 y `819.209961 mm`). En los otros cinco casos
la cara quedaba fuera del tramo y el ajuste seguia representando una jamba exterior.

## Correccion minima

`core/door_corner_utils.py` conserva la posicion proyectada cuando el giro no esta
resuelto y la cara candidata de `JAMB_ONLY` cae estrictamente dentro del tramo. El
plan mantiene estado, candidato y distancia como diagnostico, pero devuelve
`applied=False`; no se especializa por indice ni se cambia `opening_utils.py`.

Regresiones conservadas en el levantamiento real:

- indice 9: `JAMB_ONLY`, sin snap, endpoints pre-snap y ancho `819.209961 mm`;
- indice 6, Servicio Sanitario: `SNAPPED`, `START/LEFT`, ancho `629.668593 mm`;
- indice 8: `NO_FIT`, ancho `903.035889 mm`, sin desplazamiento;
- indice 3: `JAMB_ONLY` aplicado, primera jamba `x=6665.344424`;
- las 10 puertas conservaron `Hosts=[Wall]` y cortes positivos.

Reejecucion reemplazo 10/10 sin duplicar. Undo/Redo, guardar y reabrir conservaron
los resultados. La corrida final con los modulos recargados del build `.2` produjo
10 puertas, 6 estados `JAMB_ONLY`, 1 `NO_FIT`, 7 snaps aplicados y cero rechazos.

## Aviso de actualizacion

`InitGui.py` conserva `LastNotifiedVersion` y agrega `LastNotifiedBuild`. La identidad
notificada es ahora `VERSION + BUILD_ID`. Una preferencia heredada que solo contiene
version muestra un aviso de migracion una vez y luego queda silenciosa.

Prueba Qt real mediante MCP:

- estado anterior: `0.14.8 / 2026.08.30.1`;
- estado actual: `0.14.8 / 2026.08.30.2`;
- primera activacion: un `QMessageBox` con version/build anterior y actual;
- segunda activacion: cero dialogos;
- parametros finales: `0.14.8 / 2026.08.30.2`.

## Pruebas y alcance

- `py_compile` y `compileall`: aprobados;
- pruebas puras focales: 61/61;
- `freecad_door_corner_snap_end_to_end.py`: aprobado, incluidos Mode1/Mode2,
  `NO_FIT`, `JAMB_ONLY`, corte, reejecucion, Undo/Redo y reapertura;
- `freecad_door_table_end_to_end.py`: aprobado, CREATE/KEEP/REPLACE y persistencia;
- A/B y regresion final sobre copia real 1416: aprobados.

La suite global inicio 229 pruebas: 227 aprobaron; persisten fuera de alcance una
falla de `test_room_label_utils` y la falta de `pytest` en el Python 3.9 usado para
importar `test_roof_system_core`. Ninguna pertenece a los archivos de esta tarea.

Respaldo previo:
`FacilArquitecturaWB/Respaldos_2026-08-30_FA_geom9_build_notice_pre_build2/`.
No hubo commit ni push. El documento original termino como unico documento abierto,
157 objetos, `isSaved()==True` e `isTouched()==False`.

---

# RESULTADO CODEX - FA Puertas BIM - fase 3 excepciones reales

Fecha: 2026-08-30 America/Costa_Rica
FreeCAD probado: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.8 / build 2026.08.30.1
Estado: DIAGNOSTICO CERRADO / VALIDADO MEDIANTE MCP / SIN CAMBIO DE CODIGO

## Entorno y alcance

Se confirmaron la version/build y los modulos cargados desde la ruta DEV canonica.
El documento real `_1416_Levantamiento_250424_Depurado` se inspecciono primero en
lectura. Las pruebas con escritura se hicieron sobre una copia exacta creada con
`Document.saveCopy()`; la copia temporal se elimino al terminar.

No se modificaron `Mode1/Mode2`, `NO_FIT`, `JAMB_ONLY`, el ancho autoritativo del
Sketch ni ningun archivo Python. La version/build permanece sin cambios.

## Caso A - puerta desplazada respecto al buque dibujado

La candidata reproducible es `GeometryIndex=9`, objeto `Window009`. El problema
ya existe en el eje fuente y no es un doble desplazamiento BIM:

- Sketch: `(6593.255, 11984.387) -> (6593.255, 11165.177)`, ancho `819.210 mm`;
- simbolo CAD original mas cercano (`Link__U44_`): radio/ancho `696.235 mm`,
  bisagra en `(6591.659, 11860.910)` y extremo cerrado en
  `(6590.233, 11164.676)`;
- un extremo del Sketch coincide con el simbolo a aproximadamente `3.1 mm`, pero
  el otro se prolonga `123.5 mm`; el eje es `122.975 mm` mayor que la hoja CAD;
- despues de proyeccion y `JAMB_ONLY`, las jambas quedan en
  `(6590.344, 11920.000)` y `(6590.344, 11100.790)` sin cambiar el ancho;
- `Placement` del objeto es cero; la Base esta en `(6515.344, 11920.000)` y el
  subvolumen de corte ocupa exactamente `y=11100.790..11920.000`;
- marco, Base y corte coinciden entre si; su interseccion con el material de los
  perfiles originales de muro es `0 mm3`. `Hosts=[Wall]`, `FA_HostWall=Wall` y
  `MoveWithHost=True` no produjeron una segunda traslacion.

Conclusion: la herramienta conserva correctamente la geometria autoritativa del
Sketch. Corregirla automaticamente deformaria el dato de entrada. Para ajustar
esta puerta debe corregirse `GeometryIndex=9` o regenerarse el eje desde el objeto
CAD correcto; no corresponde cambiar el algoritmo general.

## Caso B - puerta oblicua que abre hacia el exterior

El caso es `GeometryIndex=7`, `Window007`:

- eje fuente: `(5940.547, 18144.723) -> (5125.458, 18069.298)`, ancho
  `818.569 mm`;
- eje final: `(6018.344, 18135.335) -> (5203.414, 18058.241)`; la jamba START se
  alinea con `JAMB_ONLY` y `FA_CornerShift_mm=-76.568`;
- el arco CAD original abre hacia `(-0.091, +0.996)`;
- el Sketch no contiene metadato de bisagra/interior y no existe
  `Spreadsheet_Puertas`; por eso quedan `HingeEndpoint=AUTO`,
  `OpeningSide=AUTO`, sin `OpensInward`, y el preset conserva su `Mode1` nativo;
- la hoja BIM medida abre hacia `(-0.027, -1.000)`, opuesta al arco CAD
  (`dot=-0.993`). No es una inversion nueva de la convencion Mode1/Mode2: falta
  autoridad de datos para elegir el cuadrante.

La correccion segura ya disponible es Tabla de Puertas. En una copia exacta se
aplico solo a esa fila `HingeEndpoint=START`, `OpeningSide=RIGHT` y
`OpensInward=True`. El dry-run produjo `MATCH + REPLACE`; la puerta paso a
`Mode2` y su vector real `(-0.194, +0.981)` se alineo con el arco CAD
(`dot=0.9946`). Host, ancho, posicion, estado `JAMB_ONLY` y subvolumen de corte
`859497628.35 mm3` se conservaron.

No se automatizo la lectura de arcos DXF en `FA Puertas BIM`: el Sketch actual
solo transmite posicion, orientacion y ancho. Conectar nuevamente la seleccion
CAD con metadatos de giro seria una mejora separada, no una correccion local de
esta fase.

## Caso visualmente mayor - NO_FIT confirmado

`GeometryIndex=8`, `Window008`, es un `NO_FIT` correcto:

- ancho del Sketch: `903.035889 mm`;
- luz util entre caras: `830.000000 mm`;
- exceso/penetracion: `73.035889 mm`;
- `FA_CornerSnapped=False`; el eje no se recorto ni se deformo.

La interseccion con el muro original corresponde precisamente a ese exceso. No se
modifico el algoritmo; la geometria fuente requiere revision si se desea que quepa.

## Regresion positiva - Servicio Sanitario

`GeometryIndex=6`, `Window006`, permanecio exactamente igual antes/despues de la
prueba de tabla: `START/LEFT`, `Mode1`, `SNAPPED`, Host `Wall`, ancho
`629.668593 mm`, bisagra `(3431.344, 13530.000)` y subvolumen de corte
`661152022.32 mm3`. Su hoja sigue orientada hacia `-X`, de acuerdo con el arco CAD
original y el recinto sanitario.

## Pruebas

- MCP real, copia exacta: 10 puertas antes/despues; correccion exclusiva del
  indice 7; reejecucion `KEEP` sin duplicados.
- Undo restauro `Mode1/AUTO/AUTO`; Redo restauro `Mode2/START/RIGHT`.
- Guardar, cerrar y reabrir la copia conservo 10 puertas, Host y cortes.
- Pruebas puras focales: `60/60` en `test_door_corner_utils`,
  `test_opening_utils`, `test_element_data_core` y `test_freecad_compat`.
- Documento original al finalizar: unico documento abierto, 157 objetos,
  archivo original asociado, `isSaved()==True` e `isTouched()==False`.

Pendiente funcional, no bloqueo: editar el eje 9 si el usuario desea hacerlo
coincidir con el simbolo CAD y registrar `START/RIGHT/True` para el eje 7 en una
Tabla de Puertas del documento productivo. No hubo commit ni push.

---

# RESULTADO CODEX - FA Puertas BIM - correccion focalizada fase 2

Fecha: 2026-08-30 America/Costa_Rica
FreeCAD probado: 1.1.3 revision 20260725
Workbench: FacilArquitecturaWB 0.14.8 / build 2026.08.30.1
Estado: IMPLEMENTADO / VALIDADO MEDIANTE MCP / TAREA COMPLETADA

## Cambio minimo

- `door_corner_utils.py` separa la cara para alinear la jamba de la evidencia
  necesaria para inferir giro. Un cruce puede producir `JAMB_ONLY` sin inventar
  bisagra ni cuadrante.
- El plan verifica ambas jambas con tolerancia de ajuste de 1 mm. Cuando el ancho
  no cabe entre caras devuelve `NO_FIT`, conserva posicion/ancho del Sketch y
  reporta luz util y penetracion.
- La direccion fisica de la hoja se traduce a `Mode1/Mode2` usando el eje real
  desde la bisagra hasta la otra jamba. El adaptador modifica solo el token del
  componente abatible de `Simple door` o `Glass door`; no reconstruye presets.
- Tabla de Puertas conserva sus valores explicitos, puede aportar giro cuando la
  geometria solo resuelve jamba y compara el modo nativo para idempotencia.
- Nuevas propiedades de trazabilidad: `FA_CornerStatus`, `FA_CornerNoFit`,
  `FA_CornerSwingResolved`, `FA_JambEndpoint`, `FA_NativeOpeningMode`,
  `FA_ProjectedFirst/Second`, `FA_AvailableWidth_mm` y penetracion asociada.

## Evidencia MCP controlada

Matriz de ocho puertas sobre un `Arch Wall` multisegmento:

- `Mode1`: dos sentidos START/END con la misma bisagra fisica y hoja real `+Y`;
- `Mode2`: dos sentidos START/END con la misma bisagra fisica y hoja real `+Y`;
- `NO_FIT`: 903.036 mm frente a 830.000 mm, penetracion 73.036 mm;
- cruce: jamba alineada, `HingeEndpoint=AUTO`, `OpeningSide=AUTO`;
- puerta sin lateral: sin movimiento;
- dos extremos equivalentes: ambiguo, sin movimiento.

Los ocho objetos conservaron Host y subvolumen de corte. Reejecucion reemplazo
8/8 sin duplicar; Undo/Redo y guardar/cerrar/reabrir aprobaron.

## Comparacion real 1416 sobre copia segura

| GeometryIndex | Antes | Despues fase 2 |
|---:|---|---|
| 6 | `LEFT/Mode1`, hoja hacia pared | Sin regresion: `LEFT/Mode1`, vector real `(-0.971, 0.239)` |
| 1 | `RIGHT/Mode1`, hoja real hacia `-Y` | `RIGHT/Mode2`, hoja real hacia `+Y` `( -0.153, 0.988 )` |
| 8 | snap START invalido | `NO_FIT`; ancho 903.036, luz 830.000, penetracion 73.036; sin snap |
| 3 | sin cara ni giro resueltos | `JAMB_ONLY`; primera jamba en `x=6665.344`; giro permanece `AUTO` |

La copia produjo 10 puertas, 10 hosts `Wall`, cortes positivos, reejecucion 10/10,
Undo/Redo y reapertura. El documento original termino como unico documento abierto,
157 objetos, archivo asociado y `isTouched() == False`.

## Pruebas

- MCP: `freecad_door_corner_snap_end_to_end.py`,
  `freecad_door_table_end_to_end.py`, `freecad_change_door_type_end_to_end.py`,
  `freecad_double_door_bim_smoke.py`, `freecad_window_table_end_to_end.py`,
  `freecad_openings_end_to_end.py` y `freecad_openings_only_end_to_end.py`: OK.
- Tabla de Puertas verifico valores explicitos `END/RIGHT` con hoja real y cambio
  posterior a `LEFT`; puerta doble con `HingeEndpoint=BOTH` y 13 solidos: OK.
- Pruebas puras focales: 63/63. Suite global: 225/226; unica falla preexistente y
  ajena en `test_room_label_utils...collects_structured_labels...`. `compileall`: OK.

## Archivos de esta fase

- `core/door_corner_utils.py`, `core/opening_utils.py`, `core/door_table_utils.py`;
- pruebas focales y E2E de esquina/tabla;
- `core/constants.py`, `package.xml`, README y documentacion de continuidad.

Respaldo previo: `Respaldos_2026-08-30_FA_puertas_fase2_pre_build`. No se
modificaron ElectricCR, MEPWorkbenchCR ni GameEngineExportWB. No hubo commit/push.

---

# RESULTADO CODEX - FA Puertas BIM - diagnostico MCP limitado

Fecha: 2026-08-30 America/Costa_Rica
FreeCAD probado: 1.1.3 revision 20260725
Workbench cargado: FacilArquitecturaWB 0.14.8 / build 2026.08.29.1
Estado: DIAGNOSTICO COMPLETADO / SIN CAMBIOS DE CODIGO NI BUILD

## Entorno real

Antes de medir geometria se confirmo mediante MCP que `FacilArquitecturaWB`,
`InitGui.py`, `opening_utils.py`, `door_corner_utils.py` y
`cmd_create_doors_bim.py` proceden de la copia DEV sincronizada
`Macros-de-Freecad/FacilArquitecturaWB`. Los comandos estable y alias estan
registrados. No hay evidencia de modulo sombreado ni cache antiguo.

Documento real: `1416 Levantamiento 250424 Depurado`, 157 objetos, archivo asociado
y `isTouched() == False`. La muestra se leyo sobre las puertas existentes; no se
volvio a ejecutar el comando y no se guardo el documento.

## Muestra MCP

Todas las coordenadas y distancias estan en milimetros. `START/END` se refiere al
sentido real de la geometria del `Sketch_Centros_Puertas`. La direccion de hoja a
90 grados se midio sobre el solido `Door` ya generado, no se dedujo solo de
metadatos.

| Geom. / objeto | Host y encuentro | Jambas fisicas START -> END | Candidatos y cara real | Snap / bisagra | Normal; apertura declarada | Hoja real a 90 | Resultado y causa |
|---|---|---|---|---|---|---|---|
| 6 / `Window006` | `Wall`, seg. 9; T, pared lateral seg. 10 termina en el host | `(3431.344,13530.000)` -> `(3431.344,14159.669)` | cara `y=13530.000`; separacion previa START `53.441` | snap `-53.441`; bisagra `START` | `Normal=-X`; `LEFT`; `OpensInward=True` | `-X`, paralela y hacia la pared lateral | **Correcta.** Un solo candidato, no hay conflicto en la otra jamba y `LEFT` coincide con el `Mode1` nativo. |
| 1 / `Window001` | `Wall`, seg. 1; T local entre laterales seg. 15 y 8 | `(3975.344,9175.000)` -> `(3311.494,9175.000)` | elegida cara derecha `x=3975.344`, gap `56.342`; cara izquierda `x=3145.344`, holgura final `166.149` | snap `-56.342`; bisagra `START` | `Normal=+Y`; `RIGHT`; `OpensInward=True` | `-Y`; la pared elegida se extiende hacia `+Y` | **Incorrecta en cuadrante.** Jamba y bisagra son correctas, pero la hoja abre al lado opuesto. |
| 8 / `Window008` | `Wall`, seg. 3; tramo entre dos encuentros T, laterales seg. 8 y 19 | `(3145.344,7544.000)` -> `(4048.380,7544.000)` | cara izquierda `x=3145.344`, gap `1.499`; cara derecha `x=3975.344`, gap inicial `74.535` | elige START; bisagra `START` | `Normal=+Y`; `LEFT`; `OpensInward=True` | `+Y`, coherente con la pared izquierda | **Incorrecta por ajuste imposible.** Ancho `903.036` mayor que luz entre caras `830.000`; la jamba END queda `73.036` dentro de la pared derecha. |
| 3 / `Window003` | `Wall`, seg. 4; cruce con pared seg. 17, ambas atraviesan la interseccion | `(6719.952,11995.000)` -> `(7445.872,11995.000)` | cara `x=6665.344`; START queda a `54.607` | sin snap; bisagra `AUTO` | `Normal=(0,0,0)`; `AUTO`; sin `OpensInward` | `+Y`, resultado por defecto | **Incorrecta/no resuelta.** El cruce no ofrece una extension lateral unica; el plan descarta todo el candidato, incluida la alineacion de jamba. |

## Causa raiz demostrada

Hay tres limites independientes; no corresponde resolverlos con un refactor unico:

1. **La semantica FA no gobierna el cuadrante nativo.** Todas las puertas simples
   conservan `WindowParts = ... Edge8,Mode1`. `FA_OpeningSide`, `FA_OpensInward` y
   `Normal` no cambian `Mode1` a `Mode2`. El codigo nativo de `ArchWindow.py` rota
   la hoja con el signo de `Mode1/Mode2`; `Normal` se usa para la normal del
   elemento/extrusion. Por eso el caso `LEFT` funciona y el caso `RIGHT` abre al
   lado opuesto aunque sus metadatos digan lo contrario.
2. **El score elige una esquina sin validar la otra jamba.** GeometryIndex 8 tiene
   dos candidatos no equivalentes por score, pero el ancho no cabe entre sus caras.
   El plan aplica el mas cercano y deja el extremo opuesto dentro de la pared.
3. **En T inversa/cruce se mezcla posicion con sentido de apertura.** Cuando la
   pared perpendicular atraviesa ambos lados, `_side_extension_direction()` la
   descarta. Es correcto no inferir cuadrante, pero tambien se pierde una cara real
   util para alinear la jamba.

## Correccion minima recomendada para la segunda fase

Primero, traducir explicitamente el cuadrante fisico deseado al modo nativo del
preset: conservar `Mode1` cuando produce la direccion pedida y usar `Mode2` cuando
se requiere el giro inverso. No intentar controlarlo mediante `Normal`. Esta es la
pieza minima que explica la diferencia correcta/incorrecta entre GeometryIndex 6 y
1.

Como guardas geometricas separadas:

- antes de aplicar snap, comprobar ambas jambas contra todas las caras laterales y
  rechazar/reportar `NO_FIT` cuando el ancho excede la luz disponible;
- separar `jamb_face_candidate` de `swing_direction_candidate`: en un T inverso o
  cruce puede existir una cara segura para posicion, mientras bisagra/cuadrante debe
  quedar `AUTO` o provenir de recinto/tabla/usuario.

Prueba MCP recomendada: una matriz controlada con el mismo vano dibujado START->END
y END->START, lados fisicos LEFT/RIGHT, un caso `NO_FIT` y un cruce. Debe comprobar
coordenada de ambas jambas, `WindowParts Mode1/Mode2`, vector real de la hoja a 90,
host/corte e idempotencia. Riesgo **medio**: invertir globalmente `Mode1` romperia
el caso correcto; la traduccion debe depender de direccion fisica, no solo del texto
START/END.

## Criterio de parada

Se alcanzo evidencia suficiente para explicar una puerta correcta y tres fallos
distintos. Conforme al limite de esta fase, no se modifico el algoritmo, no se
incremento version/build y no se ejecutaron iteraciones de correccion.

---

# RESULTADO CODEX - FA Puertas BIM + snap a pared lateral

Fecha/hora: 2026-08-29 America/Costa_Rica
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD probado: 1.1.3 revision 20260725
Version/build: 0.14.8 / 2026.08.29.1
Estado: IMPLEMENTADO / PROBADO / VERIFICADO MCP / TAREA COMPLETADA

## Diagnostico previo a la modificacion

- FreeCAD cargaba el Workbench desde la ruta DEV canonica. La copia `Mod` es un
  junction a esa misma ruta, no otra instalacion.
- El documento real `1416 Levantamiento 250424 Depurado` tenia 137 objetos, no
  estaba modificado y contenia 10 ejes de puerta y un `Arch Wall` basado en una red
  de 20 segmentos.
- El probe inicial obtuvo cero candidatos porque `resolve_door_corner_snap()`
  excluia el objeto Wall completo. Al excluir solo el segmento anfitrion aparecieron
  tres resultados unicos: indices 1, 6 y 8.
- FreeCAD 1.1.3 no expone `FreeCADGui.removeCommand`. Tras una recarga, el ID
  `FA_CreateDoorsFromSketch` podia conservar la instancia Python de 0.14.7 aunque
  los modulos actuales fueran 0.14.8/build 4. Una prueba con sentinel confirmo que
  el boton llamaba ese callback huerfano.

## Cambio minimo

- `core/opening_utils.py`: el tramo anfitrion se identifica con
  `reference_segment_index`; los otros tramos del mismo Wall se presentan como
  registros virtuales a `plan_door_corner_snap()`. No se crean objetos ni otra
  logica geometrica paralela.
- `FA_CornerWall` guarda el nombre estable como `PropertyString`. Es trazabilidad,
  no un segundo enlace a la pared que participe en `MoveWithHost`.
- `core/reloadable_command.py` y `cmd_create_doors_bim.py`: el ID estable delega a
  la clase del modulo vigente en cada activacion.
- Los lectores de Tabla de Puertas y Tabla de Ventanas eliminan el apostrofo literal
  que `Spreadsheet::Sheet.getContents()` devuelve antes de textos.
- Las regresiones BIM antiguas se alinearon con el contrato 0.14.5: objetos alojados
  no se duplican en `Level.Group`; mantienen `FA_TargetLevel`.

## Resultado MCP real

- Boton real sobre copia segura del documento: 10 puertas, tres snaps en indices
  `[1, 6, 8]`, anchos exactos, diez `Hosts=[Wall]` y diez cortes positivos. El
  documento original permanecio intacto.
- Modelo controlado: jamba en la cara x=50 mm, ancho 900 mm, bisagra `START`, giro
  hacia la pared y hoja a 90 grados aproximadamente paralela. Puerta alejada sin
  desplazamiento; candidato doble ambiguo reportado sin desplazamiento.
- Reejecucion: 3 puertas reemplazadas sin duplicados. Undo/Redo y guardar/reabrir:
  aprobados.
- Puerta doble: snap del marco con `HingeEndpoint=BOTH`, 13 solidos y corte real.
- Barra `FA Aberturas BIM`: una accion `FA Puertas BIM` y una `FA Tabla de puertas`;
  los IDs estable y alias estan registrados.

Corrida MCP consolidada, 7/7:

1. `freecad_door_corner_snap_end_to_end.py`;
2. `freecad_door_table_end_to_end.py`;
3. `freecad_window_table_end_to_end.py`;
4. `freecad_openings_end_to_end.py`;
5. `freecad_openings_only_end_to_end.py`;
6. `freecad_change_door_type_end_to_end.py`;
7. `freecad_double_door_bim_smoke.py`.

Pruebas puras: 220/221. La unica falla es preexistente y ajena:
`test_room_label_utils.RoomLabelUtilsTests.test_collects_structured_labels_and_consolidates_duplicates`.
`compileall FacilArquitecturaWB` aprobo.

Estado final de FreeCAD: solamente el documento original abierto, 137 objetos,
archivo asociado sin cambiar y `isTouched() == False`.

Durante la recarga final, ejecutar el loader de hot restart desde la llamada MCP
cerro inesperadamente FreeCAD. Se inicio nuevamente FreeCAD 1.1.3 y el dialogo
nativo informo `Recuperado con exito`; restauro exactamente el documento de 137
objetos sin cambios. En esa sesion limpia el Workbench se cargo normalmente desde
la ruta DEV, confirmo build `2026.08.29.1`, una instancia
`ReloadableCommandProxy` para `FA_CreateDoorsFromSketch` y una sola barra de
aberturas. FreeCAD queda abierto.

## Pendiente separado

`FA_HostWall` historicamente es otro `PropertyLink` ademas de `Hosts`; en FreeCAD
1.1.3 puede duplicar el desplazamiento de una abertura cuando se mueve el host. Este
trabajo elimino solamente el enlace nuevo de esquina que habria agregado un tercer
desplazamiento. Migrar la trazabilidad historica de todas las aberturas requiere una
tarea independiente.

---

# RESULTADO GPT - ElementDataCore + Tabla de Puertas

Fecha/hora: 2026-08-28 America/Costa_Rica
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD objetivo: 1.1.3
Version candidata: 0.14.8 / build 2026.08.28.4
Estado: IMPLEMENTACION DIRECTA GPT / PRUEBAS PURAS APROBADAS / PENDIENTE FREECAD REAL

## Implementacion candidata

- `ElementDataCore` soporta categoria `doors` y conserva contrato JSON-compatible.
- nueva `Spreadsheet_Puertas` con tipo, bisagra, lado/sentido de apertura, altura y trazabilidad; geometria de ancho/posicion/orientacion permanece autoritativa en el Sketch destino.
- tipos nativos extensibles mediante presets instalados en FreeCAD y `TypeRef`; `DoorType` puede ser un nombre logico de usuario.
- puerta doble FA integrada mediante factory existente `architecture.door.double_leaf.glazed.europa`, sin crear un segundo objeto BIM.
- `FA_DoorTypeOverrides` historico sigue vigente para `FA Puertas BIM`, pero la tabla marca su preset como autoritativo al aplicar.
- `FA_Project/06_Tables` organiza `Spreadsheet_Puertas` y `Spreadsheet_Ventanas`.
- nuevo comando unico `FA_DoorTable` en `FA Aberturas BIM`.
- proteccion de puertas manuales y estados `MATCH/CAMBIO/NO_MATCH/AMBIGUO`; dry-run obligatorio antes de confirmar GUI.

## Validacion ejecutada fuera de FreeCAD

- `py_compile`: todos los modulos nuevos/tocados de la tarea aprobados.
- pruebas puras focales: 29/29 aprobadas (`ElementDataCore` + `door_type_utils`).
- cubierto: serializacion, bisagra/apertura, dobles, alias de tipo, preset instalado, tipo desconocido rechazado, cambio de ancho, duplicidad/ambiguedad.
- se preparo `tests/freecad_door_table_end_to_end.py` para validar Simple door con nombre logico de usuario + puerta doble FA, hosts, cortes, KEEP/REPLACE, Undo/Redo y reapertura.

## Pendiente obligatorio

No se declara validado en FreeCAD/MCP desde este chat porque no hay una sesion MCP de FreeCAD expuesta. Ejecutar la prueba real en FreeCAD 1.1.3 antes de cerrar 0.14.8 y registrar cualquier ajuste de orientacion de simbolo/apertura que el entorno real demuestre necesario.

---

# RESULTADO CODEX - FA Cerrar buques de puertas y ventanas

Fecha/hora: 2026-08-28 America/Costa_Rica
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD objetivo y probado: 1.1.3 revision 20260725
Version/build: 0.14.7 / 2026.08.28.2
Estado: IMPLEMENTADO / PROBADO / VERIFICADO MCP / TAREA COMPLETADA

## Diagnostico real previo

El boton visible carga desde la ruta DEV canonica y llama a
`commands/cmd_create_closed_rooms.py` -> `create_closed_wall_sketches()` ->
`bridge_wall_gaps()`. No existe un segundo motor productivo. Se corrigio tambien
el registro para conservar el ID estable `FA_CloseWallSketch`; la barra
`FA Recintos y cielos` contiene esa unica accion de cierre.

El documento real `1416 Levantamiento 250424 Depurado` se inspecciono solo en
lectura. Datos:

- Sketch muro: 37 lineas, espesor 150 mm, Placement identidad;
- `Sketch_Centros_Ventanas`: 14 lineas;
- `Sketch_Centros_Puertas`: 10 lineas;
- `Sketch_Centros_Puerta Principal`: una linea;
- total: 25 geometrias de abertura.

Las ventanas reales son paralelas al eje del muro. Las puertas tambien siguen
su pared, pero varias quedan junto a esquina/T, con desplazamientos de pocos
milimetros. Dos casos forman cadenas consecutivas: ventana 7 + puerta 9 sobre
el eje vertical interior y ventana 9 + puerta 5 en la fachada horizontal.

La primera diferencia real fue el orden candidato-primero del algoritmo
anterior. `_wall_gap_candidate()` eliminaba antes de evaluar la abertura:

- ventana de 2809 mm y cadena ventana+puerta de 3153 mm, por superar el limite
  generico de 2500 mm;
- puertas que requieren extender un tramo hasta el interior de una pared de
  apoyo en una T/esquina;
- el modo `selection` podia luego asociar la abertura no usada a varios buques
  cercanos; una puerta real obtuvo 10 candidatos iniciales.

## Correccion

`core/room_utils.py` 0.9.0 conserva el motor existente y cambia el planificador:

1. analiza cada abertura antes de generar el cierre;
2. agrupa solo geometrias consecutivas, colineales y sobre el mismo eje;
3. usa los tramos de muro paralelos como autoridad de direccion/alineamiento;
4. permite que la longitud medida de la abertura justifique localmente un buque
   mayor al limite generico;
5. en esquina/T extiende solo el tramo colineal hasta la pared de apoyo, sin
   alterar esa pared;
6. deduplica candidatos fisicamente equivalentes y no aplica una eleccion
   ambigua;
7. conserva el matcher anterior como compatibilidad para ejes de abertura
   perpendiculares/oblicuos y conserva el fallback avanzado de mochetas;
8. expone `diagnose_wall_gap_closures()` y
   `diagnose_closed_wall_sketches()` como dry-run JSON-compatible.

Cada cierre informa Sketch/Label, `GeometryIndex`, indices de muro, indices de
fuente, modo, metodo, score y longitud. La salida agrega conteos de geometrias
usadas, ambiguas y rechazadas.

## Resultado MCP real

- dry-run: 37 segmentos, 25 aberturas, 23 regiones, 25 usadas, 0 ambiguas, 0
  rechazadas, resultado previsto de 19 segmentos;
- boton real: un `Sketch_Cerrado_*`, 19 lineas, 44 restricciones, 23 cierres;
- fuente: permanecio con 37 lineas;
- repeticion: una sola salida, mismo nombre, cero duplicados;
- Undo/Redo: 1 -> 0 -> 1 salidas y 19 lineas restauradas;
- muro BIM: `Arch.makeWall`, `IfcType=Wall`, un solido, volumen
  47.023.681.412,57 mm3;
- edicion paramétrica: desplazar 10 mm el Placement del Sketch desplazo 10 mm
  el muro; al restaurarlo volvio a su posicion;
- ventana BIM: host conservado y corte real 267.300.000,00 mm3;
- puerta BIM: host conservado y corte real 272.016.675,00 mm3;
- guardado/reapertura: 19 lineas, 44 restricciones, Wall/Base y dos Hosts
  conservados;
- recarga final: `VERSION CARGADA v0.14.7`, build `2026.08.28.2`, sin errores
  nuevos en Report View.

La copia temporal verificable se guardo en
`C:/Users/marco/AppData/Local/Temp/FA_CloseWallSketch_MCP_Test.FCStd`. Al terminar
se cerraron los documentos temporales; el original quedo como unico documento
abierto, con 198 objetos, fuente de 37 lineas y su salida historica de 23 lineas
sin cambios.

## Pruebas

- `test_room_utils`: 36/36;
- regresion real JSON `tests/fixtures/close_wall_gaps_1416.json`: aprobada;
- pruebas focales room/grid/BIM/openings: 81/81;
- `compileall`: aprobado;
- suite completa: 202/203.

La falla restante es
`test_room_label_utils.RoomLabelUtilsTests.test_collects_structured_labels_and_consolidates_duplicates`.
Se reproduce aislada, ya existia fuera del alcance y no se modifico su modulo.

## Archivos modificados

- `core/room_utils.py`
- `commands/cmd_create_closed_rooms.py`
- `tests/test_room_utils.py`
- `tests/fixtures/close_wall_gaps_1416.json`
- version/build: `core/constants.py`, `Init.py`, `InitGui.py`, `__init__.py`
- `README.md`, `DOCUMENTACION_WORKBENCH.md`, `TAREA_ACTUAL.md`,
  `RESULTADO_CODEX.md`, `ESTADO_PROYECTO.md`
- memoria reusable en `Memoria_FreeCAD/sesiones/`.

Respaldo previo:
`Respaldos_2026-08-28_FA_cerrar_buques_pre_0.14.7`.

No se modificaron `FA Tabla de ventanas`, ElectricCR, MEPWorkbenchCR,
GameEngineExportWB ni ArchGrid.

---

# HISTORIAL - ElementDataCore + Tabla de Ventanas

Fecha/hora: 2026-08-28 America/Costa_Rica
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD objetivo y probado: 1.1.3 revision 20260725
Version/build: 0.14.6 / 2026.08.28.1
Estado: IMPLEMENTADO / COMPILADO / PROBADO / VERIFICADO_MCP / PENDIENTE UPALA REAL

## Resultado funcional

Se implemento `FA Tabla de ventanas` como una sola herramienta dentro de
`FA Aberturas BIM`. Crea o reutiliza `Spreadsheet_Ventanas`, extrae ventanas BIM
nativas, valida filas contra el Sketch actual, muestra un dry-run, aplica solo
coincidencias seguras e importa/exporta mediante la API nativa de Spreadsheet.

El nucleo `core/element_data_core.py` es independiente de FreeCAD/Qt y devuelve
datos JSON-compatible. Implementa normalizacion, validacion, serializacion y
matching con estados `MATCH`, `CAMBIO`, `NO_MATCH` y `AMBIGUO`.
`apply_records(..., dry_run=True)` no escribe por defecto.

La geometria del Sketch destino manda sobre centro, orientacion y ancho. La
tabla manda sobre altura, antepecho, preset y propiedades transferibles. Hosts,
Level y relaciones BIM se resuelven nuevamente en el documento destino. No se
creo `FA_Window`: los resultados siguen siendo ventanas `ArchWindow._Window`.

## Diagnostico FreeCAD real

- FreeCAD: 1.1.3, revision 20260725.
- Ventana nativa: `Part::FeaturePython`, proxy `ArchWindow._Window`, `Base`,
  `Hosts`, `IfcType = Window`.
- `SillHeight` nativo persistente no existe en esta version. El antepecho real
  es la cota Z del Sketch `Base`; FA conserva tambien `FA_Sill_mm`.
- Los presets nativos se identifican por nombre; el entero `Preset` esta
  indexado desde uno.
- Manage Doors and Windows no cubre antepecho, preset ni transferencia.
- `ArchSchedule` es adecuado para reportes unidireccionales, no para aplicar
  registros editables a instancias.
- `Spreadsheet::Sheet.exportFile/importFile` conserva UTF-8 y valores; el
  archivo es tabulado aunque tenga extension `.csv`.
- `Document.copyObject(sheet, True)` conservo las celdas entre documentos.

## Prueba MCP de extremo a extremo

Se usaron dos documentos temporales controlados porque no estaban disponibles
dos versiones comparables de Upala. La prueba cubrio:

1. dos ventanas BIM nativas con hosts en el documento origen;
2. extraccion a `Spreadsheet_Ventanas`;
3. copia nativa y round-trip CSV;
4. Sketch destino equivalente, reordenado y con anchos modificados;
5. edicion manual de altura/antepecho en tabla;
6. validacion: dos `CAMBIO`;
7. dry-run: dos `CREATE`;
8. aplicacion: dos `CREATE`, con host del documento destino;
9. reejecucion: dos `KEEP`, sin duplicados;
10. cambio posterior: un `REPLACE` seguro y un `KEEP`;
11. Undo/Redo;
12. guardado, cierre y reapertura.

Una sonda adicional creo una ventana manual con `ElementID` coincidente. La
aplicacion devolvio `SKIP=1`, no creo reemplazos y conservo el mismo objeto.

Valores finales: anchos 1100/1300 mm desde el Sketch, alturas 1250/1500 mm y
antepechos 800/850 mm desde la tabla. El archivo verificable quedo en
`.codex_tmp/fa_window_table_end_to_end.FCStd`.

El comando fue recargado con el loader real. La barra `FA Aberturas BIM`
contiene una sola accion `FA_WindowTable`; no hay comandos duplicados.

## Archivos de esta tarea

- `core/element_data_core.py`
- `core/window_table_utils.py`
- `commands/cmd_window_table.py`
- `ui/dialog_window_table.py`
- `resources/icons/window_table.svg`
- extension minima de `core/opening_utils.py`
- registro en `InitGui.py`
- `tests/test_element_data_core.py`
- `tests/freecad_window_table_end_to_end.py`
- `tests/freecad_window_table_toolbar_smoke.py`
- version/build y documentacion del Workbench

Se creo antes de editar el respaldo
`Respaldos_2026-08-28_FA_elementdata_pre_0.14.6`. No se modificaron ElectricCR,
MEPWorkbenchCR ni GameEngineExportWB.

## Pruebas

- pruebas focales ElementDataCore/opening/bim: 46/46 aprobadas;
- `compileall FacilArquitecturaWB`: aprobado;
- prueba MCP end-to-end: aprobada;
- conflicto con ventana manual: `SKIP=1`, objeto conservado;
- recarga/registro GUI real: aprobado;
- documento real activo de levantamiento: inspeccionado solo en lectura, 132
  objetos, sin tabla ni ventanas FA agregadas.

La suite completa ejecuto 197 pruebas: 196 aprobadas y una falla previa,
reproducible tambien aislada, en
`test_room_label_utils.RoomLabelUtilsTests.test_collects_structured_labels_and_consolidates_duplicates`.
Ese modulo no pertenece al alcance y no fue modificado.

## Pendiente

Repetir solamente la validacion funcional final con las versiones reales de
Upala cuando esten accesibles. Los criterios tecnicos y la prueba real controlada
quedan satisfechos.

## Procedimiento exacto de validacion final en FreeCAD

1. Reiniciar FreeCAD 1.1.3 y cargar `FacilArquitecturaLoader.FCMacro`.
2. Abrir el documento Upala origen que contiene las ventanas BIM verificadas.
3. Ejecutar `FA Tabla de ventanas` y pulsar `Extraer del modelo`.
4. Revisar `Spreadsheet_Ventanas` y exportarla con `Exportar CSV`, o copiar la
   Spreadsheet completa al documento destino.
5. Abrir el documento Upala destino y seleccionar el Sketch vigente de centros
   de ventanas; seleccionar tambien los muros candidatos solo si se desea
   restringir la busqueda de host.
6. Ejecutar `FA Tabla de ventanas`, importar/copiar la tabla y pulsar `Validar
   contra Sketch`.
7. Confirmar que las filas esperadas sean `MATCH` o `CAMBIO`; revisar y no
   aplicar cualquier `NO_MATCH` o `AMBIGUO`.
8. Pulsar `Aplicar tabla`, revisar el resumen dry-run y confirmar.
9. Verificar anchos contra el Sketch, alturas/antepechos/presets contra la tabla,
   `Hosts` del documento destino y cortes reales de los muros.
10. Repetir `Aplicar tabla` y confirmar que no aparezcan duplicados; probar
    Ctrl+Z/Ctrl+Y y guardar, cerrar y reabrir una copia del documento.

---

# HISTORIAL ANTERIOR - FA Importar CAD estable y determinista

Fecha/hora: 2026-08-27 America/Costa_Rica
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD objetivo y probado: 1.1.3
Version/build final: 0.14.4 / 2026.08.27.1
Estado: PROGRAMADO / COMPILADO / PROBADO / VERIFICADO_MCP / VALIDADO_MANUALMENTE

## Resultado productivo 0.14.4

Se implemento una compatibilidad minima y autocancelable para FreeCAD #31637 en
`core/freecad_compat.py`. La importacion CAD solo llama un helper delgado que
abre el context manager alrededor de `importDXF.insert()`.

La clasificacion usa AST y, si hace falta, bytecode sobre
`importDXF._import_dxf_file()`. Devuelve `affected`, `not_affected` o `unknown`.
Solo `affected` sustituye temporalmente `FreeCADGui.suspendWaitCursor` y
`resumeWaitCursor`; `finally` restaura las identidades originales. El estado
`unknown` no parchea. Si una version futura incorpora la correccion, el patron
antiguo desaparece y FA desactiva automaticamente el workaround.

FreeCAD 1.1.3 real fue detectado como `affected` mediante AST, con llamadas
`resumeWaitCursor` y `suspendWaitCursor`. Una excepcion controlada dentro del
context manager dejo ambas funciones exactamente restauradas.

### Pruebas GUI reales

Se reinicio FreeCAD para cargar 0.14.4 desde cero y se acciono cuatro veces el
boton real `FA Importar referencia DWG/DXF`:

| Archivo | Insert | Comando | Resultado |
|---|---:|---:|---|
| DWG 1 | 4.310 s | 8.550 s | 139/140, cursor normal |
| DWG 2 | 3.420 s | 7.190 s | 139/140, cursor normal |
| DWG 3 | 3.960 s | 7.830 s | 139/140, cursor normal |
| DXF | 3.540 s | 6.670 s | 137/138, cursor normal |

No hubo una sola muestra de `QApplication.overrideCursor()` en espera. Los
eventos de mouse, rueda y teclado llegaron inmediatamente despues del mensaje.
Pan cambio la posicion real de camara; un clic selecciono `Layer004`; Espacio
cambio su visibilidad y luego se restauro.

Los tres DWG conservaron 15 textos, 15 capas, 53 App::Link, Puertas=11,
Ventanas=15, escala 10.788 x 23.530 m y documento sin guardar. El DXF conservo
137/138, 15 textos, 13 capas, 53 links, Puertas=11 y Ventanas=15. Las preferencias
Draft y las identidades nativas de ambas funciones coincidieron con el baseline
despues de cada importacion.

Pruebas finales: `compileall` aprobado y 161/161 pruebas Python aprobadas. Existe
una regresion obligatoria que simula FreeCAD corregido, confirma
`needs_dxf_waitcursor_workaround() == False`, no monkeypatch y llamada normal a
`insert()`.

No se modifico la instalacion de FreeCAD ni otros Workbenches. La tarea permanece
abierta hasta la validacion manual del usuario.

## Resultado A/B FreeCAD #31637

Se reprodujo el boton real en dos sesiones nuevas de FreeCAD 1.1.3. La geometria
y los dialogos terminan en ambos casos; la diferencia esta en el filtro global
de eventos instalado por `Gui::WaitCursor`.

| Evidencia | A stock | B no-op reversible durante insert |
|---|---:|---:|
| `importDXF.insert` | 3.779 s | 3.767 s |
| `import_cad_reference()` | 5.742 s | 5.354 s |
| `Command.Activated` | 7.803 s | 7.536 s |
| cursor despues del mensaje | WaitCursor shape 3 | None |
| QTimer 0/100/500/1000 | si | si |
| botones del mouse | bloqueados | responden |
| teclado | bloqueado | responde |
| pan/zoom/seleccion | pan/seleccion imposibles | verificados |

En A, Windows siguio mostrando `Responding=True` y los QTimer corrieron, pero el
WaitCursor permanecio mas de 24 s y el event filter no recibio ningun press,
release ni tecla. La rueda y el movimiento si pasaron. Los dialogos modales
respondieron, igual que en la observacion del usuario.

En B se comprobo primero que las dos funciones nativas eran builtin,
reemplazables y que no existia otro override cursor fuera de la prueba. Se
anularon solo durante el `importDXF.insert()` original y se restauraron en
`finally`; ambas identidades quedaron restituidas. El cursor fue `None` en todas
las muestras. Se verifico manualmente:

- pan: posicion de camara de `[-361245.3, 5828.5, 287645.7]` a
  `[-467474.8, 58948.7, 287645.7]`;
- zoom: altura de camara de `575291.375` a `1048249.25`;
- seleccion: clic real en el arbol selecciono `Layer004`;
- teclado: Espacio cambio visibilidad `True -> False -> True`.

En A y B quedaron 139 importados/140 totales, 15 textos, 15 capas, 53 links,
Puertas=11, Ventanas=15, escala 10.788 x 23.530 m y documento sin guardar.

Conclusion: el resultado `A bloquea / B responde` confirma practicamente que el
fallo de FA es FreeCAD #31637. No hizo falta la prueba C. No se modifico
`importDXF.py`. Esta evidencia fue la base de la compatibilidad productiva y
autocancelable implementada despues en 0.14.4.

## Reapertura por fallo de validacion manual

La validacion manual del usuario fallo con 0.14.3 / build 2026.08.26.1. El boton
real `FA Importar referencia DWG/DXF` muestra el mensaje final y permite cerrarlo,
pero FreeCAD queda trabado/no responde durante un tiempo prolongado. Por ello la
tarea no esta cerrada y las corridas MCP anteriores no prueban la recuperacion
real de la GUI.

Se conserva la correccion del perfil DXF determinista, porque si resolvio la
variabilidad de 139 frente a miles de objetos. No se revierte 0.14.3 sin evidencia.
La proxima prueba debe recorrer el QAction visible y medir el cierre del mensaje,
los retornos del nucleo/dialogo/comando, QTimer a 0/100/500/1000 ms y la capacidad
real de mover, hacer zoom y seleccionar. Tambien debe comparar, una variable por
vez, vista 3D oculta, `fitAll` omitido, seleccion limpia, cierre de vista MDI y
cierre del documento.

## Resultado

Se corrigio la dependencia accidental de las preferencias globales DXF. Antes,
FA solo controlaba escala y dialogo; `importDXF.readPreferences()` reconstruia
el modo desde booleanos globales y el mismo DXF podia producir 139 objetos
fusionados o 5.679 formas individuales. La nueva version aplica durante la
importacion un perfil moderno, rico y eficiente, y restaura exactamente todos
los valores anteriores.

El perfil conserva:

- textos;
- capas Draft;
- layouts;
- bloques ocultos/estrella;
- App::Link de bloques;
- geometria de puertas y ventanas;
- metadata FA.

El comando ahora usa el ID estable `FA_ImportCADReference`, sin timestamp.

## Instrumentacion

Se dejaron marcas `[FACILARQ][IMPORT]` con `time.perf_counter()` para:

- conversion DWG a DXF y ruta temporal;
- preferencias antes/activas/restauradas;
- `importDXF.insert`;
- ambos recomputes;
- construccion de `imported`;
- metadata;
- `viewTop`, `fitAll` y `placement_bounds`;
- entrada/salida de `finally`;
- retorno del nucleo, dialogo y `Command.Activated`;
- aparicion/cierre del QMessageBox;
- QTimer posteriores al retorno.

En la prueba final `Command.Activated` con el DXF real:

- `importDXF.insert`: 4.736 s;
- primer recompute: 0.000185 s;
- metadata: 0.000219 s;
- segundo recompute: 0.000198 s;
- `fitAll`: 0.707 s;
- retorno del nucleo: 5.661 s;
- cierre del mensaje y retorno total: 6.045 s;
- QTimer 0/100/500/1000 ms: ejecutados.

## Pruebas reales

Unidad elegida: metros, porque la cabecera declara milimetros incorrectamente.
`Pared_Concreto001` quedo en 10.788 x 23.530 m.

| Archivo/ruta | Importados/totales | Textos | Capas | Tiempo |
|---|---:|---:|---:|---:|
| DWG depurado 1 | 139/140 | 15 | 15 | 6.67 s |
| DWG depurado 2 | 139/140 | 15 | 15 | 6.30 s |
| DWG depurado 3 | 139/140 | 15 | 15 | 5.27 s |
| DXF depurado | 137/138 | 15 | 13 | 4.66 s |
| DWG no depurado | 325/326 | 161 | 33 | 13.75 s |

Las tres corridas DWG automatizadas:

- mostraron y cerraron el mensaje final;
- dejaron documento nuevo sin guardar;
- conservaron Puertas (11 hijos) y Ventanas (15 hijos);
- ejecutaron QTimer a 0/100/500/1000/2000 ms;
- devolvieron el control al banco MCP, pero no anticiparon el bloqueo observado
  en la interaccion manual.

El perfil hostil de formas individuales se probo de forma reversible. FA produjo
139 objetos, no 5.679, y restauro luego el perfil hostil; el banco restauro al
final la configuracion original del usuario.

## DXF original frente a conversion ODA

- DXF original depurado: 2.721.495 bytes, SHA-256
  `9F4403701C5C6F694E588F2949FF45799AEBE64D024A49CAC176433C5AC0EC6A`.
- DXF desde DWG depurado: 2.761.715 bytes, SHA-256
  `DFB87C6BCD21B0F8C72D8495C9B7562E40E27C81C4140A97484342F72C088AA1`.
- Ambos conservan 53 bloques, 87 INSERT y 15 TEXT.
- ODA cambia 111 LWPOLYLINE por 109 LWPOLYLINE + 2 POLYLINE y agrega dos capas
  de texto escaladas; de ahi 137 frente a 139 objetos importados.

El DXF temporal se conservo para diagnostico en
`FacilArquitecturaWB/.codex_tmp/import_diagnostics_20260826/`.

## Regresiones

- 161/161 pruebas Python: aprobadas.
- `compileall`: aprobado.
- smoke nuevo de perfil temporal y restauracion en FreeCAD: aprobado.
- Compound sintetico: aprobado.
- `Pared_Concreto001` real: 37 lineas a 150 mm + 2 lineas de columna,
  reejecucion sin duplicar, fuente con 21 hijos/140 bordes y sin Explode.
- guardado/reapertura: 326 objetos, 161 textos y metadata conservados.

## Diagnostico del congelamiento historico, superado por la prueba A/B

En las primeras corridas no se reprodujo el congelamiento exacto ni la cifra
398. Una llamada MCP agoto 90 s y entonces se interpreto como espera del
despacho MCP. La prueba posterior desde el boton real demostro que esa
interpretacion era incompleta: Qt seguia ejecutando trabajo, pero el WaitCursor
global bloqueaba botones y teclado.

El DWG no depurado produce 325 importados/326 totales y es el caso real mas
cercano a la cifra reportada. La causa demostrada de resultados variables era el
perfil global heredado; queda eliminada en 0.14.3.

## Archivos modificados

- `FacilArquitecturaWB/core/cad_reference_import.py`
- `FacilArquitecturaWB/core/freecad_compat.py`
- `FacilArquitecturaWB/commands/cmd_import_cad_reference.py`
- `FacilArquitecturaWB/core/constants.py`
- `FacilArquitecturaWB/package.xml`
- `FacilArquitecturaWB/tests/test_cad_reference_import.py`
- `FacilArquitecturaWB/tests/test_freecad_compat.py`
- `FacilArquitecturaWB/tests/freecad_cad_import_profile_smoke.py`
- `FacilArquitecturaWB/DOCUMENTACION_WORKBENCH.md`
- `FacilArquitecturaWB/TAREA_ACTUAL.md`
- `FacilArquitecturaWB/RESULTADO_CODEX.md`
- `ESTADO_PROYECTO.md`
- `Memoria_FreeCAD/incidentes/2026-08-26_import-cad-perfil-global.md`

Respaldo previo:
`FacilArquitecturaWB/Respaldos_2026-08-26_FA_import_pre_0.14.3/`.

No se modificaron ElectricCR, MEPWorkbenchCR ni GameEngineExportWB. No hubo
commit ni push. FreeCAD se reinicio para cargar 0.14.4 desde cero, los cuatro
documentos temporales se cerraron sin guardar y FreeCAD permanece abierto.

## Pendientes

- Repetir la validacion manual del usuario en 0.14.4; hasta que pase, la tarea
  sigue abierta.
- Verificar en un FreeCAD futuro que el workaround se desactive automaticamente.
- Bloques dinamicos de mobiliario contienen coordenadas extremas y pueden ampliar
  `fitAll`/el rango informado; se dejo fuera para no alterar datos sin una tarea
  especifica.
- Los IDs antiguos con timestamp permanecen en memoria hasta un futuro reinicio;
  la barra recargada usa el comando estable.

---

# RESULTADO ANTERIOR - Importacion CAD y Compound de paredes

Fecha/hora: 2026-08-23 America/Costa_Rica
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD objetivo y probado: 1.1.3
Version/build final: 0.14.2 / 2026.08.23.2
Estado: DIAGNOSTICADO / CORREGIDO / PROBADO_MCP_REAL

## 1. Regresion de importacion DWG

Se uso el DWG real `1416 Levantamiento 250424 Depurado.dwg`, el mismo indicado
por el usuario. La instrumentacion temporal con `time.perf_counter()` y marcas
`[FACILARQ][IMPORT]` midio el flujo completo vigente:

- conversion DWG a DXF: 0.622 s;
- `importDXF.insert`: 5.410 s;
- primer y segundo recompute: menos de 0.001 s en conjunto;
- metadata y `_placement_bounds`: menos de 0.001 s cada uno;
- `fitAll`: 0.554 s;
- retorno de `import_cad_reference`, aparicion del mensaje final y retorno de
  `run_import_dialog`: 6.660 s en total;
- resultado: 139 objetos importados mas un objeto de metadata, documento nuevo
  sin guardar y preferencias Draft restauradas.

Las pruebas A/B reversibles terminaron sin bloqueo: `fit_view=False` (5.138 s),
sin `fitAll` (4.946 s), sin segundo recompute (5.335 s), sin limites (5.507 s) y
sin metadata (5.570 s). La ruta directa produjo 139 objetos: conversion 0.474 s,
`importDXF.insert` 4.297 s y recompute 0.0002 s.

El `QMessageBox` real aparecio a los 5.166 s, visible y activo, y el comando
retorno a los 5.672 s al cerrarlo. Un DWG pequeno y un DXF importaron 5 objetos
en 1.252 s y 0.937 s, respectivamente. El DWG pequeno se guardo, cerro y reabrio
como FCStd con 6 objetos, incluida la metadata.

El unico atasco reproducido pertenecio al banco MCP: Qt conservaba internamente
un boton del raton como presionado y `FreeCADMCP.gui_dispatch` posponia toda tarea
GUI; habia ocho llamadas en cola y ninguna habia entrado al importador. Enviar
eventos de liberacion restauro el despacho sin cerrar FreeCAD. Por tanto no se
modifico `cad_reference_import.py` ni se elimino ninguna etapa correcta.

El historial local sincronizado con GitHub confirma contenido identico del nucleo
y del comando entre los checkpoints del 6 y 18 de agosto. El cambio posterior
visible en `InitGui.py` organiza barras y registra comandos nuevos, pero no altera
la importacion. Preferencias verificadas: `dxfScaling=1000`, dialogo DXF activo,
importador moderno, creacion Part activa y textos desactivados. Convertidor ODA:
25.12.0. Las preferencias quedaron restauradas despues de cada prueba.

## 2. Causa de `Pared_Concreto001`

El `Part::Feature Compound` real contiene 21 componentes y 140 bordes. La version
0.14.1 lo separaba por Wire: nueve componentes entraban en `profile_axis`; ademas,
la columna compacta marcaba el unico id de fuente del Compound y filtraba los 63
registros de borde del resto de paredes. De ahi surgian seis Sketches, 11 lineas y
espesores falsos 428, 440 y 700 mm.

El flujo manual que funciona no corresponde a `Part Explode` por hijos, sino a
`Draft Downgrade / splitWires`: entrega 140 objetos Edge a la ruta estable de
topologia y pares paralelos. Ese fue el oraculo de la correccion.

## 3. Cambio aplicado

Para estrategia automatica y exclusivamente `Part::Feature` con Shape Compound,
el nucleo crea en memoria una fuente virtual por borde. No crea objetos de Explode,
no cambia el arbol y conserva el objeto fuente para metadata. App::Link,
puertas/ventanas especializadas, Shapes no Compound y tipos derivados conservan
su ruta anterior.

La reejecucion registra `FA_ExtractionStrategy` y `FA_SourceObjectNames` y reemplaza
solo Sketches FA creados antes desde exactamente los mismos objetos y estrategia.
Una falla previa al momento de crear el reemplazo deja intacta la salida anterior.

## 4. Resultado real en FreeCAD

Comparacion controlada sobre copias del Shape real:

| Resultado | Compound directo | 140 bordes splitWires |
|---|---:|---:|
| Ejes totales | 39 | 39 |
| Muros | 37 a 150 mm | 37 a 150 mm |
| Columna | cruz de 2 lineas | cruz de 2 lineas |
| 428 / 440 / 700 mm | 0 | 0 |
| Claves geometricas | identicas | identicas |

El Compound directo conservo 21 hijos y 140 bordes. Solo agrego dos Sketches; no
creo ningun `Part::Feature` intermedio. Segunda ejecucion: siguen siendo dos
Sketches. Undo, Redo, guardar y reabrir conservaron las 37 lineas de muro, la cruz
de columna y la fuente intacta. El comando GUI real selecciono ambos Sketches al
terminar y tampoco duplico en la segunda ejecucion.

## 5. Archivos modificados

- `FacilArquitecturaWB/core/centerline_utils.py`
- `FacilArquitecturaWB/core/constants.py`
- `FacilArquitecturaWB/package.xml`
- `FacilArquitecturaWB/tests/test_centerline_network.py`
- `FacilArquitecturaWB/README.md`
- `FacilArquitecturaWB/DOCUMENTACION_WORKBENCH.md`
- `FacilArquitecturaWB/TAREA_ACTUAL.md`
- `FacilArquitecturaWB/RESULTADO_CODEX.md`
- `ESTADO_PROYECTO.md`
- `Memoria_FreeCAD/incidentes/2026-08-23_import-dwg-y-compound-paredes.md`

Respaldos previos: `FacilArquitecturaWB/Respaldos_2026-08-23_FA_compound_centerlines_pre_0.14.2/`.
No se modificaron ElectricCR, MEPWorkbenchCR ni GameEngineExportWB.

## 6. Pruebas

- 151/151 pruebas Python: aprobadas.
- Smoke FreeCAD real de Compound sintetico: aprobado, dos ejes de 4000 mm, fuente intacta.
- A/B real `Pared_Concreto001`: aprobado, geometria y grupos identicos.
- Reejecucion, Undo/Redo, guardado/reapertura: aprobados.
- Comando GUI real, dos ejecuciones: aprobado.
- DWG real, DWG pequeno, DXF, guardado y mensaje final: aprobados.

Artefactos de validacion cerrados en FreeCAD y conservados para inspeccion:
`.codex_tmp/FA_Control_Upala_Paredes.FCStd` y
`.codex_tmp/FA_ParedCompound_Regression.FCStd`.

## 7. Pendientes y prueba del usuario

Estas dos regresiones quedan cerradas tecnicamente. No se avanzo a
Areas/Wires/Spaces. Para comprobacion manual:

1. Recargar `FacilArquitecturaLoader.FCMacro` y confirmar
   `VERSION CARGADA: v0.14.2 | build 2026.08.23.2`.
2. Importar `1416 Levantamiento 250424 Depurado.dwg`; confirmar el mensaje final y
   que el documento nuevo queda sin guardar.
3. Seleccionar directamente `Pared_Concreto001`, sin Explode, y ejecutar
   `FA Centros desde seleccion`.
4. Confirmar dos Sketches: 37 lineas de muro con `FA_WallThickness = 150 mm` y
   dos lineas de columna; no deben aparecer 428, 440 ni 700 mm.
5. Ejecutar de nuevo: deben seguir existiendo solo esos dos Sketches.
6. Probar Undo/Redo y guardar/reabrir una copia.

---

# Historial anterior - FA Cambiar tipo de puerta

Fecha/hora: 2026-08-13 America/Costa_Rica
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD objetivo y probado: 1.1.3
Version/build final: 0.13.1 / 2026.08.13.2
Estado: PROGRAMADO / COMPILADO / PROBADO / VERIFICADO_MCP / VERIFICADO_VISUAL

## Correccion posterior del boton Aplicar

El usuario detecto que seleccionar `Glass door` y pulsar `Aplicar` no ejecutaba
el cambio. La causa era exclusivamente la conexion Qt del dialogo:
`QDialogButtonBox.Apply` tiene `ApplyRole` y no emite la señal `accepted` que
estaba conectada. Se conecto directamente `apply_button.clicked` con
`QDialog.accept`.

Se agrego
`tests/freecad_change_door_type_dialog_smoke.py`, ejecutado dentro de FreeCAD
1.1.3 real. La prueba localiza el boton, ejecuta `click()` y confirma
`QDialog.Accepted`. Tambien se repitio la prueba integral de tres puertas y
volvio a aprobar cambio de preset, identidad, corte, regeneracion, rechazos y
persistencia. El Workbench fue recargado en vivo como 0.13.1 / 2026.08.13.2; el
documento del usuario permanecio abierto, activo y sin guardar.

## Resultado

Se implemento el comando interno `FA_ChangeDoorType`, visible como
`FA Cambiar tipo de puerta`, dentro de la barra `FA Aberturas BIM`. Acepta una o
varias puertas Arch/BIM existentes y cambia su preset mediante el generador nativo
instalado de FreeCAD, sin crear geometria propietaria de puerta.

La implementacion conserva la identidad del objeto. En FreeCAD 1.1.3 real se
comprobo que es seguro generar una puerta nativa temporal y transferir al mismo
objeto seleccionado su `Base`, `WindowParts`, `Preset`, `Frame` y `Offset`. Luego
se restauran y validan dimensiones, Placement, Hosts, Normal, apertura, simbolos,
IfcType, contenedor y propiedades `FA_*`. La puerta/Base temporal y la Base anterior
sin referencias se retiran solamente despues de validar el corte.

## Investigacion y presets instalados

Se revisaron los archivos primarios de la instalacion local:

- `Mod/BIM/ArchWindowPresets.py`
- `Mod/BIM/ArchWindow.py`
- `Mod/BIM/bimcommands/BimWindow.py`

Hallazgos reales:

- FreeCAD: `1.1.3`, revision `20260725`, hash
  `145529fe741292ff0b3977a01195bf0247425794`.
- `ArchWindowPresets.WindowPresets` es una lista de nombres simples.
- Los presets nativos de puerta instalados son exactamente `Simple door` y
  `Glass door`.
- `Sliding door` no existe en esta instalacion y por eso no se ofrece ni se probo.
- `Preset` es `App::PropertyInteger`, bloqueada en la interfaz.
- `ArchWindow._Window.onChanged()` no reconstruye la geometria al cambiar solo
  `Preset`; la forma depende de `Base`, `WindowParts`, dimensiones y estado Arch.
- `makeWindowPreset()` crea el Sketch y la puerta, asigna `Preset`, `Frame`,
  `Offset` e `IfcType`, y ejecuta recomputes internos.

Por ello se descarto expresamente cambiar solamente `Preset`.

## Seguridad, lote y regeneracion

La operacion completa se ejecuta dentro de una transaccion FreeCAD desde el
comando. Todas las selecciones se validan antes de modificar la primera puerta. Si
una transferencia o un corte falla, el comando aborta el lote.

Para cada host se conserva una copia de la forma y del subvolumen anterior. Despues
del cambio se verifica que:

- la puerta conserve el mismo objeto, Hosts, Placement, Normal y dimensiones;
- la forma de puerta tenga solidos validos;
- el nuevo subvolumen siga dentro del soporte nominal;
- `Wall.Shape.common(subvolume).Volume` sea practicamente cero;
- el volumen perforado del Wall no cambie cuando se conserva el vano exterior.

Las puertas dobles especiales `FA_InsertDoubleDoorBIM` y otros objetos de varias
hojas incompatibles se rechazan claramente y sin modificarlos. Tambien se rechazan
Window, Opening Element y Part generico.

Una puerta procedente de `FA_CreateDoorsFromSketch` conserva
`FA_SourceSketch`/`FA_SourceGeometryIndex` y recibe `FA_TypeOverride = true`. El
Sketch fuente guarda `FA_DoorTypeOverrides` como JSON por indice. El motor actual
de `opening_utils.py` consulta ese mapa al regenerar, de modo que una excepcion
individual conserva su preset y no altera las otras lineas del Sketch.

## Interfaz

El dialogo muestra:

- cantidad de puertas seleccionadas;
- tipo actual comun o `Varios`;
- combo construido desde los presets instalados;
- `Conservar ancho y alto`, siempre activo y bloqueado por seguridad;
- `Conservar apertura (%)`, activo por defecto;
- botones Aplicar y Cancelar.

Los mensajes de operacion usan el prefijo `[FACILARQ][PUERTAS]`.

## Archivos modificados por esta tarea

- `FacilArquitecturaWB/core/door_type_utils.py`
- `FacilArquitecturaWB/core/opening_utils.py`
- `FacilArquitecturaWB/commands/cmd_change_door_type.py`
- `FacilArquitecturaWB/ui/dialog_change_door_type.py`
- `FacilArquitecturaWB/resources/icons/change_door_type.svg`
- `FacilArquitecturaWB/InitGui.py`
- `FacilArquitecturaWB/Init.py`
- `FacilArquitecturaWB/__init__.py`
- `FacilArquitecturaWB/core/constants.py`
- `FacilArquitecturaWB/package.xml`
- `FacilArquitecturaWB/tests/test_door_type_utils.py`
- `FacilArquitecturaWB/tests/freecad_change_door_type_end_to_end.py`
- `FacilArquitecturaWB/tests/freecad_change_door_type_toolbar_smoke.py`
- `FacilArquitecturaWB/README.md`
- `FacilArquitecturaWB/DOCUMENTACION_WORKBENCH.md`
- `FacilArquitecturaWB/NOTES_RESEARCH.md`
- `FacilArquitecturaWB/RESULTADO_CODEX.md`

No se modificaron ElectricCR, MEPWorkbenchCR ni GameEngineExportWB.

## Pruebas ejecutadas

1. `python -m compileall -q FacilArquitecturaWB`: APROBADO.
2. `python -m unittest discover -s FacilArquitecturaWB/tests -p "test_*.py"`:
   148/148 APROBADAS.
3. Prueba integral `freecad_change_door_type_end_to_end.py` en FreeCADCmd 1.1.3:
   APROBADA.
   - tres puertas y seleccion multiple;
   - anchos 800, 1000 y 1200 mm;
   - alturas 2100 y 2300 mm;
   - `Simple door -> Glass door -> Simple door`;
   - repeticion sobre la misma puerta;
   - identidad, Label, Placement, Width/Height, Hosts, Normal, Opening, IfcType,
     Level, propiedades FA y corte conservados;
   - cero puertas temporales o duplicadas;
   - ventana, Opening Element y puerta doble rechazados;
   - override por indice respetado al regenerar desde Sketch;
   - guardar, cerrar y reabrir FCStd.
4. Regresion `freecad_openings_end_to_end.py`: APROBADA, dos puertas, dos
   ventanas, dos muros, Undo/Redo, idempotencia y persistencia.
5. Regresion `freecad_openings_only_end_to_end.py`: APROBADA, seis aberturas,
   rechazos geometricos esperados y persistencia.
6. Regresion `freecad_double_door_bim_smoke.py`: APROBADA, puerta doble alojada y
   libre, 13 solidos, corte de 840 000 000 mm3 y persistencia.
7. Diagnostico MCP real inicial: APROBADO.
   - FreeCAD 1.1.3;
   - documento activo `La_Cruz_Versión_2_1`;
   - modulo nativo `ArchWindowPresets` de la instalacion 1.1;
   - presets detectados `Simple door`, `Glass door`.
8. Hot restart y smoke MCP real: APROBADO.
   - version 0.13.1 / build 2026.08.13.2;
   - `FA_ChangeDoorType` registrado;
   - una sola barra `FA Aberturas BIM`;
   - una sola accion `FA_ChangeDoorType` en la barra.
9. Smoke geometrico MCP real posterior a la recarga: APROBADO.
   - misma identidad tras `Simple door -> Glass door -> Simple door`;
   - 900 x 2100 mm;
   - Placement, Hosts y Normal iguales;
   - apertura 65% conservada con la casilla activa y restablecida a 0% al
     desactivarla;
   - volumen del Wall igual;
   - interseccion residual Wall/hueco: `0.0 mm3`;
   - una puerta total y cero auxiliares visibles;
   - `FA_DoorTypeOverrides = {"0":"Simple door"}` al finalizar.
10. Captura isometrica MCP de una `Glass door` a 35% alojada en un Wall:
    VERIFICADA VISUALMENTE; marco, panel de vidrio, simbolo de apertura y hueco
    aparecen coherentes, con residuo geometrico Wall/hueco `0.0 mm3`.

Artefacto temporal de prueba:

- `.codex_tmp/fa_change_door_type.FCStd`

## Estado real de FreeCAD

La sesion grafica del usuario no se cerro. El hot restart se ejecuto mediante el
loader existente y dejo `La_Cruz_Versión_2_1` activo. Las pruebas MCP de geometria
usaron y cerraron solamente el documento temporal `FAChangeDoorTypeMCP`; no se
guardo ni se modifico el FCStd del usuario.

## Limitaciones reales

- Solo se ofrecen presets integrados en `ArchWindowPresets`; Parts Library no se
  incluye en esta primera version porque usa un flujo de importacion diferente.
- FreeCAD 1.1.3 instalado no contiene `Sliding door`.
- La puerta doble especial FA se rechaza deliberadamente para no degradar su
  familia de dos hojas a un preset de una hoja.
- `Conservar ancho y alto` no se puede desactivar en esta version: evitar cambios
  accidentales del vano exterior es parte del criterio de seguridad.

Pendientes funcionales respecto de `TAREA_ACTUAL.md`: ninguno.

## Procedimiento exacto de prueba para el usuario

1. Ejecutar `FacilArquitecturaLoader.FCMacro`.
2. Confirmar en consola `VERSION CARGADA: v0.13.1 | build 2026.08.13.2`.
3. Activar `Facil Arquitectura`.
4. Seleccionar una o varias puertas Arch/BIM existentes. No seleccionar el Wall,
   ventanas ni otros objetos junto con ellas.
5. En `FA Aberturas BIM`, pulsar `FA Cambiar tipo de puerta`.
6. Elegir `Simple door` o `Glass door`, decidir si conserva la apertura y pulsar
   Aplicar.
7. Confirmar en consola los mensajes `[FACILARQ][PUERTAS]` y
   `Cambio completado: N/N`.
8. Verificar visualmente el nuevo tipo y que la puerta siga en el mismo punto y
   dentro del mismo Wall.
9. Guardar, cerrar y reabrir el FCStd; repetir el cambio en sentido contrario.
10. Si la puerta procede de un Sketch FA, regenerar `FA Puertas BIM` y comprobar
    que el indice modificado conserva el preset elegido.

## Validacion manual final - 2026-08-27

El usuario probo la importacion real en FreeCAD y confirmo que la aplicacion ya
no queda pegada despues de importar el DWG. Con esta evidencia se aprueba la
validacion manual de Facil Arquitectura 0.14.4 / build 2026.08.27.1 para el
incidente FreeCAD #31637.

Estado del incidente: CERRADO TECNICAMENTE.

Queda pendiente solamente el cierre administrativo en GitHub (commit/push),
que no se realizo en esta etapa.



---

# RESULTADO - Orden del arbol del modelo

Fecha/hora: 2026-08-27 16:28 America/Costa_Rica
Proyecto: `Macros-de-Freecad / FacilArquitecturaWB`
FreeCAD objetivo: 1.1.3
Version global: se mantiene `0.14.4 / 2026.08.27.1` hasta prueba real.

## Objetivo

Aplicar la regla de residencia de objetos sin modificar documentos FCStd existentes:
los elementos permanentes deben residir en la estructura BIM nativa del edificio y
los auxiliares deben quedar separados del modelo terminado. Las ramas temporales de
importacion CAD se dejan intactas.

## Diagnostico

Los comandos de muros, puertas, ventanas, openings y columnas ya usan el `Level`
nativo. `FA_CreateSiteFloorBIM`, cielos modulares y plataforma tambien tenian
contencion espacial/funcional explicita. El desorden nuevo se originaba principalmente
en `FA_CreateProject`/`FA_CreateMasterSketches`, que llamaban a la estructura legacy
completa, y en `FA_CreateBuildingGrid`, que mezclaba referencias auxiliares como hijos
directos del Level.

## Cambios

- `core/project_structure.py`: nueva estructura de soporte por demanda; se conserva
  `ensure_project_structure()` completo para compatibilidad.
- `commands/cmd_create_project.py`: crea/reutiliza Building + Level y solo Parameters.
- `commands/cmd_create_master_sketches.py`: crea solo Parameters + MasterSketches.
- `commands/cmd_centerlines_from_selection.py`, `cmd_door_centerlines_from_selection.py`,
  `cmd_window_centerlines_from_selection.py` y `cmd_create_closed_rooms.py`: crean solo
  `FA_MasterSketches`, sin materializar ramas legacy ajenas.
- `commands/cmd_collect_room_labels.py`: crea solo `FA_Parameters`.
- `commands/cmd_create_sample_geometry.py`: crea solo Parameters + MasterSketches.
- `core/bim_structure_utils.py`: grupo auxiliar reutilizable por Level.
- `core/building_grid_utils.py`: ArchGrid y trazado visible pasan a `Auxiliares FA`.
- pruebas focales actualizadas para ausencia de ramas legacy vacias y enrutamiento
  de auxiliares.
- `README.md` y `DOCUMENTACION_WORKBENCH.md`: regla canonica incorporada.

No se modifico el FCStd del usuario, no se reorganizaron `_BlockDefinitions`,
`_UnreferencedBlocks` ni `Capas`, y no se eliminaron objetos/grupos legacy.

## Pruebas

- `py_compile`: aprobado para `project_structure.py`, `bim_structure_utils.py`,
  `building_grid_utils.py`, los comandos de proyecto/master, los seis comandos auxiliares
  auditados (centros, cierre, rotulos y muestra) y las dos pruebas modificadas.
- prueba focal de estructura por demanda: aprobada; no aparecen `FA_BIM`,
  `FA_Areas` ni `FA_Electromechanical` cuando no se solicitan.
- prueba focal de grupo auxiliar: aprobada; el mismo Level reutiliza un unico
  `FA_Auxiliary_<Level>` con rol `auxiliary_group`.
- prueba focal de enrutamiento de ArchGrid: aprobada; un Level usa su grupo
  auxiliar y un contenedor legacy no-Level conserva el comportamiento anterior.

## Estado

CODIGO Y DOCUMENTACION ACTUALIZADOS / PRUEBAS FOCALES APROBADAS / PRUEBA REAL EN
FREECAD 1.1.3 PENDIENTE. No incrementar la version global hasta esa validacion.


## Resultado adicional GPT - FacilArquitecturaWB 0.14.5

Fecha/hora: 2026-08-27 17:24 America/Costa_Rica
Version/build: 0.14.5 / 2026.08.27.2

Se diagnostico mediante captura del arbol de FreeCAD que puertas y ventanas no estaban creadas fisicamente dos veces: el mismo `Name` (`Window`, `Window001`, etc.) aparecia bajo el muro anfitrion y tambien directamente bajo el Building Storey. La causa en codigo era la combinacion de `obj.Hosts=[wall]` con `add_to_level()` aplicado tanto al objeto como a su Base.

Cambios:

- `core/bim_structure_utils.py`: nuevo `tag_target_level()` sin modificar `Level.Group`.
- `core/opening_utils.py`: puertas, ventanas y vanos alojados conservan `Hosts` y trazabilidad de nivel, pero no se agregan como segunda membresia al Level; el Base tampoco se agrega como hermano del Level.
- `core/double_door_bim.py`: misma regla para puerta doble alojada; la libre sigue en Level.
- `InitGui.py`: aviso por `QMessageBox` solo al detectar cambio de `VERSION`, con ultima version notificada persistida en parametros de FreeCAD.
- `core/constants.py`, `package.xml` y metadatos: version 0.14.5 / build 2026.08.27.2.

Pruebas: `py_compile` aprobado para los modulos Python modificados. Falta validacion funcional en FreeCAD 1.1.3 real del arbol y del aviso de version. No se abrio, modifico ni guardo el FCStd original.


## Parche candidato build 2026.08.28.4 - puertas junto a pared lateral

Se diagnostico que `opening_utils.py` proyectaba los extremos del Sketch sobre el muro
anfitrion pero conservaba literalmente la separacion longitudinal respecto de una pared
lateral. Ademas, `FA_OpensInward` era principalmente trazabilidad y no participaba en
la inferencia automatica del cuadrante de giro.

Se preparo la correccion:

- nuevo `core/door_corner_utils.py`, puro/JSON-compatible;
- busca una pared lateral aproximadamente perpendicular y unica;
- calcula la interseccion con el eje del host y la **cara real** de la pared lateral a
  partir de su espesor y angulo;
- traslada el vano completo manteniendo su longitud;
- infiere `START/END`, `LEFT/RIGHT` y `OpensInward=True`;
- rechaza cruces laterales que no definen un lado de apertura unico;
- dos extremos equivalentes -> ambiguo/no modificar;
- `opening_utils.py` aplica la misma regla al comando normal `FA Puertas BIM`;
- `door_table_utils.py` reutiliza el plan para Tabla de Puertas y protege valores
  explicitos de la tabla frente a sobrescrituras silenciosas;
- puertas dobles pueden ajustar el marco pero mantienen `HingeEndpoint=BOTH`;
- trazabilidad nueva: `FA_CornerSnapped`, `FA_CornerWall`,
  `FA_CornerGapBefore_mm`, `FA_CornerShift_mm`, `FA_CornerSnapReason`.

Tolerancia candidata: `180 mm` para esquina, separada de `250 mm` de host.

Validacion fuera de FreeCAD:

- `tests/test_door_corner_utils.py`: **6/6**;
- cubre START, END, conservacion exacta del ancho, fuera de tolerancia, ambiguedad,
  pared transversal y pared oblicua;
- `py_compile`: `door_corner_utils.py`, `opening_utils.py`, `door_table_utils.py` y
  `freecad_door_corner_snap_probe.py` aprobados.

Se dejo preparada tambien `tests/freecad_door_corner_snap_end_to_end.py`, que crea un documento temporal controlado con un muro host, una pared lateral y dos puertas; comprueba snap a la cara real, ancho conservado, bisagra/apertura, corte BIM, puerta lejana sin mover, reejecucion, Undo/Redo y guardar/reabrir.

Queda pendiente ejecutar `tests/freecad_door_corner_snap_probe.py` y `tests/freecad_door_corner_snap_end_to_end.py` en FreeCAD 1.1.3/MCP. No se declara validado en entorno real todavia.
