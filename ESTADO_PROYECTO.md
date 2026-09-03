# ESTADO VIGENTE - CRBIMCore / Barra comun Espacios y Recintos v0.1

Ultima actualizacion: 2026-09-02 America/Costa_Rica
Componentes: `CRBIMCore 0.1.0`, `FacilArquitecturaWB`, `ElectricCR`
FreeCAD: `1.1.3`, revision `20260725`
Estado: **V0.1 CERRADA Y VERIFICADA MEDIANTE MCP**.

- Existen cuatro command IDs comunes: seleccionar, informar, nombrar y guia.
- Facil Arquitectura y ElectricCR reutilizan la misma implementacion y registran
  la barra de forma idempotente.
- Space es canonico; Area valida es fallback; AMBIGUOUS/NOT_FOUND son seguros.
- Nombrar modifica solo Label y conserva identidad, geometria y jerarquia.
- La macro poligonal desde muros BIM permanece funcional, visible y sin
  reescritura.
- Smoke real, persistencia, Undo/Redo, regresiones y verificacion visual
  aprobaron; FreeCAD quedo sin documentos temporales abiertos.

No iniciar v0.2 automaticamente.

---

# ESTADO VIGENTE - ElectricCR / RoomResolver fase 2A

Ultima actualizacion: 2026-09-01 America/Costa_Rica
Componentes: `ElectricCR` + `CRBIMCore 0.1.0`
FreeCAD: `1.1.3`, revision `20260725`
Estado: **FASE 2A CERRADA Y VERIFICADA MEDIANTE MCP**.

- El calculo de iluminacion usa RoomResolver para enumerar recintos.
- Space-only, legacy-only, prioridad Space, AMBIGUOUS y NOT_FOUND aprobaron.
- `DatosRecintos` conserva 12 columnas; recalculo no duplica hojas/objetos.
- Spaces permanecen read-only; no se crearon ni migraron dispositivos.
- Contrato semantico del arbol documentado, sin reorganizacion de modelos.
- Pendiente futuro: objeto electromecanico comun y reconstruccion idempotente.

---

# ESTADO VIGENTE - CRBIMCore / RoomResolver fase 1

Ultima actualizacion: 2026-09-01 America/Costa_Rica
Componente: `CRBIMCore 0.1.0`
FreeCAD: `1.1.3`, revision `20260725`
Estado: **FASE 1 READ-ONLY CERRADA Y VERIFICADA MEDIANTE MCP**.

## Resultado actual

- Existe un nucleo neutral JSON-compatible sin FreeCAD/GUI/Qt.
- El adaptador reconoce Arch Space manual, Spaces FA y Areas heredadas con geometria/metadatos suficientes.
- Prioridad: `NATIVE_SPACE > LEGACY_AREA > NOT_FOUND`.
- Dos candidatos fisicos plausibles producen `AMBIGUOUS`.
- `HVACSpace.BaseSpace` sigue la identidad fisica; HVAC convertido sin enlace y SubArea quedan excluidos.
- Smoke real: 8 candidatos, 17 objetos sin cambios, guardado/reapertura estable.
- Pruebas: 11/11 RoomResolver, 22/22 contratos FA y E2E real de Spaces aprobado.

FacilArquitecturaWB conserva `0.14.11 / 2026.09.01.14`. No se modificaron ElectricCR, MEPWorkbenchCR ni modelos originales.

Pendiente futuro, no iniciado: adopcion del resolver por consumidores de disciplina. Requiere una tarea nueva; no continuar automaticamente.

---

# ESTADO VIGENTE - FacilArquitecturaWB / Espacios BIM

Ultima actualizacion: 2026-09-01 America/Costa_Rica
Version/build DEV: `0.14.11 / 2026.09.01.14`
FreeCAD: `1.1.3`, revision `20260725`
Estado: **TAREA DE IDENTIDAD PERSISTENTE CERRADA Y VERIFICADA MEDIANTE MCP**.

## Resultado actual

- Los `Arch Space` reconocidos se actualizan en sitio y conservan `Name`, `FA_RoomID`, `FA_RoomUID`, Base y `PropertyLink` externos.
- `NO_MATCH` crea solo el Space nuevo.
- Los Spaces `stale` se reportan y conservan.
- `AMBIGUO` no escribe sobre candidatos.
- Undo/Redo, guardar/cerrar/reabrir y `GameExportExclude` aprobaron en el E2E real.
- La demo `FA_Demo_Casa_123456` se resincronizo con dos Spaces antes y despues; no creo duplicados.
- Pruebas focales locales: 22/22.

