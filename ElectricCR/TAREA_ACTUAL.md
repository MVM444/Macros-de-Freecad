# ElectricCR - Tarea actual

**Fecha:** 2026-08-10 20:31, America/Costa_Rica.

**Estado:** CORRECCION IMPLEMENTADA Y RENDERIZADA; VALIDACION EN EL FREECAD REAL DE MARCO PENDIENTE.

## Objetivo actual - popup oscuro del panel Registrar acometida

Corregir la lista emergente oscura de los `QComboBox` de
`Configuracion del proyecto/Registrar_Acometida_y_Ruta.FCMacro` sin alterar
calculos, datos ni la estructura del Task Panel.

## Resultado tecnico actual

- Se confirmo que el QSS del formulario era correcto, pero el popup Qt6 puede
  quedar fuera del arbol visual de `AcometidaRoot` al entrar en Gui.Control.
- Cada vista nativa `combo.view()` recibe ahora directamente fondo blanco,
  texto oscuro, seleccion azul y colores deshabilitados.
- La prueba reproduce el reparentado dentro de un `QDockWidget` llamado
  `Tareas` y renderiza los tres tabs y el popup con tema oscuro y claro.
- `py_compile` y el smoke test de FreeCAD 1.1.3 pasaron.

## Validacion pendiente de Marco

Cerrar el panel abierto, ejecutar de nuevo `Registrar acometida y ruta` y
desplegar los combos de material/conductor, medidor, tablero, Wire y area.

No actualizar `HISTORIAL_CAMBIOS.md` hasta recibir esa validacion.

---

## Contexto anterior: centro de circulo en Ruta critica

**Fecha:** 2026-08-10 20:18, America/Costa_Rica.

**Estado:** IMPLEMENTACION Y PRUEBA TECNICA COMPLETADAS; VALIDACION VISUAL DE MARCO PENDIENTE.

### Objetivo

Permitir que `Conectar/RutaCritica_Seleccionados.FCMacro` use el centro
geometrico de una arista circular como origen o destino de la ruta.

## Resultado tecnico actual

- Una arista circular usa `Curve.Center`, aun cuando FreeCAD entregue tambien
  el punto donde se hizo clic sobre la circunferencia.
- El endpoint se identifica como `CIRCLE_CENTER` en el resolver y metadatos.
- Aristas lineales conservan el punto de clic fiable y su fallback anterior.
- El smoke test completo paso en FreeCAD 1.1.3, incluida una ruta real hacia
  el centro de un circulo, Undo/Redo y guardar/reabrir temporal.

## Validacion pendiente de Marco

Seleccionar el borde de un circulo como origen o destino y confirmar en la
vista que la ruta llega al centro del circulo.

No actualizar `HISTORIAL_CAMBIOS.md` hasta recibir esa validacion.

---

## Contexto anterior: RectFromBoundaryLines con caras BIM

**Fecha:** 2026-08-10 20:06, America/Costa_Rica.

**Estado:** IMPLEMENTACION Y PRUEBA TECNICA COMPLETADAS; VALIDACION VISUAL DE MARCO PENDIENTE.

### Objetivo

Ampliar `Areas/RectFromBoundaryLines.FCMacro` para aceptar caras seleccionadas
de paredes BIM/Arch, conservando su flujo anterior con aristas.

## Resultado tecnico actual

- Las caras verticales de muros se convierten en lineas limite proyectadas en XY.
- En caras horizontales se toma el borde recto mas cercano al punto del clic.
- Se pueden mezclar aristas y caras BIM.
- El area guarda `FA_SourceMethod` y enlaces `FA_SourceWalls` hacia los muros.
- La macro no modifica los muros fuente ni guarda un documento de proyecto.
- El smoke test con cuatro muros Arch reales paso en FreeCAD 1.1.3, incluyendo
  geometria, compatibilidad con aristas, Undo/Redo y guardar/reabrir temporal.

## Validacion pendiente de Marco

Seleccionar con Ctrl las caras interiores de dos o mas muros BIM reales y
confirmar visualmente que el rectangulo usa los limites esperados. Si se usa
la cara superior, hacer clic cerca del borde interior que se desea tomar.

No actualizar `HISTORIAL_CAMBIOS.md` hasta recibir esa validacion.

---

## Contexto anterior: Ruta critica solo seleccionados

**Fecha:** 2026-08-10, America/Costa_Rica.

