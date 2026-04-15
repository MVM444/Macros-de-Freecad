# Conectar Circuitos Ramales

## Alcance

Este documento resume las reglas funcionales y los problemas recurrentes para la macro de ramales internos del circuito.

Macro objetivo:

- `Conectar_Circuitos_Ramales_Auto.FCMacro`

Este documento no cubre alimentadores al tablero.
Los alimentadores deben tratarse por separado.


## Objetivo general

La macro debe resolver solo la red interna del circuito:

- backbone entre cajas octogonales
- conexiones desde cajas octogonales a tomacorrientes
- conexiones desde cajas octogonales a apagadores cuando se habilite

No debe intentar:

- conectar al tablero
- enrutar alimentadores
- mezclar en una misma logica ramales y alimentadores

Decision de arquitectura (2026-03-26):

- separar flujo de tomacorrientes y flujo de luminarias en macros distintas para evitar regresiones cruzadas.
- `Conectar_Circuitos_Ramales_Auto.FCMacro`: circuito de tomacorrientes (y apagadores segun configuracion), sin planner de luminarias.
- `Conectar_Circuitos_Luminarias_Auto.FCMacro`: circuito de luminarias/apagadores con troncal por apagadores y distribucion por recintos.


## Reglas funcionales recurrentes

### 1. La caja octogonal es el nodo principal

- La caja octogonal es la referencia principal del ramal.
- Los dispositivos del circuito deben colgar de su caja octogonal correspondiente.
- La macro no debe priorizar una simple cercania si ya existe una relacion correcta caja-dispositivo.


### 2. Orden correcto del circuito

- El circuito debe resolverse circuito por circuito.
- Si el usuario selecciona un objeto de un circuito, debe procesarse su grupo de circuito.
- Si no hay seleccion, puede procesar todos los circuitos detectados.
- No debe mezclar varios circuitos como si fueran uno solo.


### 3. Backbone entre octogonales

- Las octogonales deben conectarse entre si completando el circuito.
- No debe saltarse cajas intermedias y crear enlaces largos irracionales.
- Si el orden del circuito ya es claro por la geometria, debe respetarse.
- Si hace falta, usar orden por perimetro del grupo para evitar saltos largos.


### 4. Conexiones a dispositivos

- Si el dispositivo tiene su caja octogonal correspondiente, debe conectarse a esa caja.
- Si falta la octogonal:
  - puede conectarse a otro dispositivo cercano que si tenga octogonal
  - solo como fallback coherente
- No debe subir a `3000 mm` y volver a bajar cuando la conexion directa local sea la correcta.


### 5. Regla de cota

- Si dos dispositivos no estan a la misma cota, no deben conectarse directamente entre si.
- En ese caso deben ir por la caja octogonal.
- La conexion dispositivo-dispositivo directa solo se admite si la cota es compatible y es un fallback razonable.


### 6. Geometria de la ruta

- La ruta debe ser ortogonal.
- No debe atravesar el centro del recinto si se puede evitar.
- Debe seguir muros o el perimetro del grupo cuando eso mejora la lectura del circuito.
- Las octogonales ya estan sobre el muro y sirven como referencia del recorrido.


### 7. Entrada correcta a la octogonal

- La tuberia debe entrar perpendicularmente al lado correcto de la octogonal.
- No debe entrar por un lado distinto de donde viene la ruta.
- No debe doblar dentro de la caja.
- No deben salir varias tuberias del mismo punto de la caja si hay puertos disponibles.


### 8. Curvas

- Debe usarse radio de curvatura de referencia:
  - `100 mm`
- Si el tramo es demasiado corto, el radio debe ajustarse automaticamente.
- Deben evitarse curvas innecesarias.
- Si dos lineas y una curva bastan, no deben crearse tres lineas.


### 9. Agrupacion en el arbol