Incidencias resueltas en esta build: proxies recargables para los dos comandos de recintos, actualizacion en sitio del Sketch documental y reconocimiento seguro de Spaces FA creados por la demo.

Siguiente trabajo posible: disenar `RoomResolver`. **No esta implementado ni iniciado**; requiere una tarea nueva y explicita.

---

# CIERRE TEMPORAL - FA Puertas BIM / GeometryIndex 1

Fecha: 2026-08-31 America/Costa_Rica
Version/build conservado: `0.14.11 / 2026.08.31.3`
Estado: **CIERRE TEMPORAL CON LIMITACION CONOCIDA**.

La validacion manual del usuario sobre `FA_Geom1_Downstream` no acepto la posicion visual de GeometryIndex 1. Esto prevalece sobre la validacion MCP/captura previa: el caso **no se considera corregido**.

Se detiene deliberadamente la cadena de nuevas heuristicas. El build `.3` se conserva como baseline tecnico porque las pruebas focales y E2E aprobaron y no se observaron regresiones en los casos que funcionan. La excepcion de GeometryIndex 1 queda documentada como deuda tecnica localizada, no como bloqueo del Workbench.

Decision de arquitectura para el futuro: separar resolucion automatica segura de excepciones persistentes (`AUTO_OK`, `AUTO_AMBIGUOUS`, `MANUAL_OVERRIDE`) antes de intentar nuevas correcciones geometricas globales. No agregar otra tolerancia/score/caso especial al resolvedor solo por esta puerta.

## Verificacion final del cierre

- FreeCAD real: 1.1.3 revision 20260725.
- Baseline cargada: `0.14.11 / 2026.08.31.3`, desde la ruta DEV esperada.
- Algoritmo y version/build: sin modificaciones durante el cierre.
- Pruebas focales: 63/63.
- Smoke MCP: puerta BIM de 900 mm con host, subvolumen y corte real aprobados.
- GeometryIndex 1: limitacion conocida no resuelta; no se intentaran mas
  heuristicas geometricas en esta fase.
- Copia `FA_Geom1_Downstream` cerrada y sus cuatro residuos temporales eliminados.
- Original: unico documento abierto, 157 objetos, guardado y sin cambios
  pendientes antes/despues de la limpieza.
- Respaldos de builds `.2` y `.3`: conservados.

El cierre define una baseline limpia dentro del alcance de FA Puertas BIM. El
worktree general sigue conteniendo cambios previos y de otros modulos que no se
tocaron ni se limpiaron.

---

# ESTADO DEL PROYECTO

Ultima actualizacion: 2026-08-31 America/Costa_Rica

## Proyecto activo

`Macros-de-Freecad / FacilArquitecturaWB`

Tarea activa: `FA Puertas BIM - GeometryIndex 1 downstream / Base ArchWindow`.

## Estado

IMPLEMENTADO / VALIDADO MEDIANTE MCP Y CAPTURA / VALIDACION MANUAL PENDIENTE.

- Version candidata: `0.14.11`
- Build: `2026.08.31.3`
- Fuente de desarrollo: copia local sincronizada con Google Drive/OneDrive
- FreeCAD real: 1.1.3, revision 20260725
- Workbench cargado desde la ruta DEV esperada

## Resultado vigente GeometryIndex 1 downstream - 2026-08-31

La prueba manual del build `.2` demostro que `BOUNDED` no bastaba. El recorrido
capa por capa confirmo Sketch y `FA_Projected` correctos. La primera divergencia
estaba en el Base de `Simple door`: `Wire0` coincidia con el segmento, pero la hoja
usa `Wire1`, retraida 50 mm por lado. GeometryIndex 1 terminaba con bisagra fisica
a 50 mm del CAD y hoja 100 mm menor.

El build `.3` adapta solo el Base de puertas `BOUNDED`: expande el marco exterior
alrededor de la hoja, conservando `Window.Width=FA_Width_mm=663.850602 mm`. La
Wire1 y hoja coinciden ahora con `0..663.850602`; el marco exterior y corte ocupan
`-50..713.850602`, dentro de las caras `-56.341660..773.658340`.

La copia real esta abierta y guardada como `FA_Geom1_Downstream`. MCP numerico,
captura superior, reejecucion, Undo/Redo, reapertura, E2E BOUNDED, Tabla de Puertas,
puerta doble y ventanas aprobaron. GeometryIndex 6, 8, 3 y 9 no cambiaron.

Pendiente: validacion manual del usuario sobre la copia abierta. El original sigue
con 137 objetos y su estado previo `isTouched()==True`; no se guardo ni modifico.

## Cierre vigente GeometryIndex 1 vs 6 - 2026-08-31

