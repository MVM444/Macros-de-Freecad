# ElectricCR - Revision macro por macro

**Proposito:** Registrar de forma persistente la revision funcional de cada macro antes de decidir si se incorpora al Workbench, permanece como macro, se fusiona, se archiva o se excluye.

**Version:** 2026-08-10, revision tecnica de Ruta critica seleccionados.

## Estado provisional despues de la consolidacion

| Herramienta | Rol | Madurez | Resultado | Decision provisional |
|---|---|---|---|---|
| `electriccr/connections/feeders.py` | NUCLEO | CANDIDATA | COMPROBADA-PARCIAL | Motor comun activo; validacion visual pendiente. |
| `electriccr/connections/backbone.py` | NUCLEO | CANDIDATA | COMPROBADA-PARCIAL | Motor comun activo; validacion visual pendiente. |
| `Conectar_Alimentadores_a_Tablero_Auto.FCMacro` | OPERATIVA | CANDIDATA | COMPROBADA-PARCIAL | Interfaz general visible. |
| `Conectar_Octogonales_por_Circuito.FCMacro` | OPERATIVA | CANDIDATA | COMPROBADA-PARCIAL | Interfaz general visible. |
| `Ajustar_Alimentador_o_Ramal_Manual.FCMacro` | OPERATIVA | ACTIVA | COMPROBADA-PARCIAL | Visible y preservada como ajuste distinto. |
| `RutaCritica_Seleccionados.FCMacro` | OPERATIVA | CANDIDATA | COMPROBADA-PARCIAL | Seleccion geometrica y radio probados tecnicamente; validacion GUI de Marco pendiente. |
| Variantes TP/TCOM de alimentador | ESPECIALIZADA | LEGACY-REEMPLAZADA | COMPROBADA-PARCIAL | Wrapper compatible, fuera de barra normal. |
| Variantes TP/TCOM de backbone | ESPECIALIZADA | LEGACY-REEMPLAZADA | COMPROBADA-PARCIAL | Wrapper compatible, fuera de barra normal. |
| `Conectar_Tableros_Cara_Superior.FCMacro` | ESPECIALIZADA | LEGACY-REEMPLAZADA | COMPROBADA-PARCIAL | Wrapper del motor de equipos. |
| `Conectar_Desconectores_HVAC_a_TP.FCMacro` | ESPECIALIZADA | LEGACY-REEMPLAZADA | COMPROBADA-PARCIAL | Wrapper de asignacion/geometria; tabla heredada pendiente de migrar. |
| `Preparar_Red_TCOM_Completa.FCMacro` | OPERATIVA | LEGACY-REEMPLAZADA | COMPROBADA-PARCIAL | Orquestador de servicios generales. |
| `Conectar_Cajas_a_Tablero_Auto.FCMacro` | NUCLEO | LEGACY-DEPENDENCIA | COMPROBADA-PARCIAL | Respaldo/compatibilidad de ramales; fuera de barra normal. |
| `alimentadores_backend.py` | NUCLEO | LEGACY-DEPENDENCIA | POR VERIFICAR | No usado por el nuevo motor; conservar mientras haya consumidores. |
| `ramales_backend.py` | NUCLEO | LEGACY-DEPENDENCIA | COMPROBADA-PARCIAL | Todavia usado por flujos de ramales no consolidados. |

`FUSIONADA` describe la funcion geometrica absorbida por los modulos comunes;
no implica que el archivo historico haya sido borrado. Todas las versiones
previas estan respaldadas bajo
`Conectar/Backups/consolidacion_conexiones_20260808/`.

## Principio

No se debe asumir que Marco recuerda que hace cada macro ni por que fue creada.

Codex debe reconstruir primero el contexto tecnico de cada herramienta utilizando codigo, documentacion, historial, pruebas y relaciones con otras macros.

El usuario aporta principalmente la validacion funcional que no puede deducirse del repositorio: uso real, resultado esperado, comportamiento visual y decisiones historicas no documentadas.

## Metodo de revision

Las macros se revisan una por una, pero siempre dentro de su familia funcional para detectar:

- duplicacion;
- solapamiento;
- reemplazos historicos;
- dependencias;
- capacidades unicas;
- intentos experimentales;
- desviaciones del objetivo original.

Antes de decidir el destino de una macro, responder como minimo:

1. Que problema pretendia resolver originalmente.
2. Que hace realmente el codigo actual.
3. Que objetos crea o modifica.
4. Que entradas requiere y que salida produce.
5. Que otras macros o modulos hacen algo parecido.
6. Si otras herramientas dependen de ella.
7. Si existe evidencia de uso real.
8. Si existe evidencia de pruebas solamente de desarrollo.
9. Si produce el resultado esperado.
10. Si tiene alguna capacidad unica que deba conservarse.
11. Si debe ser visible para el usuario final.
12. Si merece migrarse a codigo propio del Workbench.