**Estado:** IMPLEMENTACION COMPLETA -> PRUEBAS TECNICAS REALIZADAS -> VALIDACION FUNCIONAL DE MARCO PENDIENTE.

### Objetivo

Mejorar `Conectar/RutaCritica_Seleccionados.FCMacro` para que el primer
objeto o subelemento seleccionado sea el origen geometrico y los siguientes
sean destinos independientes, conservando el flujo ortogonal existente.

## Alcance de la correccion

- usar `Face.CenterOfMass`, `Vertex.Point` y el punto fiable seleccionado
  sobre una arista;
- conservar el fallback `get_connection_point()` para objetos completos;
- preservar caras, aristas o vertices distintos del mismo objeto;
- solicitar altura Z y radio en un solo dialogo;
- usar 235 mm como referencia editable para EMT de 2 pulgadas;
- reducir el radio cuando no cabe y usar 0 mm como ruta sin curva;
- mantener agrupamiento, nombres, multiples destinos, transaccion y logs;
- guardar metadatos geometricos sin crear enlaces que puedan causar ciclos.

## Resultado tecnico

- Se agrego `Conectar/selection_geometry.py` como helper comun pequeno.
- `Ajustar_Alimentador_o_Ramal_Manual.FCMacro` delega en ese helper la
  resolucion de subgeometria y el radio maximo uniforme.
- `ElectricCR/tests/smoke_ruta_critica_seleccionados.py` paso en FreeCAD
  1.1.3 con geometria real Part/Draft, radio 235/otro/0/reducido,
  endpoints altos y bajos, mismo objeto, multiples destinos, repeticion,
  Undo/Redo y guardar/reabrir una copia temporal.
- `USE_RESULTS_SHEET` permanece en `False`.

## Validacion pendiente de Marco

Desde FreeCAD GUI, seleccionar objetos, caras, vertices y aristas reales en
el orden deseado y confirmar que el resultado visual, el punto de clic sobre
aristas, la curva y el dialogo corresponden al flujo de Marco.

No actualizar `HISTORIAL_CAMBIOS.md` en esta etapa.

---

## Contexto anterior: legibilidad del panel de acometida

La tarea anterior corrigio el contraste de
`Configuracion del proyecto/Registrar_Acometida_y_Ruta.FCMacro` bajo temas
claros y oscuros, sin modificar calculos ni rutas. Su validacion visual final
por Marco permanece pendiente.

---

## Contexto anterior: altura de luminarias Link

La tarea anterior corrigio `Iluminacion/ColocarLuminarias_Link.FCMacro` para que:

- conserve el tipo de luminaria asignado a cada area mediante
  `LightingTypeKey`;
- use como altura 3D la altura elegida explicitamente en el dialogo;
- no reemplace esa altura por `LightingMountHeight` ni por el valor
  predeterminado del registro;
- mantenga el simbolo 2D en Z=0 y eleve solamente la geometria 3D del
  maestro enlazado.

### Causa confirmada

Con la opcion `Usar el tipo asignado en cada area`, la macro reutilizaba
tambien `LightingMountHeight` y, en su defecto, la altura predeterminada del
tipo. Para `Luminaria 60x60` ese valor es 3000 mm. Por eso la altura escrita
en el dialogo se leia correctamente, pero se descartaba antes de crear el
maestro `App::Link`.

### Validacion requerida

- probar desde la interfaz con dos areas que tengan tipos distintos;
- escribir una altura diferente de 3000 mm;
- confirmar en vista axonometrica que ambos modelos 3D usan esa altura;
- confirmar en planta que los simbolos 2D permanecen en Z=0.

No actualizar `HISTORIAL_CAMBIOS.md` hasta recibir validacion visual de Marco.

---

## Contexto anterior: consolidacion de conexiones

Consolidar la familia `Conectar/` en un sistema general para:

- conectar alimentadores desde cajas, equipos, desconectores o tableros hacia
  cualquier tablero asignado;
- conectar el backbone de cajas octogonales de cualquier circuito;
- conservar el ajuste manual como herramienta distinta;
- reducir variantes visibles especializadas por nombres como TP o TCOM.

Version objetivo de esta tarea: FreeCAD 1.1.3.

## Principios confirmados

- TP, TCOM, TAA, TS, TUPS y nombres futuros son instancias del concepto
  general `TABLERO`.
- La identidad del tablero proviene de propiedades y relaciones, no de ramas
  geometricas codificadas por nombre.