La prueba A/B sobre copia exacta demostro una diferencia geometrica general. El
indice 1 queda completamente contenido entre dos caras externas opuestas: luz
`830.000 mm`, ancho `663.851 mm` y holgura `166.149 mm`. Elegir cualquiera de
las dos jambas es ambiguo y el snap anterior lo desplazaba `56.342 mm`. El indice
6 solo tiene una cara externa candidata y su ajuste de `53.441 mm` es unico.

El nuevo estado `BOUNDED` conserva la posicion longitudinal del Sketch, pero
retiene la orientacion BIM inferida. En FreeCAD 1.1.3 real, el indice 1 quedo
`BOUNDED`, sin shift, `START/RIGHT/Mode2`; el indice 6 permanecio `SNAPPED`,
`START/LEFT/Mode1`. Los indices 3, 8 y 9 conservaron sus protecciones previas.

La copia real creo 10 puertas con Hosts y cortes positivos. Reejecucion 10/10,
Undo/Redo, guardado/reapertura, E2E de esquinas, Tabla de Puertas y puerta doble
aprobaron. Suite focal 62/62. La suite global conserva fuera de alcance una falla
de rotulos y dos cargas que requieren `pytest` en el Python 3.9 del sistema.

El documento original ya estaba tocado al inicio (137 objetos,
`isTouched()==True`); no se modifico ni se guardo durante esta tarea.

## Cierre vigente GeometryIndex 9 y aviso de build - 2026-08-30

La prueba A/B obligatoria demostro que el snap actual desplazaba la geometria 9
`64.386719 mm`; neutralizar solo `resolve_door_corner_snap()` devolvio los endpoints
pre-snap y la coincidencia visual con el simbolo CAD. La causa era una cara de cruce
ubicada dentro del propio tramo: era el unico `JAMB_ONLY` con `target_axis` interior.

El planificador puro conserva ahora la posicion para ese caso, sin regla por indice.
Los indices 3 y demas `JAMB_ONLY` con cara exterior siguen ajustandose; Servicio
Sanitario (6), `NO_FIT` (8), Mode1/Mode2, Host, corte y Tabla de Puertas aprobaron.
La copia real produjo 10 puertas, reejecucion sin duplicados, Undo/Redo y reapertura.

El aviso de Workbench usa `LastNotifiedVersion + LastNotifiedBuild`. La transicion
real `.1 -> .2` mostro un solo dialogo y la segunda activacion quedo silenciosa.
El documento original termino como unico documento abierto, 157 objetos, guardado y
sin tocar. Suite focal 61/61; E2E de esquinas y Tabla de Puertas aprobados.

La seccion historica de fase 3 que atribuia el caso solo al Sketch queda superada por
esta evidencia A/B.

## Cierre fase 3 de puertas - 2026-08-30

La puerta desplazada (`GeometryIndex=9`) no sufre doble movimiento: el Sketch ya
mide `819.210 mm` frente a `696.235 mm` del simbolo CAD. Base, marco y corte son
coherentes y no invaden el perfil de muro original. Debe corregirse el eje fuente,
no recortarse automaticamente.

La puerta oblicua exterior (`GeometryIndex=7`) queda `AUTO/AUTO` porque el Sketch
no conserva el sentido del arco ni existe Tabla de Puertas en el documento. Una
copia exacta confirmo la ruta segura: `START/RIGHT/OpensInward=True` mediante Tabla
produce `Mode2`, alinea la hoja con el arco CAD (`dot=0.9946`) y conserva Host,
ancho, posicion y corte. Repeticion KEEP, Undo/Redo y reapertura aprobaron.

`GeometryIndex=8` permanece como `NO_FIT` correcto (`903.036 > 830.000 mm`,
exceso `73.036 mm`). Servicio Sanitario, indice 6, quedo sin regresion en
`START/LEFT/Mode1`. Pruebas puras focales: 60/60. No se cambio codigo, version ni
build. El original termino como unico documento abierto, 157 objetos,
`isSaved()==True` e `isTouched()==False`.

## Correccion fase 2 de puertas - 2026-08-30

El giro simple se traduce por geometria fisica a `Mode1/Mode2`; invertir START/END
no cambia la puerta. El snap verifica ambas jambas y devuelve `NO_FIT` sin recortar
el ancho. Cruces/T inversas pueden alinear una cara con estado `JAMB_ONLY`, pero no
inventan apertura.

MCP controlado y copia real 1416 aprobados. GeometryIndex 6 permanece correcto; 1
usa `Mode2` y abre al cuadrante esperado; 8 detecta 903.036 > 830.000 mm con 73.036
mm de penetracion; 3 alinea jamba y conserva giro `AUTO`. Tabla de Puertas, cambio
de tipo, puerta doble, ventanas, Host/corte, idempotencia, Undo/Redo y reapertura
aprobaron. Original: 157 objetos, `isTouched() == False`.

