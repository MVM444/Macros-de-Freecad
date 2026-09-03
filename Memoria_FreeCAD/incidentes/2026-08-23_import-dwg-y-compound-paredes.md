# Importacion DWG y Compound de paredes

Fecha: 2026-08-23  
Equipo: DESKTOP-5586S7P  
FreeCAD: 1.1.3  
Workbench: FacilArquitecturaWB 0.14.2 / 2026.08.23.2

## Hallazgo 1 - separar cola MCP de operacion FreeCAD

Una llamada MCP puede agotar su tiempo sin haber ejecutado el codigo solicitado.
En este caso `rpc_server.gui_dispatch._rpc_request_queue` acumulo ocho tareas y
`_processing` permanecia falso. La causa era el guard de navegacion: Qt conservaba
internamente un boton del raton como presionado y `process_gui_tasks()` devolvia sin
procesar la cola.

Indicadores utiles:

- la traza almacenada por el codigo solicitado sigue vacia;
- el documento esperado no existe todavia;
- FreeCAD figura abierto y Windows no lo considera colgado;
- no hay proceso ODA activo;
- la cola MCP crece, pero `_processing` es falso.

Enviar eventos de liberacion de botones restauro la cola sin cerrar FreeCAD. Antes
de atribuir 90 s al DWG, medir por separado espera de despacho y tiempo interno con
`time.perf_counter()`.

## Hallazgo 2 - oraculo correcto para Compound importado

`Part Explode` por hijos no siempre reproduce lo que el usuario llama explotar.
Para `Pared_Concreto001`, el flujo exitoso real era `Draft Downgrade` con
`splitWires`, que produjo 140 objetos Edge. Seleccionar objetos `CompoundFilter`
puede volver a recorrer su `Base` por `OutList` y duplicar la fuente.

Cuando un `Part::Feature Compound` contiene paredes y columnas:

1. asignar un solo source id a todo el Compound permite que una columna compacta
   filtre bordes de paredes no relacionadas;
2. conservar cada Wire activa heuristicas `profile_axis` que pueden inventar
   espesores basados en la envolvente local;
3. descomponer virtualmente a bordes antes de contexto topologico reutiliza la ruta
   estable de pares paralelos, reconstruccion de perfiles compactos, merge y dedupe.

La descomposicion debe ser solo en memoria, conservar el objeto fuente para
metadata y excluir App::Link y estrategias especializadas. El caso validado produjo
37 ejes de muro de 150 mm y una cruz de columna de 2 lineas tanto directo como con
140 bordes, sin objetos de Explode ni espesores 428/440/700.