## Tres ejes de clasificacion

Mantener los tres ejes ya adoptados:

### Rol funcional

- NUCLEO
- OPERATIVA
- SOPORTE
- ESPECIALIZADA
- MANTENIMIENTO
- SISTEMA

### Madurez

- ESTABLE
- ACTIVA
- CANDIDATA
- BETA
- REVISAR
- REVISAR-SOLAPAMIENTO
- REVISAR-INTEGRIDAD
- LEGACY-DEPENDENCIA
- LEGACY-REEMPLAZADA
- DESARROLLO
- ARCHIVADA / ARCHIVABLE

### Resultado comprobado

- COMPROBADA
- COMPROBADA-PARCIAL
- PROMETEDORA
- EXPERIMENTAL
- DESVIADA
- DUPLICADA
- INCOMPLETA
- FALLIDA
- ABANDONADA
- POR VERIFICAR
- NO APLICA

## Decision ElectricCR

Agregar una decision independiente de los tres ejes anteriores.

Valores permitidos:

- `INCORPORAR`: merece convertirse en comando o modulo propio del Workbench.
- `INCORPORAR DESPUES`: es util, pero depende de consolidacion, validacion o migraciones previas.
- `MANTENER COMO MACRO`: sigue siendo util, pero por ahora no justifica migracion.
- `EXPERIMENTAL`: se conserva en laboratorio/desarrollo y no debe formar parte del flujo productivo normal.
- `FUSIONAR`: su capacidad debe integrarse con otra herramienta antes de decidir su retiro.
- `LEGACY`: se conserva por compatibilidad o dependencia.
- `RESPALDO`: ya no debe formar parte del flujo normal, pero se conserva historicamente.
- `EXCLUIR`: no debe aparecer en ElectricCR productivo.
- `DESCARTABLE`: no aporta funcionalidad que justifique mantenerla activa; cualquier eliminacion requiere respaldo y autorizacion.
- `POR VERIFICAR`: falta evidencia suficiente para decidir.

## Regla de seguridad

El inventario previo es una preclasificacion tecnica. No equivale automaticamente a una decision definitiva de Marco.

No convertir `CANDIDATA`, `PROMETEDORA`, `REVISAR`, `POR VERIFICAR` o `REVISAR-SOLAPAMIENTO` en `INCORPORAR` sin completar la revision correspondiente.

No convertir `DUPLICADA`, `FALLIDA`, `DESVIADA`, `ABANDONADA` o `LEGACY-REEMPLAZADA` en eliminacion fisica sin respaldo y autorizacion expresa.

## Registro por herramienta

Para cada macro revisada agregar una entrada con esta estructura:

```text
### <ruta/archivo.FCMacro>

Familia:
Objetivo original:
Funcion real confirmada:
Entradas:
Salidas / objetos modificados:
Herramientas relacionadas:
Dependencias:
Uso conocido:
Pruebas conocidas:
Validacion de Marco:

Rol funcional:
Madurez:
Resultado comprobado:
Decision ElectricCR:
Destino o reemplazo:
Confianza:

Motivo de la decision:
Pendientes:
Fecha de revision:
```

## Estado de revision por familias

| Familia | Estado | Observacion |
|---|---|---|
| Areas | PENDIENTE DE REVISION DETALLADA | Primera familia recomendada para establecer el metodo definitivo. |
| Objetos | PENDIENTE | Revisar despues de Areas. |
| Iluminacion | PENDIENTE | Tiene varias herramientas ya documentadas como activas y legacy. |
| Tomacorrientes | PENDIENTE | Comparar insercion, etiquetas, organizacion y rotacion. |
| Deteccion | PENDIENTE | Revisar variantes NFPA y relacion con Areas. |
| Cajas | PENDIENTE | Revisar despues de Deteccion/Tomacorrientes. |
| Tableros / Configuracion | PENDIENTE | Revisar comandos de tablero, calculo y organizacion. |
| Conectar | AUDITORIA PARCIAL - DEPENDENCIA RECUPERADA LOCALMENTE | Reconstruidas generaciones; los dos archivos historicos fueron recuperados desde `b7d4fef`, sin commit ni prueba funcional FreeCAD. |

## Notas funcionales confirmadas por Marco

### Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro

Familia: Conectar / Alimentadores

Confirmacion de Marco:

- Esta macro es IMPORTANTE dentro del flujo de conexiones.
- No debe tratarse como una variante secundaria, descartable o reemplazada solamente por ser antigua o por no localizarse facilmente en el `main` actual.
- Antes de cualquier limpieza, migracion o fusion, Codex debe reconstruir su arquitectura completa y verificar su presencia real en la copia local, ramas, respaldos y GitHub.

Evidencia tecnica ya documentada:

- Existe `Conectar/DOCUMENTACION_ALIMENTADORES_TABLERO.md` con una documentacion extensa del flujo.
- La documentacion describe una arquitectura de tres piezas:
  1. `Conectar_Alimentadores_a_Tablero_Auto.FCMacro` como interfaz y orquestacion.
  2. `alimentadores_backend.py` como backend especializado.
  3. `Conectar_Cajas_a_Tablero_Auto.FCMacro` como backend legado que contiene parte de la logica geometrica estable reutilizada.
- La documentacion de cierre del 2026-03-19 indica un estado funcional general bueno y que la etapa se considero concluida, aunque con mejoras futuras posibles de interfaz y mantenibilidad.

Clasificacion definitiva: PENDIENTE DE REVISION DETALLADA.

Decision ElectricCR: POR VERIFICAR.

Regla especial: no eliminar, ocultar permanentemente, fusionar ni migrar esta familia hasta reconstruir y validar primero el flujo funcional completo.

Fecha de nota: 2026-08-08.

## Auditoria provisional - Alimentadores y backbone

Fecha de revision: 2026-08-08.

Alcance original de la auditoria: no se modifico, restauro, fusiono, movio ni elimino codigo. Despues de la auditoria, Marco solicito recuperar los dos archivos historicos desde `b7d4fef`. El informe comparativo y la actualizacion estan en `RESULTADO_CODEX.md`.

### `Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro`

Familia: Conectar / alimentadores.

Objetivo original: crear exclusivamente los alimentadores desde la caja principal de cada circuito hasta un tablero, usando rutas guia, caras y carriles coordinados.

Funcion real confirmada: controlador de UI y orquestacion que delegaba el planeamiento y trazado en `alimentadores_backend.py`.

Entradas: tablero, caras, rutas guia, grupos de circuito, orden manual, altura, radio, separacion e inicio de abanico.

Salidas / objetos modificados: alimentadores EMT agrupados por circuito, configuracion persistida y metadatos de ruta.

Herramientas relacionadas: v1 general, TP Top, TCOM Top y Proponer Rutas Guia.

Dependencias: directa de `alimentadores_backend.py`; indirecta de la v1 recuperada localmente.

Uso conocido: 182 ejecuciones registradas; ultima el 2026-03-28. El registro no separa produccion de depuracion.

Pruebas conocidas: documentacion de continuidad y requisitos recurrentes; sin prueba reproducida en esta auditoria.

Validacion de Marco: pendiente comparar con TP/TCOM posteriores.

Rol funcional: OPERATIVA.

Madurez: REVISAR-INTEGRIDAD.

Resultado comprobado: COMPROBADA-PARCIAL.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta sobre arquitectura y dependencia; media sobre calidad visual final.

Motivo de la decision: fue recuperada desde `b7d4fef` y conserva capacidades documentadas que no aparecen en las macros posteriores; falta validarla.

Pendientes: validar resultado historico y resolver la dependencia antes de cualquier reactivacion.

### `Conectar/alimentadores_backend.py`

Familia: Conectar / motor de alimentadores.

Objetivo original: encapsular la logica madura de alimentadores de la v1 detras de una API menor.

Funcion real confirmada: agrega carriles por guia/seccion, parches de entrada al tablero, seleccion de fuente, configuracion manual y limpieza; delega gran parte de su API a la v1.

Entradas: circuitos, dispositivos, cajas, tablero, guias y configuracion.

Salidas / objetos modificados: planes, mapas de carriles, conexiones y grupos.

Herramientas relacionadas: controlador de Alimentadores y v1.

Dependencias: carga en tiempo de ejecucion `Conectar_Cajas_a_Tablero_Auto.FCMacro` mediante `SourceFileLoader`; NetworkX es opcional.

Uso conocido: indirecto mediante la macro de alimentadores.

Pruebas conocidas: la dependencia fisica fue recuperada y coincide con el blob historico; falta ejecucion funcional en FreeCAD.

Validacion de Marco: pendiente.

Rol funcional: NUCLEO.

Madurez: LEGACY-DEPENDENCIA.

Resultado comprobado: POR VERIFICAR.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta.

Motivo de la decision: contiene logica general valiosa, pero no es autonomo.

Pendientes: validar en FreeCAD la dependencia recuperada y decidir despues entre conservarla temporalmente o extraer sus funciones.