Suite focal pura 63/63; global 225/226 con la unica falla preexistente de rotulos
de recintos. Respaldo: `Respaldos_2026-08-30_FA_puertas_fase2_pre_build`.

## Diagnostico limitado de puertas - 2026-08-30

Muestra real: GeometryIndex 6 correcta; 1 con cuadrante invertido; 8 con ancho
mayor que la luz entre dos caras; 3 en cruce sin direccion lateral unica.

Hallazgo principal: el preset `Simple door` conserva `Edge8,Mode1` en todos los
casos. `FA_OpeningSide`, `FA_OpensInward` y `Normal` no seleccionan `Mode2`; por
eso un caso `LEFT` coincide y uno `RIGHT` abre al lado opuesto. Ademas, el snap no
valida simultaneamente la jamba contraria y el rechazo de cruces mezcla alineacion
de cara con inferencia de apertura.

Siguiente fase recomendada: traduccion fisica `Mode1/Mode2`, guarda `NO_FIT` entre
dos jambas y separacion entre candidato de cara y candidato de cuadrante. Riesgo
medio; preservar explicitamente el caso correcto GeometryIndex 6. Documento real
intacto: 157 objetos, `isTouched() == False`.

## Resultado vigente 0.14.8 - Puertas BIM, snap lateral y tablas

El documento 1416 usa un `Arch Wall` multisegmento. El resolvedor de esquina ya
excluye solamente el tramo anfitrion y reutiliza los demas tramos laterales del mismo
objeto como geometria virtual. En la prueba real se resolvieron tres snaps unicos de
10 ejes (indices 1, 6 y 8), sin alterar anchos, hosts ni cortes. El comando estable
usa un proxy recargable porque FreeCAD 1.1.3 no ofrece `removeCommand`.

`ElementDataCore` y `FA_DoorTable` quedaron validados en FreeCAD real: dry-run,
CREATE/KEEP/REPLACE, puerta simple y doble, bisagra/apertura, host/corte, Undo/Redo
y reapertura. La Tabla de Ventanas tambien paso su regresion integral. Siete pruebas
MCP BIM pasaron en una corrida consolidada. Suite pura: 220/221; permanece solo la
falla preexistente de `test_room_label_utils`, fuera del alcance. El documento 1416
original quedo intacto, con 137 objetos y sin cambios pendientes.

La recarga final por loader desde MCP cerro FreeCAD inesperadamente. La recuperacion
nativa restauro con exito el mismo documento de 137 objetos sin cambios. En la
sesion limpia se cargo FacilArquitecturaWB desde DEV, build `2026.08.29.1`, y se
confirmaron el proxy recargable y la barra unica. FreeCAD permanece abierto.

## Tarea anterior: FA Cerrar buques de puertas y ventanas

La 0.14.7 queda cerrada y validada en FreeCAD 1.1.3 real mediante MCP: 37 -> 19 lineas, 25/25 aberturas usadas, 23 cierres, 44 restricciones, muro nativo y cortes de puerta/ventana confirmados.

## Resultado principal vigente de 0.14.7

`FA_CloseWallSketch` usa ahora un planificador abertura-primero. La geometria
real del levantamiento 1416 mostro ventanas y puertas alineadas con sus muros,
incluyendo aberturas mayores de 2500 mm, cadenas consecutivas y cinco casos
junto a esquina/T. El algoritmo conserva el muro como autoridad, permite que la
abertura justifique localmente su longitud, extiende solo el tramo colineal hasta
la pared de apoyo y no aplica candidatos ambiguos.

Resultado real: 37 -> 19 lineas, 25/25 geometrias usadas, 23 cierres, 0
ambiguas, 0 rechazadas y 44 restricciones. El comando tiene ID estable y una
sola accion en la barra. Repeticion sin duplicados, Undo/Redo, guardado/reapertura,
muro Arch paramétrico y cortes nativos de puerta/ventana quedaron validados.

Pruebas focales: 81/81. Suite completa: 202/203; la unica falla es la regresion
aislada de `test_room_label_utils`, fuera del alcance y reproducible por separado.
El documento 1416 original quedo intacto y como unico documento abierto.

## Tarea anterior: ElementDataCore + Tabla de Ventanas

La 0.14.6 implemento `Spreadsheet_Ventanas`, matching seguro y transferencia
entre documentos. Su validacion final con archivos Upala reales permanece como
seguimiento independiente; esta tarea no modifico ese flujo.

