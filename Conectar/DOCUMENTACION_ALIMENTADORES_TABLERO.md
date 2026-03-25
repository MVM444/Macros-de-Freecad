# Documentacion de la macro `Conectar_Alimentadores_a_Tablero_Auto`

Fecha de cierre de esta etapa: 2026-03-19

## 1. Objetivo del documento

Este documento deja trazabilidad tecnica y funcional de la macro de alimentadores a tablero, para poder:

- retomar el trabajo en otra sesion con Codex
- permitir que otra persona entienda el estado real del proyecto
- reducir perdida de contexto despues de una semana de iteraciones
- dejar claro que partes estan estables, cuales son provisionales y cuales quedan pendientes

No es un resumen corto. Es una documentacion de continuidad.


## 2. Alcance de la macro

La macro `Conectar_Alimentadores_a_Tablero_Auto.FCMacro` esta dedicada al enrutamiento de alimentadores desde cajas octogonales de circuitos hacia un tablero electrico.

El flujo general es:

1. detectar el tablero y las caras activas
2. detectar rutas guia
3. construir un plan por circuito
4. asignar carriles globales y por guia
5. calcular el punto de entrada sobre la cara del tablero
6. generar el alimentador
7. agrupar el resultado bajo el grupo del circuito


## 3. Estado actual al cierre de esta etapa

Estado funcional general: bueno.

Lo que quedo razonablemente bien:

- la macro ya genera alimentadores de forma consistente
- el reparto sobre la cara `Top` del tablero mejoro mucho respecto al estado inicial
- el caso donde una linea "se devolvia" hacia el tablero fue corregido
- la linea central del abanico superior mejoro de manera importante
- la guia lateral izquierda volvió a rematar hacia abajo, no hacia el borde lateral del tablero
- existe un respaldo congelado del estado actual

Lo que sigue siendo mejorable, pero no bloquea este cierre:

- la estetica del formulario aun no esta al nivel deseado
- la interfaz sigue siendo funcional antes que pulida
- la logica de limpieza/reutilizacion de grupos fue reforzada, pero conviene revalidarla cuando se retome trabajo funcional pesado
- la ventana de `Salidas de tuberia del tablero` quedo fuera del flujo principal, pero el codigo permanece

Decision tomada al cierre:

- se da por concluida esta etapa
- los siguientes cambios fuertes ya deberian ser sobre interfaz, mantenibilidad o refinamiento fino


## 4. Archivos principales involucrados

### 4.1 Archivo principal de interfaz y orquestacion

- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro)

Responsabilidades:

- construir el formulario
- leer y guardar preferencias
- detectar tablero, caras y rutas guia
- construir configuracion de ejecucion
- ordenar circuitos y secciones
- pedir al backend el plan y los carriles
- ejecutar la creacion de alimentadores


### 4.2 Backend de alimentadores

- [alimentadores_backend.py](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py)

Responsabilidades:

- encapsular la logica estable heredada
- parchear comportamiento del backend v1 en puntos concretos
- distribuir carriles y entradas sobre el tablero
- manejar grupos, limpieza y utilidades de enrutamiento
- exponer una API mas pequena para la macro dedicada a alimentadores


### 4.3 Backend legado reutilizado

- [Conectar_Cajas_a_Tablero_Auto.FCMacro](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Cajas_a_Tablero_Auto.FCMacro)

Responsabilidades:

- contiene la logica original mas estable de rutas y conexion
- provee funciones internas reutilizadas por el backend nuevo
- sigue siendo la base mecanica del enrutamiento real


## 5. Arquitectura actual

La macro actual no reescribe desde cero el algoritmo.

La arquitectura real es:

1. `Conectar_Alimentadores_a_Tablero_Auto.FCMacro`
2. `alimentadores_backend.py`
3. `Conectar_Cajas_a_Tablero_Auto.FCMacro`

Eso significa:

- la macro visible es un controlador
- el backend nuevo hace de capa intermedia
- el backend legado sigue ejecutando la parte geometrica profunda

Ventajas de esta arquitectura:

- no se rompio la logica estable de rutas mas de lo necesario
- se pudieron hacer muchos ajustes sin duplicar todo el algoritmo
- la macro de alimentadores se mantuvo separada del flujo completo de cajas

Costo de esta arquitectura:

- hay bastante acoplamiento con funciones internas del backend legado
- hay parches contextuales en vez de un redisenio total
- leer el flujo completo requiere revisar los tres archivos


## 6. Cambio conceptual mas importante de esta semana

El problema central no era solo "dibujar una ruta". El problema era alinear bien tres cosas:

- la posicion real del circuito respecto a la ruta guia
- la distribucion interna sobre la cara del tablero
- el abanico final que remata sobre el tablero sin cruces innecesarios

La solucion que termino funcionando mejor fue esta:

- dejar de tratar el punto de tablero como algo totalmente fijo
- calcular mejor el arreglo global de entradas sobre la cara `Top`
- desplazar ese arreglo para que la linea central o priorizada del grupo quede mejor alineada con la llegada real
- reservar tratamiento recto solo donde de verdad tenga sentido

En otras palabras:

- se paso de "forzar la ruta para llegar a puntos fijos"
- a "mover inteligentemente los puntos de tablero para que la ruta quede natural"


## 7. Problemas principales atendidos durante esta etapa

### 7.1 Cruces en el abanico final hacia el tablero

Problema:

- varias lineas se cruzaban en el punto final donde todas convergian sobre `Top`

Acciones tomadas:

- ajuste de carriles por guia
- inversion de `lane_eff` para casos concretos de flujo
- reparto mas amplio del array sobre el tablero
- anclaje del arreglo global respecto a una linea priorizada
- desplazamiento de puntos de entrada sobre el tablero
- parametro `Inicio abanico tablero`

Resultado:

- mejora clara respecto al estado inicial
- el comportamiento final ya es usable


### 7.2 Linea que se devolvia antes de entrar al tablero

Problema:

- en el caso `TP-15 Archivo`, la ruta llegaba al final de la guia y luego devolvia hacia el tablero

Acciones tomadas:

- clamp del remate final para que no se pasara del punto util
- mejor control del remate y del eje final

Resultado:

- el caso dejo de devolverse


### 7.3 Uso incompleto del ancho del tablero

Problema:

- las entradas sobre `Top` se agrupaban demasiado y se desaprovechaba el ancho util

Acciones tomadas:

- reduccion de margenes
- distribucion mas global sobre toda la cara
- reparto por bloque completo, no solo por pequenos racimos de seccion
- anclaje respecto a linea priorizada

Resultado:

- mejor uso del ancho
- todavia mejorable, pero ya muy superior al inicio


### 7.4 Grupo lateral izquierdo mal resuelto

Problema:

- la guia izquierda termino en algunas iteraciones pegandose al borde del tablero o saliendo lateralmente

Acciones tomadas:

- se forzo el remate de `Top/Bottom` por eje `Y`
- se quito el remate lateral no deseado

Resultado:

- la guia izquierda volvio a rematar hacia abajo


### 7.5 Duplicacion de grupos `Alimentadores_*`

Problema:

- en multiples pruebas se acumulaban grupos nuevos dentro del arbol

Acciones tomadas:

- se creo logica de reutilizacion de grupos por etiqueta y nombre esperado
- se revisaron descendientes y grupos del documento, no solo hijos directos
- se agrego limpieza de grupos generados vacios antes y despues de recalcular

Archivos clave:

- [alimentadores_backend.py:667](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:667)
- [alimentadores_backend.py:704](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:704)
- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2386](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2386)
- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2596](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2596)

Estado al cierre:

- mejorado
- recomendable volver a observarlo cuando se hagan pruebas funcionales intensas


## 8. Cambios de interfaz realizados

### 8.1 Seccion `Salidas de tuberia del tablero`

La idea fue buena, pero por ahora no es necesaria como parte del flujo normal.

Decision tomada:

- quitarla del formulario principal
- mantener el codigo por si en el futuro se desea recuperar

Esto permite:

- simplificar el flujo para el usuario
- reducir ruido en la interfaz
- mantener la posibilidad de rescatar la funcionalidad luego


### 8.2 Guia para el usuario

La pestana que antes estaba vacia o casi sin valor fue convertida en una guia rapida.

Referencias:

- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:189](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:189)
- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2128](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2128)


### 8.3 Estilo visual

Se hicieron varios intentos de modernizacion del panel.

Estado al cierre:

- mejor que el estado inicial improvisado
- aun no esta al nivel deseado
- el usuario indico correctamente que todavia no se ve del todo bien

Conclusiones sobre UI:

- la apariencia final no conviene seguirla afinando a mano con puro Python y `stylesheet`
- lo correcto para una futura iteracion es usar `Qt Designer` y un archivo `.ui`


## 9. Parametros relevantes introducidos o consolidados

### 9.1 `Inicio abanico tablero`

Parametro visible para el usuario.

Valor por defecto:

- `700 mm`

Objetivo:

- controlar desde que distancia previa al tablero comienza el abanico final

Referencia:

- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:52](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:52)


### 9.2 `board_entry_x` y `board_entry_y`

No son parametros de UI directa. Son datos internos por circuito.

Objetivo:

- permitir que el backend reciba un punto de entrada real sobre el tablero
- distribuir el array del tablero de forma mas inteligente

Referencias:

- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2432](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2432)
- [alimentadores_backend.py:793](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:793)


### 9.3 `guide_straight_priority`

Objetivo:

- definir que linea dentro de una guia puede tener prioridad para una bajada mas recta

Referencias:

- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2431](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2431)
- [alimentadores_backend.py:797](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:797)


## 10. Funciones y puntos de codigo importantes

### 10.1 Macro principal

Formulario:

- `FormularioAlimentadores.run()`
- punto de arranque de UI y preferencias

Configuracion backend:

- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2290](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2290)

Ejecucion:

- `ejecutar_alimentadores(...)`

Conexion real por circuito:

- [Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2549](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Alimentadores_a_Tablero_Auto.FCMacro:2549)


### 10.2 Backend nuevo

Reutilizacion/limpieza de grupos:

- [alimentadores_backend.py:667](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:667)
- [alimentadores_backend.py:704](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:704)

Borrado de alimentadores previos:

- [alimentadores_backend.py:753](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:753)

Wrapper de conexion:

- [alimentadores_backend.py:761](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:761)

Parche de remate `Top/Bottom`:

- [alimentadores_backend.py:1270](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:1270)

Asignacion de prioridad recta y puntos de tablero:

- [alimentadores_backend.py:1931](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:1931)
- [alimentadores_backend.py:2075](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\alimentadores_backend.py:2075)


### 10.3 Backend legado

Borrado de alimentadores previos:

- [Conectar_Cajas_a_Tablero_Auto.FCMacro:3811](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Cajas_a_Tablero_Auto.FCMacro:3811)

Conexion interna real:

- [Conectar_Cajas_a_Tablero_Auto.FCMacro:4439](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Conectar_Cajas_a_Tablero_Auto.FCMacro:4439)


## 11. Flujo recomendado de prueba manual

Cuando se retome trabajo sobre esta macro, el flujo sugerido es:

1. abrir el documento de prueba
2. abrir la macro `Conectar_Alimentadores_a_Tablero_Auto`
3. seleccionar el tablero y la cara `Top`
4. cargar o seleccionar las rutas guia
5. ajustar:
   - `Nivel ruta`
   - `Radio curvatura`
   - `Separacion circuitos`
   - `Inicio abanico tablero`
6. usar `Actualizar alimentadores`
7. revisar:
   - alineacion sobre el tablero
   - cruces del abanico final
   - remate de la guia izquierda
   - grupos `Alimentadores_*` en el arbol


## 12. Logs utiles

Prefijos de log importantes:

- `[ALIM_AUTO]`
- `[ALIM_BACKEND]`
- `[CAJA_TAB_AUTO][DEBUG]`

Lineas especialmente utiles:

- `Carriles globales por guia`
- `Vector de offset`
- `Remate tablero en banda`
- `Orden Top/Bottom reajustado`
- `Proceso terminado`

Si se necesita diagnostico posterior, esas lineas siguen siendo las mas utiles.


## 13. Respaldo creado

Se genero un respaldo de este punto de trabajo en:

- [respaldo_alimentadores_20260319_114918.zip](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Backups\respaldo_alimentadores_20260319_114918.zip)
- [respaldo_alimentadores_20260319_114918.sha256.txt](c:\Users\marco\OneDrive - Caja Costarricense de Seguro Social\Documentos\FreeCAD\Macros\Macros-de-Freecad\Conectar\Backups\respaldo_alimentadores_20260319_114918.sha256.txt)

Incluye:

- `alimentadores_backend.py`
- `Conectar_Alimentadores_a_Tablero_Auto.FCMacro`
- `Conectar_Cajas_a_Tablero_Auto.FCMacro`

Ese respaldo se dejo como punto congelado para poder volver atras si hace falta.


## 14. Que quedo pendiente a futuro

### 14.1 Interfaz

Pendiente recomendado:

- migrar el formulario a `Qt Designer` y archivo `.ui`

Razon:

- la estetica ya esta forzando demasiado trabajo manual en Python
- `Qt Designer` permitiria ajustar mejor tamanos, layout, espaciados y proporcionalidad


### 14.2 Tabla manual de salidas del tablero

No se elimina del todo.

Queda como funcionalidad potencial futura, por si se decide volver a una asignacion mas manual del array del tablero.


### 14.3 Afinado fino del abanico final

Aunque quedo en buen estado, siempre podria mejorarse:

- mejor distribucion para casos muy densos
- tolerancias por guia
- reglas distintas por cantidad de circuitos


### 14.4 Limpieza de grupos

La limpieza fue reforzada, pero conviene seguirla observando en futuras sesiones para asegurarse de que:

- no aparezcan grupos vacios acumulados
- no queden grupos huerfanos
- no se mezclen objetos generados manualmente con automaticos


## 15. Recomendaciones para Codex cuando retome este modulo

### 15.1 No empezar rehaciendo el algoritmo

La logica ya mejoro bastante. No conviene:

- reescribir todo desde cero
- desmontar el wrapper actual sin necesidad

Conviene:

- hacer cambios pequenos y verificables
- mantener el backend legado como base mientras siga funcionando


### 15.2 UI: separar apariencia de logica

La proxima iteracion seria mejor si:

- el formulario vive en `.ui`
- la macro solo conecta eventos y datos


### 15.3 Antes de tocar distribucion del tablero

Revisar primero:

- `board_entry_x`
- `board_entry_y`
- `guide_straight_priority`
- `board_align_distance`
- la construccion de `lane_meta_map`

Esos son los puntos clave del comportamiento actual.


### 15.4 Antes de tocar grupos

Revisar:

- `ensure_unique_child_group`
- `cleanup_empty_generated_groups`
- `delete_autoroute_feeders`

No conviene crear otra tercera estrategia distinta sin entender esas tres capas.


## 16. Recomendaciones para cualquier persona que lea esto

Si el objetivo es usar la macro:

- el estado actual ya sirve para trabajo real con supervision visual

Si el objetivo es desarrollarla:

- lea primero este documento
- luego revise `Conectar_Alimentadores_a_Tablero_Auto.FCMacro`
- luego `alimentadores_backend.py`
- y solo despues el backend legado

Si el objetivo es mejorar la interfaz:

- no siga apilando `stylesheet` sin un diseno mas claro
- use `Qt Designer`


## 17. Conclusiones de esta etapa

Esta semana de trabajo dejo tres logros reales:

1. la macro paso de un estado inestable a un estado funcional mucho mas controlado
2. el comportamiento sobre el tablero mejoro de forma importante
3. ahora existe documentacion, respaldo y una base clara para retomar

La macro no esta "terminada para siempre".
Pero si quedo en un punto serio, usable y retomable sin perder el contexto.