- Las tuberias del ramal deben quedar dentro del grupo del circuito.
- No deben perder la jerarquia del proyecto.
- Deben evitar crear subgrupos paralelos absurdos.
- El destino ideal es un subgrupo del circuito, por ejemplo:
  - `Ramales_EMT`
  - o equivalente coherente con la estructura existente


### 10. Panel y persistencia

- El formulario debe seguir el estandar de FreeCAD/ElectricCR.
- Debe poder mantenerse abierto mientras el usuario selecciona objetos.
- La configuracion escrita por el usuario debe persistir.
- No debe obligar a reescribir los mismos datos en cada ejecucion.


## Problemas recurrentes

### A. Enredo general del ramal

Sintoma:

- la macro crea demasiadas conexiones o conexiones ilogicas
- el resultado no respeta la topologia del circuito

Causa probable:

- la macro esta resolviendo por cercania simple en vez de usar un plan de circuito


### B. Mezcla de todos los circuitos

Sintoma:

- parece que todos los dispositivos forman un solo circuito

Causa probable:

- el alcance se resolvio mal
- el grupo de circuito no se detecto bien


### C. Saltos largos entre cajas

Sintoma:

- una caja se conecta a otra lejana y se brinca una intermedia

Causa probable:

- orden incorrecto de octogonales
- no se uso el orden espacial/perimetral del circuito


### D. Curvas dentro de la caja

Sintoma:

- la curva se ve dentro de la octogonal
- visualmente parece que la tuberia entra por el lado incorrecto

Causa probable:

- punto final correcto, pero aproximacion geometrica incorrecta


### E. Conexion errada por caja mas cercana

Sintoma:

- el dispositivo se conecta a una caja cercana cualquiera, pero no a la correcta del circuito

Causa probable:

- se perdio la relacion `CajaOrigenKey` o la macro no la uso


## Lista minima de verificacion

Antes de dar por buena una version nueva de la macro de ramales, verificar:

1. Procesa el circuito correcto y no mezcla grupos.
2. Las cajas del circuito se enlazan en orden coherente.
3. Los dispositivos con caja se conectan a su caja.
4. Los dispositivos sin caja solo usan fallback razonable.
5. No hay curvas dentro de octogonales.
6. Las entradas a cajas son perpendiculares al lado correcto.
7. Las rutas no cruzan el recinto de forma absurda.
8. La jerarquia del arbol se mantiene.
9. La configuracion del formulario persiste.


## Prioridades para implementacion

Orden recomendado:

1. detectar bien el alcance del circuito
2. detectar bien la relacion caja-dispositivo
3. construir el plan del circuito
4. ordenar correctamente las octogonales
5. dibujar el backbone
6. dibujar las bajadas a dispositivos
7. pulir geometria de entrada y curvas


## Regla de trabajo

Si una version nueva de la macro vuelve a introducir problemas ya resueltos, no seguir agregando heuristicas locales.

Lo correcto es:

- volver al plan del circuito que ya funcionaba
- extraer solo la logica madura
- y reconstruir sobre esa base

## Estado transitorio actual

- Para recuperar el comportamiento estable mas rapido, `Conectar_Circuitos_Ramales_Auto.FCMacro` puede apoyarse temporalmente en el backend de ramales de `Conectar_Cajas_a_Tablero_Auto.FCMacro`.
- Esto es una medida pragmatica de recuperacion, no el estado final deseado.
- Si luego se quiere independencia total, el siguiente paso es copiar dentro de la macro de ramales solo las funciones maduras de la `v1` y eliminar la dependencia en tiempo de ejecucion.
- Ya existe una primera separacion tecnica: `Conectar_Circuitos_Ramales_Auto.FCMacro` consume un backend compartido `Conectar/ramales_backend.py`.
- La `v1` se deja intacta por seguridad.
- El siguiente paso de independencia real es mover funciones maduras desde la `v1` al backend compartido y luego dejar de cargar `Conectar_Cajas_a_Tablero_Auto.FCMacro` en tiempo de ejecucion.