## Historial anterior: importacion CAD y continuidad de muros

FA ya no hereda de forma accidental el modo global de importacion DXF. Usa
temporalmente el perfil moderno de formas fusionadas y conserva textos, layouts,
bloques y capas; al terminar restaura exactamente las preferencias del usuario.

El mismo DXF convertido genero:

- 139 objetos con el perfil fusionado;
- 5.679 con formas individuales.

Las pruebas automatizadas anteriores no reprodujeron el congelamiento, pero la
validacion manual del usuario si fallo: despues de cerrar `Importacion CAD
completada`, FreeCAD queda trabado/no responde durante un tiempo prolongado. El
timeout MCP previo ya no se considera evidencia suficiente de un problema
exclusivo de la cola MCP. Antes de la prueba A/B, la recuperacion real de la GUI
seguia sin verificar.

La nueva prueba A/B mediante el boton real aislo el problema. En FreeCAD stock,
`QApplication.overrideCursor()` queda en WaitCursor shape 3 y el filtro global
bloquea botones y teclado aunque Qt, CPU, QTimer y dialogos sigan respondiendo.
Con `suspendWaitCursor/resumeWaitCursor` anulados reversiblemente solo durante
`importDXF.insert`, el cursor permanece en `None` y pan, zoom, seleccion y teclado
responden. Las funciones nativas se restauraron en `finally`.

Esto confirma FreeCAD issue #31637 para el flujo FA. La 0.14.4 incorpora una
compatibilidad temporal y autocancelable: inspecciona estructuralmente el
importador instalado, aplica monkeypatch solo en `affected`, restaura las
funciones en `finally` y no actua en `not_affected` o `unknown`.

Tres DWG consecutivos y el DXF directo se importaron desde el boton real con
cero muestras de WaitCursor posterior. Pan, zoom, seleccion y teclado
respondieron. La tarea no se cierra hasta la prueba manual del usuario.

## Banco real

| Archivo | Importados/totales | Textos | Capas | Tiempo |
|---|---:|---:|---:|---:|
| DWG depurado, 0.14.4 corrida 1 | 139/140 | 15 | 15 | 8.55 s comando |
| DWG depurado, 0.14.4 corrida 2 | 139/140 | 15 | 15 | 7.19 s comando |
| DWG depurado, 0.14.4 corrida 3 | 139/140 | 15 | 15 | 7.83 s comando |
| DXF depurado, 0.14.4 | 137/138 | 15 | 13 | 6.67 s comando |
| DWG no depurado | 325/326 | 161 | 33 | 13.75 s |

Las tres corridas DWG y el DXF se ejecutaron mediante el boton real, cerraron el
QMessageBox, dejaron documentos nuevos sin guardar y comprobaron eventos Qt,
pan, zoom, seleccion y teclado. La aceptacion final sigue requiriendo la prueba
manual del usuario.

## Escala y estructura

Unidad real usada: metros. La cabecera DXF/DWG declara milimetros, por lo que
`auto` no es correcto para este levantamiento.

`Pared_Concreto001` importada mide 10.788 x 23.530 m, conserva Shape Compound,
21 hijos y 140 bordes. Puertas y ventanas siguen detectables por sus capas:

- Puertas: 11 hijos;
- Ventanas: 15 hijos.

## Regresiones

- `FA Centros desde seleccion`: 37 lineas de muro a 150 mm + 2 lineas de
  columna; reejecucion no duplica.
- Compound sintetico sin Explode: aprobado.
- Guardar/cerrar/reabrir: 326 objetos, 161 textos y metadata conservados.
- Pruebas Python: 161/161.
- Smoke de perfil CAD temporal/restauracion: aprobado.

## Archivos principales modificados

- `FacilArquitecturaWB/core/cad_reference_import.py`
- `FacilArquitecturaWB/core/freecad_compat.py`
- `FacilArquitecturaWB/commands/cmd_import_cad_reference.py`
- `FacilArquitecturaWB/core/constants.py`
- `FacilArquitecturaWB/package.xml`
- `FacilArquitecturaWB/tests/test_cad_reference_import.py`
- `FacilArquitecturaWB/tests/test_freecad_compat.py`
- `FacilArquitecturaWB/tests/freecad_cad_import_profile_smoke.py`
- documentacion y memoria de continuidad

No se modificaron ElectricCR, MEPWorkbenchCR ni GameEngineExportWB.

## Pendientes

- Validacion manual del usuario: APROBADA el 2026-08-27; FreeCAD ya no queda
  pegado despues de importar el DWG.
- En una version futura, comprobar que el log indique `not_affected` y
  `workaround disabled`; entonces FA debe importar sin monkeypatch.