### `Conectar/Conectar_Cajas_a_Tablero_Auto.FCMacro`

Familia: Conectar / motor historico general.

Objetivo original: generar bajantes, backbone y alimentador dentro de un unico plan de circuito.

Funcion real confirmada: clasifica objetos, planea enlaces tipados, selecciona y reserva puertos, enruta por perimetro o guia, distribuye entradas de tablero y escribe wires con claves idempotentes.

Entradas: grupos, dispositivos, cajas, tablero/ancla, caras, guias y parametros.

Salidas / objetos modificados: canalizaciones, grupos `Tuberias_EMT`, propiedades de trazabilidad y log.

Herramientas relacionadas: ambos backends, macro de ramales y Alimentadores Auto.

Dependencias: FreeCAD/Draft/Part/Qt y clasificadores auxiliares.

Uso conocido: 137 ejecuciones registradas; ultima el 2026-03-26.

Pruebas conocidas: documentada como base recuperada razonablemente estable, con problemas recurrentes de cruces y entrada al tablero.

Validacion de Marco: pendiente determinar por que se abandono el flujo.

Rol funcional: NUCLEO.

Madurez: LEGACY-DEPENDENCIA.

Resultado comprobado: COMPROBADA-PARCIAL.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta sobre capacidades; media sobre calidad visual.

Motivo de la decision: fue recuperada desde `b7d4fef` porque dos modulos presentes dependen de ella; todavia no esta en un commit nuevo.

Pendientes: comparar geometria con estrategias posteriores.

### `Conectar/Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro`

Familia: Conectar / alimentador especializado TP.

Objetivo original: caja octogonal principal -> cara superior real del tablero TP.

Funcion real confirmada: detecta `TP-001..018`, verifica una cara horizontal del `Shape`, asigna una matriz 2 x 9 y crea o actualiza un alimentador por circuito.

Entradas: tablero TP, grupos TP con cajas y parametros geometricos.

Salidas / objetos modificados: `Part::Feature`, grupo por circuito, enlaces a caja/tablero y `RutaJSON`.

Herramientas relacionadas: TCOM Top y Backbone TP la usan como biblioteca.

Dependencias: FreeCAD, Part y Qt; no depende de backend Python.

Uso conocido: sin registro en la telemetria consolidada.

Pruebas conocidas: inspeccion estatica; no se hizo validacion visual en esta auditoria.

Validacion de Marco: pendiente.

Rol funcional: ESPECIALIZADA.

Madurez: CANDIDATA.

Resultado comprobado: POR VERIFICAR.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta sobre funcion; baja sobre resultado visual.

Motivo de la decision: mejora la cara real e idempotencia, pero no reemplaza rutas guia ni orden manual.

Pendientes: comparar con la generacion anterior en un mismo caso.

### `Conectar/Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero.FCMacro`

Familia: Conectar / alimentador especializado TCOM.

Objetivo original: caja octogonal principal -> cara superior real del tablero TCOM.

Funcion real confirmada: variante TCOM-01..05 de TP Top; incorpora cajas asociadas por `CircuitosJSON`, reserva de puertos y distribucion sobre el eje mayor de la cara.

Entradas: tablero TCOM, grupos/cajas TCOM y parametros geometricos.

Salidas / objetos modificados: alimentador, grupo y metadatos equivalentes a TP.

Herramientas relacionadas: TP Top y Backbone TCOM.

Dependencias: lee, compila y ejecuta TP Top como biblioteca.

Uso conocido: sin registro en la telemetria consolidada.

Pruebas conocidas: inspeccion estatica.

Validacion de Marco: pendiente.

Rol funcional: ESPECIALIZADA.

Madurez: CANDIDATA.

Resultado comprobado: POR VERIFICAR.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta sobre funcion; baja sobre resultado visual.

Motivo de la decision: es una variante parametrizable en concepto, pero hoy depende de otra macro como modulo.

Pendientes: validar reserva de puertos y distribucion real.

### `Conectar/Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro`

Familia: Conectar / backbone TP.

Objetivo original: conectar cajas octogonales del mismo circuito TP.

Funcion real confirmada: crea un arbol de expansion minima, usa la caja alimentadora como raiz cuando existe, reserva puertos y penaliza rutas cercanas a cajas intermedias.

Entradas: grupos TP, cajas, alimentador existente opcional y parametros.

Salidas / objetos modificados: ramales caja-caja idempotentes y grupos `Ramales EMT`.

Herramientas relacionadas: TP Top, Backbone TCOM y ramales_backend.

Dependencias: carga TP Top como biblioteca.

Uso conocido: sin registro en la telemetria consolidada.

Pruebas conocidas: inspeccion estatica.