- Las lineas guia son opcionales: si existen y se seleccionan se usan; si no
  existen, el motor debe crear una ruta ortogonal directa.
- La nueva logica comun debe vivir en modulos Python reutilizables; una
  `.FCMacro` no debe cargarse mediante `exec()` como biblioteca.
- Las variantes historicas se respaldan y pueden permanecer como wrappers de
  compatibilidad hasta completar la validacion funcional.

## Capacidades que deben conservarse

- seleccion de caja origen y planificacion por circuito;
- cara superior real del `Shape` y punto perteneciente a esa cara;
- distribucion de varias entradas segun conexiones reales;
- rutas guia opcionales, carriles y separacion;
- reserva de puertos y preferencia por puertos disponibles;
- rutas ortogonales, curvas, simplificacion y control de retroceso;
- actualizacion sin duplicados, limpieza controlada y trazabilidad;
- propiedades `CircuitoID`, `CajaOrigen`, `TableroDestino`, `PuertoOrigen`,
  `PuntoOrigen`, `PuntoDestino`, `CaraTablero`, `FaceIndexTablero`, `RutaJSON`,
  `EstadoConexion` y `GeneradoPor` cuando apliquen;
- Undo/Redo mediante transacciones de FreeCAD.

## Alcance minimo

Revisar y consolidar:

- `Conectar_Alimentadores_a_Tablero_Auto.FCMacro`;
- `alimentadores_backend.py`;
- `Conectar_Cajas_a_Tablero_Auto.FCMacro`;
- alimentadores TP y TCOM a cara superior;
- backbones TP y TCOM;
- `Conectar_Tableros_Cara_Superior.FCMacro`;
- `Conectar_Desconectores_HVAC_a_TP.FCMacro`;
- `Preparar_Red_TCOM_Completa.FCMacro`;
- `Ajustar_Alimentador_o_Ramal_Manual.FCMacro`;
- `ramales_backend.py`.

## Respaldo obligatorio

Antes de modificar las herramientas se debe crear:

`Conectar/Backups/consolidacion_conexiones_20260808/`

con inventario, estado previo, commit y hashes. No borrar definitivamente las
macros historicas durante esta tarea.

## Interfaz esperada

La barra normal debe tender a mostrar solamente:

- `Conectar Alimentadores`;
- `Conectar Circuito / Backbone`;
- `Ajustar Ruta`.

Las variantes reemplazadas se retiran de la barra solo despues de superar las
pruebas tecnicas. Quitar de la barra no significa borrar el archivo.

## Pruebas obligatorias

- alimentador sin guia;
- alimentador con guia;
- tableros TP, TCOM y otro codigo, usando el mismo motor;
- varias llegadas distribuidas;
- segunda ejecucion sin duplicados;
- movimiento de tablero o caja y regeneracion;
- reserva de puertos;
- backbone para circuitos TP y TCOM con el mismo motor;
- Undo/Redo;
- guardar, cerrar, reabrir y recomputar una copia de prueba.

La version actual de Puriscal puede usarse como fuente de verificacion, pero no
debe guardarse ni sobrescribirse:

`C:/Users/marco/OneDrive - Caja Costarricense de Seguro Social/2026/08-Agosto-2026/Puriscal/Puriscal 03-08-2026.FCStd`

## Documentacion final

Actualizar `RESULTADO_CODEX.md` y `REVISION_MACROS.md`. Actualizar
`HISTORIAL_CAMBIOS.md` solamente si la solucion queda tecnicamente probada y
existe evidencia suficiente de cambio aceptado.

## Resultado al 2026-08-08 18:06 CST

- respaldo con hashes: completado;
- motor Python general de alimentadores: completado;
- motor Python general de backbone: completado;
- wrappers TP/TCOM/HVAC/tablero-tablero: completados;
- guia opcional y fallback directo: probados;
- TP, TCOM, TS y TAA con el mismo motor: probados;
- puertos, cara real, distribucion, idempotencia, movimiento y Undo/Redo:
  probados;
- copia temporal de Puriscal: probada y reabierta;
- orquestador de iluminacion usando el motor comun: probado;
- barra normal reducida a tres comandos: comprobada por test;
- documento original de Puriscal: no guardado ni sobrescrito;
- validacion visual desde FreeCAD GUI por Marco: pendiente.

No actualizar `HISTORIAL_CAMBIOS.md` hasta recibir esa validacion funcional.