- Bloques dinamicos de mobiliario contienen coordenadas extremas y pueden ampliar
  `fitAll`/rango de inserciones. Requiere diagnostico separado si molesta.
- Nombres antiguos del comando con timestamp siguen en memoria hasta un futuro
  reinicio, pero la barra activa usa `FA_ImportCADReference` estable.
- No avanzar a Areas/Wires/Spaces por esta tarea.


## Tarea anterior - cierre de buques

El incidente anterior de importacion DWG/DXF permanece cerrado tecnicamente y
validado manualmente. La tarea activa cambia a `FA_CloseWallSketch`.

Intervencion directa GPT en Drive, 2026-08-27:

- `core/room_utils.py` actualizado en sitio: el cierre ya no une dos extremos en
  el punto medio; fusiona la pared a una continuidad sobre un eje comun.
- se conserva cualquier angulo real de pared;
- puerta/ventana valida el buque pero no impone la direccion del muro;
- se rechaza el cierre cuando otra pared cruza el interior del buque;
- se admite la reduccion de varios tramos consecutivos a uno cuando la topologia
  lo permite;
- metadatos `FA_CenterlineKind=doors/windows` tienen prioridad;
- `tests/test_room_utils.py` actualizado con casos horizontal, vertical,
  diagonal, desfase, dos buques, cruce y no-cierre sin evidencia;
- `commands/cmd_create_closed_rooms.py` fue actualizado en su archivo original
  de Drive; un primer listado no lo mostro, pero el inventario completo confirmo
  su ID original. La copia temporal creada durante la verificacion se elimino;
- nombre visible nuevo: `FA Cerrar buques de puertas y ventanas`;
- identificador interno `FA_CloseWallSketch` se mantiene por compatibilidad.

Validacion disponible hasta ahora: sintaxis y pruebas focales del nucleo fuera
de FreeCAD. Falta recargar el Workbench y validar sobre
`1416 Levantamiento 250424 Depurado` en FreeCAD 1.1.3. No incrementar version
global ni declarar cierre hasta esa prueba.

## Git

- Rama: `agent/respaldo-electriccr-2026-08-10`
- Commit base: `707a0fc Respaldar avances ElectricCR y workbenches`
- Cambios sin commit: si, incluidos muchos cambios previos ajenos
- Commit/push: no realizados

## Cierre del incidente - 2026-08-27

La validacion manual del usuario fue aprobada en FreeCAD real. Facil Arquitectura
0.14.4 / build 2026.08.27.1 ya no deja la interfaz pegada tras la importacion DWG.
El incidente FreeCAD #31637 se considera cerrado tecnicamente en este proyecto.

GitHub sigue pendiente de commit/push; Drive permanece como fuente de verdad.

## FA Cerrar buques - seleccion explicita de aberturas (2026-08-27 10:04)

Ajuste incremental aplicado directamente en Drive. Cuando la seleccion incluye
`Sketch_Centros_Puertas` y/o `Sketch_Centros_Ventanas`, esos sketches pasan a
ser el alcance explicito de aberturas y no se mezclan con un barrido global del
documento. Si no se selecciona ninguna abertura, se mantiene el descubrimiento
automatico. El log diferencia `modo_aberturas=selection` y
`modo_aberturas=automatic`.

Archivos: `core/room_utils.py` 0.4.0,
`commands/cmd_create_closed_rooms.py` 0.4.0 y `tests/test_room_utils.py`.
`py_compile` aprobado; 23 pruebas sinteticas focales aprobadas.
Pendiente prueba en FreeCAD 1.1.3 para confirmar que los sketches seleccionados
justifican los buques reales y aparecen en `FA_SourceOpeningSketches`.



## FA Cerrar buques - asociacion geometrica por zona local (2026-08-27 11:20)

Se corrigio el segundo problema identificado despues de la seleccion explicita.
El algoritmo anterior todavia exigia que cada linea de puerta/ventana fuera casi
paralela y coincidente con el eje del muro para justificar un buque.

La 0.4.0 mantiene la coincidencia colineal como evidencia preferida, pero agrega
un fallback de zona local: una linea de `Sketch_Centros_Puertas` o
`Sketch_Centros_Ventanas` puede validar el buque aunque este perpendicular o
ligeramente desplazada, siempre que pase por/cerca de la zona del buque y sea
longitudinalmente compatible con ese tramo. Una abertura lejana no valida el
cierre. La pared sigue siendo la unica autoridad de direccion.

El comando ahora lista en `[FACILARQ]` los sketches usados como evidencia y el
resumen final informa `sketches_abertura_usados`.