Validacion de Marco: pendiente comparar MST contra recorrido perimetral.

Rol funcional: ESPECIALIZADA.

Madurez: CANDIDATA.

Resultado comprobado: POR VERIFICAR.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta sobre algoritmo; baja sobre preferencia funcional.

Motivo de la decision: resuelve backbone, no alimentador, y usa una estrategia unica que no debe confundirse con la anterior.

Pendientes: prueba visual comparativa.

### `Conectar/ramales_backend.py`

Familia: Conectar / motor de ramales.

Objetivo original: separar la UI de ramales del planificador estable de la v1.

Funcion real confirmada: agrega planes de tomas/iluminacion, orden por recintos y comprobaciones de troncal, pero delega primitivas fundamentales a la v1.

Entradas: grupo, dispositivos, cajas, configuracion, puertos y grupo destino.

Salidas / objetos modificados: plan tipado y conexiones de ramal.

Herramientas relacionadas: `Conectar_Circuitos_Ramales_Auto.FCMacro`, flujo de luminarias y v1.

Dependencias: carga la v1 mediante `SourceFileLoader`.

Uso conocido: indirecto mediante macros de ramales/luminarias.

Pruebas conocidas: la dependencia recuperada coincide con el blob historico; ejecucion funcional pendiente.

Validacion de Marco: pendiente.

Rol funcional: NUCLEO.

Madurez: LEGACY-DEPENDENCIA.

Resultado comprobado: POR VERIFICAR.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta.

Motivo de la decision: la extraccion quedo a medio camino y la dependencia requerida fue eliminada.

Pendientes: preservar plan de recintos, controles de troncal y reglas de puertos al resolver independencia.

### `Conectar/Conectar_Circuitos_Ramales_Auto.FCMacro`

Familia: Conectar / ramales operativos.

Objetivo original: red interna del circuito sin alimentador al tablero.

Funcion real confirmada: su flujo principal usa `ramales_backend.py`; conserva ademas funciones locales solapadas de plan, perimetro y creacion de wires.

Entradas: seleccion o todos los grupos detectados y configuracion persistida.

Salidas / objetos modificados: ramales EMT dentro del circuito.

Herramientas relacionadas: ramales_backend, v1 y macro separada de luminarias.

Dependencias: backend Python y, por transitividad, v1 recuperada localmente.

Uso conocido: documentacion registra recuperacion temporal del motor v1.

Pruebas conocidas: resultado historico parcial; flujo limpio actual roto por dependencia.

Validacion de Marco: pendiente.

Rol funcional: OPERATIVA.

Madurez: REVISAR-INTEGRIDAD.

Resultado comprobado: COMPROBADA-PARCIAL.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta.

Motivo de la decision: separa correctamente el problema funcional, pero no es reconstruible desde `main`.

Pendientes: determinar que implementacion local es residual y cual debe preservarse.

### `Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro`

Familia: Conectar / ajuste manual.

Objetivo original: corregir localmente una ruta existente conservando el resto.

Funcion real confirmada: identifica ruta/objetivo, conserva tramos, evita zigzag/backtracking, respeta salida perpendicular y ajusta radio.

Entradas: ruta y referencia geometrica seleccionadas.

Salidas / objetos modificados: `Points` o `Shape` y radio de la ruta existente.

Herramientas relacionadas: todos los generadores de alimentadores y ramales.

Dependencias: FreeCAD/Part/GUI; sin backend externo.

Uso conocido: 100 ejecuciones hasta el 2026-03-26; notas registran un resultado aprobado visualmente por Marco.

Pruebas conocidas: evidencia historica de continuidad; no se repitio prueba GUI en esta auditoria.

Validacion de Marco: confirmacion actual pendiente.

Rol funcional: OPERATIVA.

Madurez: ACTIVA.

Resultado comprobado: COMPROBADA-PARCIAL.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: alta sobre codigo; media sobre comportamiento actual.

Motivo de la decision: contiene capacidades unicas; puede dejar metadatos geometricos desactualizados.

Pendientes: validar y definir sincronizacion de `RutaJSON`/extremos en una etapa funcional posterior.

### `Conectar/Proponer_Rutas_Guia_Auto.FCMacro`

Familia: Conectar / infraestructura auxiliar.

Objetivo original: proponer rutas guia a partir del plano de trabajo, areas, cajas y tableros.

Funcion real confirmada: genera ejes de pasillo/area, rutas hacia tablero y rutas representativas por circuito en un grupo propio con metadatos.

Entradas: seleccion, areas, cajas, tableros y plano de trabajo.

Salidas / objetos modificados: Draft Wires de guia 2D/3D y grupo `Rutas_Guia_Propuestas`.