Validacion fuera de FreeCAD: `py_compile` aprobado y 23/23 pruebas sinteticas
focales aprobadas en entorno stub del nucleo. Pendiente prueba real en FreeCAD
1.1.3 seleccionando juntos pared + puertas + ventanas y revisando
`FA_SourceOpeningSketches`, `FA_ClosedGapCount` y la geometria resultante.

## FA Cerrar buques - 0.5.0 consecutivos y angulos (2026-08-27 12:05)

Intervencion directa GPT en Drive sobre los archivos canonicos:

- `core/room_utils.py` -> 0.5.0;
- `commands/cmd_create_closed_rooms.py` -> 0.5.0;
- `tests/test_room_utils.py` actualizado.

La nueva iteracion permite que varias evidencias de abertura respalden el mismo
buque, por ejemplo una ventana y una puerta consecutivas. Tambien permite
prolongar extremos de paredes perpendiculares u oblicuas hasta su interseccion
real cuando existe evidencia local de puerta/ventana. Los encuentros angulados
conservan sus dos tramos y el nodo; no se ortogonalizan. Intersecciones dentro
del interior de un tramo existente no se tratan como buques faltantes.

La seleccion explicita de puertas/ventanas sigue teniendo prioridad; sin
seleccion de aberturas se mantiene el modo automatico. Las aberturas pueden ser
paralelas, perpendiculares u oblicuas respecto al muro porque funcionan como
zona de evidencia, no como autoridad de direccion.

Validacion disponible: `py_compile` aprobado y 26/26 pruebas sinteticas focales
aprobadas. Pendiente prueba en FreeCAD 1.1.3 sobre el levantamiento real antes
de declarar cierre o subir version global del Workbench.

## FA Cerrar buques - 0.6.0 mochetas y perfil seguro (2026-08-27 12:58)

Se incorpora una segunda evidencia conservadora para casos donde
`Sketch_Centros_Puertas` o `Sketch_Centros_Ventanas` esten incompletos:

- puerta/ventana sigue siendo la evidencia primaria;
- si falta la abertura, un buque colineal puede cerrarse solo cuando ambos
  extremos muestran un par de lineas cortas, aproximadamente perpendiculares y
  compatibles con mochetas;
- una sola mocheta no basta;
- una discontinuidad corta sin abertura ni par de mochetas no se cierra, incluso
  usando el antiguo argumento avanzado `allow_unmarked`;
- los encuentros perpendiculares u oblicuos siguen requiriendo evidencia de
  puerta/ventana y no se adivinan por mochetas.

Parametros predeterminados nuevos:

- buque maximo 2500 mm;
- alineacion 25 mm;
- tolerancia angular 3 grados;
- fallback por mochetas activado.

Los valores heredados 3000/5/2 se migran automaticamente solo si permanecian
intactos; cualquier personalizacion previa se conserva.

Trazabilidad: `FA_MochetaClosureCount`, `mocheta_gap_count` y log
`por_mochetas`. El comando usa seleccion explicita de aberturas cuando existe y
`collect_selected_wall_candidates()` para separar pared de puertas/ventanas.

Validacion fuera de FreeCAD: `py_compile` aprobado y 28/28 pruebas sinteticas
focales aprobadas. Pendiente validacion en FreeCAD 1.1.3 antes de incrementar
version global o declarar la tarea cerrada.


## FA Cerrar buques - 0.7.0 seleccion explicita estricta (2026-08-27 14:10)

Ajuste directo GPT en Drive para que la seleccion de sketches controle de forma
inequivoca el alcance de las aberturas.

- en `selection` solo se usan como candidatos los sketches de puerta/ventana
  seleccionados;
- el fallback por mochetas queda desactivado por defecto en ese modo y solo se
  usa si el usuario lo activa expresamente;
- el modo automatico conserva su preferencia de mochetas;
- nueva trazabilidad en el resultado: `FA_OpeningSourceMode`,
  `FA_OpeningCandidateSketches`, `FA_SourceOpeningSketches` y
  `FA_MochetaFallbackEnabled`;
- el log final diferencia candidatos de abertura de sketches realmente usados.

Archivos canonicos modificados en el mismo ID de Drive:
`core/room_utils.py` 0.7.0 y `commands/cmd_create_closed_rooms.py` 0.7.0.

Validacion fuera de FreeCAD: sintaxis aprobada y 28/28 pruebas focales
aprobadas. Sigue pendiente la prueba real en FreeCAD 1.1.3 antes de declarar
cierre o incrementar la version global del Workbench.


## Facil Arquitectura - ajuste 0.8.0 de cierre de buques (2026-08-27 15:34)

Se refuerzo el comportamiento solicitado para seleccion explicita: detectar los
sketches de puertas/ventanas no es suficiente; cuando el usuario los selecciona,
esos sketches son la autoridad de alcance y su geometria se usa como evidencia
local autoritativa para asociar buques. El modo automatico permanece mas
conservador. La direccion y topologia final siguen viniendo exclusivamente de
los tramos de pared.

Archivos: `core/room_utils.py` 0.8.0, `commands/cmd_create_closed_rooms.py` 0.8.0
y `tests/test_room_utils.py`. Validacion sintetica: 30/30 pruebas aprobadas mas
`py_compile`. Pendiente prueba real en FreeCAD 1.1.3.


## Tarea adicional - orden del arbol del modelo (2026-08-27 16:28 America/Costa_Rica)

Objetivo: hacer que las herramientas actuales de Facil Arquitectura creen un modelo
ordenado sin modificar el FCStd `1416 Levantamiento 250424 Depurado` ni reorganizar
las ramas temporales de importacion CAD.

Regla adoptada: toda herramienta que cree un objeto permanente debe insertarlo
automaticamente en la estructura espacial y funcional correcta del edificio; los
objetos temporales, de diagnostico, construccion o compatibilidad deben residir en
ramas auxiliares y ocultarse cuando corresponda.

Intervencion en Drive:

- la jerarquia permanente sigue siendo BIM nativa `Building -> Level`;
- `FA_CreateProject` crea/reutiliza Building y Level antes de los datos de soporte;
- la estructura de soporte se crea por demanda y deja de fabricar ramas legacy vacias;
- `FA_CreateMasterSketches` crea solo Parameters + MasterSketches;
- `FA_CreateBuildingGrid` coloca ArchGrid y trazado recortado en `Auxiliares FA`
  dentro del Level;
- `ensure_project_structure()` completo se conserva para compatibilidad y no se
  migran documentos existentes;
- muros, puertas, ventanas, openings, columnas, losa, cielos y plataforma se
  conservaron sin cambios de geometria porque ya usan contencion BIM nativa o una
  contencion funcional explicita documentada.

Validacion fuera de FreeCAD: `py_compile` aprobado para los cinco modulos modificados y las dos pruebas actualizadas; pruebas focales de estructura por demanda, reutilizacion del grupo auxiliar y enrutamiento de la cuadricula aprobadas.

Pendiente: prueba real en FreeCAD 1.1.3 de `FA Crear proyecto`, `FA Crear sketches
maestros` y `FA Cuadricula ArchGrid de referencia` antes de incrementar la version
global del Workbench.


### Auditoria ampliada de comandos de soporte

Se encontro la causa directa de las ramas vacias observadas en el arbol de
`1416 Levantamiento 250424 Depurado`: varios comandos auxiliares aun llamaban
`ensure_project_structure()` completo. Se actualizaron en sus archivos originales:

- `cmd_centerlines_from_selection.py`;
- `cmd_door_centerlines_from_selection.py`;
- `cmd_window_centerlines_from_selection.py`;
- `cmd_create_closed_rooms.py`;
- `cmd_collect_room_labels.py`;
- `cmd_create_sample_geometry.py`.

Ahora cada uno solicita solamente `FA_MasterSketches`, `FA_Parameters` o ambos, segun
su salida real. `py_compile` aprobado para los seis comandos.


## Cambio 0.14.5 - residencia unica de aberturas

Se corrigio la doble aparicion visual de puertas y ventanas alojadas: `Hosts` mantiene la pertenencia al muro y ya no se duplica el mismo objeto ni su Base en `Level.Group`. Se agrego `tag_target_level()` para conservar trazabilidad sin segunda residencia. La puerta doble libre sigue siendo miembro directo del Level; la alojada sigue al host.

El Workbench muestra una ventana de confirmacion solo cuando cambia `VERSION`; repetir hot restart sobre la misma version no vuelve a mostrarla. Build actual `2026.08.27.2`. Pendiente prueba visual en FreeCAD 1.1.3.


## Ampliacion validada build 2026.08.29.1 - snap de puertas a esquina

Se agrego un nucleo puro para detectar una pared lateral unica proxima a un extremo
de puerta y alinear la jamba con su cara real, conservando el ancho del Sketch. Para
puertas de una hoja se infiere bisagra y giro hacia la pared; dobles conservan `BOTH`.
La tabla no sobrescribe silenciosamente valores explicitos contradictorios. El
documento 1416 y el modelo controlado pasaron la validacion MCP completa; el Wall
multisegmento se resuelve sin crear objetos auxiliares. Ver el resultado vigente al
inicio de este archivo y `FacilArquitecturaWB/RESULTADO_CODEX.md`.