Herramientas relacionadas: generacion anterior de alimentadores.

Dependencias: FreeCAD, Draft y GUI.

Uso conocido: no analizado cuantitativamente en esta auditoria.

Pruebas conocidas: inspeccion estatica.

Validacion de Marco: pendiente.

Rol funcional: SOPORTE.

Madurez: CANDIDATA.

Resultado comprobado: POR VERIFICAR.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: no decidido.

Confianza: media.

Motivo de la decision: resuelve infraestructura auxiliar, no debe mezclarse con el motor de alimentadores.

Pendientes: validar si las guias propuestas coinciden con las usadas en proyectos reales.

### `Conectar/RutaCritica_Seleccionados.FCMacro`

Familia: Conectar / medicion y rutas criticas ad hoc.

Objetivo original: crear rutas ortogonales independientes desde el primer
elemento seleccionado hacia todos los destinos seleccionados.

Funcion real confirmada: usa cada seleccion geometrica de `SelectionEx` como
endpoint; conserva caras, aristas y vertices distintos del mismo objeto;
crea Draft Wires a una altura Z comun y aplica un radio editable limitado por
la longitud disponible.

Entradas: objetos completos, caras, vertices, aristas/puntos seleccionados,
altura de ruta y radio de curva.

Salidas / objetos modificados: Draft Wires agrupados bajo `Conexiones`, con
metadatos de origen, destino, puntos, altura y radios.

Herramientas relacionadas: `medir_distancia_y_dibujar_ruta.FCMacro`,
`Ajustar_Alimentador_o_Ramal_Manual.FCMacro` y `selection_geometry.py`.

Dependencias: FreeCAD, FreeCADGui, Draft y Qt; conserva la carga historica de
la macro base. La logica nueva compartida vive en un modulo Python.

Uso conocido: la herramienta previa fue considerada util por Marco; no se
uso el registro cuantitativo como prueba de calidad.

Pruebas conocidas: smoke test en FreeCAD 1.1.3 con seleccion simulada,
geometria Part/Draft real, mismo objeto, multiples destinos, radios,
metadatos, repeticion, Undo/Redo y reapertura.

Validacion de Marco: pendiente con seleccion real de la GUI y resultado
visual en un documento de trabajo.

Rol funcional: OPERATIVA.

Madurez: CANDIDATA.

Resultado comprobado: COMPROBADA-PARCIAL.

Decision ElectricCR: POR VERIFICAR.

Destino o reemplazo: mejora la macro existente; no crea ni reemplaza otra
herramienta especializada.

Confianza: alta sobre la logica y pruebas tecnicas; media sobre el flujo GUI
hasta la validacion de Marco.

Motivo de la decision: las limitaciones tecnicas originales fueron
reproducidas y corregidas, pero el criterio visual y el orden de seleccion
real requieren prueba funcional.

Pendientes: ejecutar los casos GUI registrados en
`MEJORAS_PENDIENTES.md`.

Fecha de revision: 2026-08-10.

## Revision provisional - legibilidad de Registrar acometida

Hecho tecnico confirmado: el popup de `QComboBox` dentro del Task Panel Qt6
puede no heredar el QSS de `AcometidaRoot`. La macro aplica ahora el estilo
claro directamente a cada vista popup nativa. Prueba renderizada con temas
oscuro/claro y reparentado en `QDockWidget`: correcta. Clasificacion
provisional: OPERATIVA / ACTIVA / COMPROBADA-PARCIAL, pendiente de validacion
en la interfaz real de Marco.

## Revision provisional - centro circular en RutaCritica Seleccionados

Hecho tecnico confirmado: `RutaCritica_Seleccionados.FCMacro`, mediante
`selection_geometry.py`, usa ahora el centro geometrico de una arista circular
o arco aunque el clic ocurra sobre la circunferencia. El endpoint queda marcado
como `CIRCLE_CENTER`. La suite completa paso en FreeCAD 1.1.3; validacion visual
en un proyecto real pendiente. Clasificacion provisional: ACTIVA / PRUEBA
TECNICA / POR VERIFICAR VISUALMENTE.

## Revision provisional - RectFromBoundaryLines con caras BIM

| Herramienta | Rol funcional | Madurez | Resultado comprobado | Decision ElectricCR provisional |
|---|---|---|---|---|
| `Areas/RectFromBoundaryLines.FCMacro` | Creacion manual de areas rectangulares desde limites | ACTIVA | PRUEBA TECNICA EN FREECAD 1.1.3 | POR VERIFICAR VISUALMENTE |

Hechos confirmados: mantiene el calculo anterior desde aristas, reconoce caras
de muros Arch/BIM, proyecta caras verticales, resuelve una cara horizontal por
el borde mas cercano al clic y conserva enlaces `FA_SourceWalls`. La prueba
uso muros Arch reales, Undo/Redo y guardar/reabrir temporal; no constituye aun
aprobacion visual en un proyecto real.

## Registro de decisiones confirmadas

## Revision provisional - analisis rectangular desde muros BIM

| Herramienta | Rol funcional | Madurez | Resultado comprobado | Decision ElectricCR provisional |
|---|---|---|---|---|
| `Xcluidos/Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` | Lanzador historico de analisis rectangular | ARCHIVADA / ARCHIVABLE | El motor reusable permanece probado | RESPALDO |

Hechos confirmados: el lanzador anterior apuntaba fuera del repositorio. La
implementacion historica era una interfaz de 1961 bytes que delegaba en
`CrearAnalisisAreasRectangulares.FCMacro` de 28666 bytes. El motor recuperado
mantiene cuatro modos de inferencia, rectangulos Draft, rotulos,
`FA_RectangularAreas`, `Spreadsheet_Analisis_Areas` y metadatos ElectricCR. La
logica reusable vive ahora en
`FacilArquitecturaWB/core/rectangular_area_analysis.py`; el lanzador se
conserva solo como respaldo y ya no se registra. No se reemplaza el flujo
poligonal ni se crea `ArchSpace`.

Todavia no asumir decisiones definitivas solamente a partir del inventario general.

Las decisiones se agregaran aqui conforme Marco, GPT y Codex revisen cada herramienta con evidencia suficiente.

## Revision provisional - Panel de macros ElectricCR 2026-08-12

| Herramienta | Rol funcional | Madurez | Resultado comprobado | Decision ElectricCR provisional |
|---|---|---|---|---|
| `ElectricCR/commands/macro_launcher.py` | Lanzador y diagnostico de comandos de macros | ACTIVA | COMPROBADA TECNICAMENTE y validada visualmente en MCP | MANTENER |
| `ElectricCR/commands/macros.py` | Registro y fuente de metadatos de macros | ACTIVA | COMPROBADA TECNICAMENTE con 122 registros simulados | MANTENER / POR VERIFICAR |
| `ElectricCR/catalog.py` | Catalogo JSON/Markdown y revision manual | ACTIVA | COMPROBADA TECNICAMENTE y validada visualmente en MCP | MANTENER |

Hechos confirmados: el panel consume los metadatos del registro de comandos,
reutiliza `usage_log.py`, persiste preferencias con `QSettings` y clasifica
`Rayo.svg` como `REVISAR`, no como error. El modo diagnostico distingue
`OK`, `REVISAR` y `ERROR`. La validacion visual MCP mostro 12 grupos, 122
herramientas, filtros, detalles, botones y modo diagnostico. La captura minima
anterior fue causada por la prueba segura, que reemplazo temporalmente
`_MACRO_GROUPS` con un grupo de prueba; no fue una perdida de metadatos.

## Revision provisional - Panel Fase 2 2026-08-12

El catalogo contiene 192 entradas: 122 activas y 70 historicas no activas.
La fuente Excel `Inventario_Clasificacion_ElectricCR_2026-08-08.xlsx` no estaba
disponible en la copia local revisada; por eso no se inventaron clasificaciones
historicas desde esa fuente. Las descripciones encontradas provienen de
metadatos oficiales/encabezados de 69 macros; las restantes muestran
explicitamente `Sin descripcion`.

La persistencia de comentarios, estado manual y decision utiliza escritura
atomica en `ElectricCR/data/macros_catalog.json`; el Markdown se regenera desde
ese JSON. Los conteos previos se conservan como `historical_count`, mientras
las nuevas ejecuciones se separan en `real_count` y `test_count`. El panel
mantiene las funciones de la Fase 1 y agrega filtros, historicas,
Contraer/Expandir y Probar.

Revision posterior: se corrigio el guardado de comentarios durante
`currentItemChanged` para usar el elemento anterior; se verifico que el texto
no pasa a la herramienta siguiente. Tambien se cachearon filas, estadisticas,
recursos de comandos y catalogo para evitar reconstrucciones por cada tecla.

## Revision provisional - Integracion de descripciones GPT 2026-08-12

La fuente `ElectricCR/MACROS_DESCRIPCIONES_GPT.json` contiene 192 entradas y
se integro por la ruta estable `ruta`. El resultado conserva 192
descripciones: 133 reemplazaron campos vacios o genericos y 59 descripciones
locales concretas se preservaron. En 36 entradas la descripcion local difiere
de la propuesta GPT; la alternativa se guardo para revision sin sobrescribir
el texto local.

La procedencia queda registrada en `fuente_descripcion` y
`confianza_descripcion` (ademas de aliases internos para el Panel). La
integracion no cambio comentarios, estado manual, decision ni los archivos de
estadisticas de uso. El Panel incorpora la descripcion a la busqueda, al
detalle y al diagnostico copiable. Resultado provisional: **COMPROBADA /
VALIDADA_MCP / VALIDADA_VISUALMENTE**; decision: **MANTENER**.

## Relacion con el inventario

El inventario externo contiene una clasificacion amplia de herramientas y sirve para priorizar la auditoria.

`REVISION_MACROS.md` es el registro de decisiones funcionales confirmadas durante la depuracion y migracion.

Cuando una decision se confirme:

1. actualizar esta ficha;
2. actualizar el inventario cuando corresponda;
3. actualizar `MAPA_WORKBENCH.md` si cambia la arquitectura o el flujo principal;
4. actualizar `RESULTADO_CODEX.md` si la decision forma parte de una tarea activa;
5. actualizar `HISTORIAL_CAMBIOS.md` solamente cuando exista un cambio funcional aceptado.

## Regla para Codex al comenzar una revision

Antes de preguntarle a Marco que hace una macro, Codex debe inspeccionarla y presentar un resumen breve con esta forma:

```text
Lo que puedo confirmar por el codigo:
- ...

Herramientas relacionadas encontradas:
- ...

Lo que todavia no puedo saber por el repositorio:
- ...

Necesito de Marco solamente confirmar:
- uso real;
- resultado esperado;
- si existe alguna razon historica no documentada para conservarla.
```

El objetivo es reducir la carga de memoria del usuario y convertir el repositorio en la memoria operativa del proyecto.

## Revision provisional - limpieza de interfaz ElectricCR 2026-08-12

| Herramienta | Rol funcional | Madurez | Resultado comprobado | Decision ElectricCR provisional |
|---|---|---|---|---|
| `Tomacorrientes/Ordenar_Tomas_XY.FCMacro` | Operativa de ordenamiento de tomas | ACTIVA | POR VERIFICAR tras reubicacion | MANTENER COMO MACRO |
| `Tomacorrientes/Ordenar_Tomas_XY_Horario.FCMacro` | Operativa de ordenamiento horario de tomas | ACTIVA | POR VERIFICAR tras reubicacion | MANTENER COMO MACRO |
| `Objetos/Habilitar_Transform_en_Links_Dispositivos.FCMacro` | Mantenimiento generico de Links | ACTIVA | COMPROBADA-PARCIAL antes del cambio de icono | MANTENER COMO MACRO |
| `Configuracion del proyecto/Asignar_Tableros_y_Circuitos.FCMacro` | Configuracion de asignacion de red | ACTIVA | POR VERIFICAR visualmente | MANTENER COMO MACRO |
| `Objetos/Alinear.FCMacro` | Soporte de alineacion generica | ACTIVA | POR VERIFICAR | POR VERIFICAR |
| `Xcluidos/Objetos/HVAC_Etiqueta_Libre.FCMacro` | Herramienta HVAC especializada | ARCHIVADA / ARCHIVABLE | POR VERIFICAR | RESPALDO |
| `Xcluidos/Areas/actualizar_rectangulos_con_spreadsheet().FCMacro` | Herramienta auxiliar de areas | ARCHIVADA / ARCHIVABLE | POR VERIFICAR | RESPALDO |
| `Xcluidos/Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` | Lanzador historico de areas rectangulares | ARCHIVADA / ARCHIVABLE | El motor reusable permanece probado | RESPALDO |
| `Xcluidos/Cajas/CajaEMT.FCMacro` | Generador legacy de caja EMT | ARCHIVADA / ARCHIVABLE | POR VERIFICAR | RESPALDO |

Hechos de organizacion confirmados:

- Las dos macros de ordenar tomas ya no se registran bajo `Objetos`; el escaner
  las encuentra solamente bajo `Tomacorrientes`.
- `Xcluidos` esta excluido del escaneo normal de `ElectricCR/commands/macros.py`.
- No se retiro `FacilArquitecturaWB/core/rectangular_area_analysis.py` ni la
  implementacion moderna `ElectricCR/electriccr/features/caja_emt_octogonal.py`.
- `Alinear` conserva deliberadamente `Rayo.svg`: reutilizar
  `MEPWorkbenchCR/resources/icons/hvac_align.svg` exigiria una dependencia o
  copia no justificada por esta tarea.
- Las referencias de uso en logs se conservaron como evidencia historica y no
  se interpretan como prueba de madurez.
