# Conectar Cajas a Tablero v2

## Alcance

Este documento resume las solicitudes recurrentes y los problemas recurrentes reportados durante el desarrollo de:

- `Conectar_Cajas_a_Tablero_Auto.FCMacro`
- `Conectar_Cajas_a_Tablero_Auto_v2.FCMacro`

Su objetivo es evitar regresiones y servir como especificacion funcional minima para la `v2`.


## Reglas funcionales recurrentes

### 1. Origen del alimentador

- El alimentador debe salir de la caja octogonal del circuito ramal.
- La caja origen debe elegirse de forma coherente con la ruta hacia la guia y el tablero.
- No debe salir de una caja plantilla, master o caja sin circuito valido.


### 2. Rutas guia

- Las rutas guia son canales de enrutamiento.
- La macro no debe autorutear libremente por todo el edificio.
- La guia no es una referencia exacta de cada punto final.
- La guia sirve para agrupar y conducir alimentadores, no para obligar una geometria imposible.
- Puede haber varias guias.
- Cada circuito debe asignarse a la guia mas conveniente o a una seccion manualmente forzada.


### 3. Comportamiento del alimentador

- Secuencia esperada:
  - salir de la octogonal
  - llegar a la ruta guia
  - avanzar por el canal de la guia
  - llegar al tablero
  - entrar al tablero sin cruces innecesarios
- La llegada final al tablero debe ser ortogonal.
- En vista lateral no debe verse inclinada.
- Debe subir perpendicular y distribuirse perpendicularmente.
- Si el tablero usa `Top`, la llegada debe rematar con dos codos ortogonales si hace falta.


### 4. Offset y separacion

- Los alimentadores de un mismo canal deben permanecer paralelos.
- La separacion debe ser constante.
- El offset debe calcularse perpendicular a la ruta local, no con un eje global fijo `X` o `Y`.
- No se deben superponer en curvas.
- Las curvas deben verse concentricas cuando comparten el mismo giro.


### 5. Cruces

- El objetivo principal es minimizar cruces.
- Si un orden espacial evita cruces, ese orden debe preferirse.
- El orden no debe depender del arbol del documento.
- Debe priorizarse un orden monotono por canal, por seccion y por posicion espacial.
- Los cruces sobre el tablero son un problema recurrente y deben tratarse como prioridad alta.


### 6. Entrada al tablero

- No debe usarse el centro del tablero como punto unico de entrada.
- Deben poder seleccionarse caras del tablero con el mouse.
- El formulario debe mostrar claramente las caras activas.
- Si se selecciona una sola cara, todas las salidas deben usar esa cara.
- Si se seleccionan varias, solo se usan esas caras.


### 7. Cara Top del tablero

- Sobre `Top`, la distribucion debe parecerse a un tablero real.
- Debe existir una matriz de puntos sobre la tapa.
- La forma preferida reportada por el usuario es:
  - dos filas
  - intercaladas
  - con separacion suficiente para tuberias de hasta 25 mm
- No debe degradarse a una sola linea si eso empeora la geometria.
- No debe crear curvas cruzadas a nivel de `3 m` justo antes de entrar al tablero.


### 8. Secciones y guias en el tablero

- Las guias funcionan como secciones de salida del tablero.
- Debe poder ordenarse manualmente el orden de las secciones.
- Debe poder ordenarse manualmente el orden de los circuitos dentro de cada seccion.
- Debe poder moverse un circuito de `AUTO` a una guia/seccion especifica.

Convenciones recurrentes pedidas:

- primera guia en la lista = mas a la derecha
- ultima guia en la lista = mas a la izquierda
- dentro de cada seccion:
  - primer circuito = mas a la derecha
  - ultimo circuito = mas a la izquierda

Nota:

- si el tablero esta rotado, derecha e izquierda deben responder a la orientacion real del tablero, no al eje global.


### 9. Orden automatico

- Cuando no haya orden manual, la macro debe usar orden automatico coherente con la geometria.
- Debe preferirse ordenar por posicion sobre la guia o por distancia monotona a lo largo del canal.
- La guia mas cercana no siempre basta; hay que respetar tambien el lado/borde del tablero.


### 10. Backbone y conexiones internas

- El backbone entre octogonales debe seguir el perimetro del grupo cuando eso evita cruzar el recinto.
- La ruta no debe doblar dentro de la caja.
- Las conexiones deben entrar perpendicularmente por el lado correcto de la octogonal.
- No deben salir varias tuberias del mismo punto de la octogonal si hay otros puertos disponibles.


### 11. Reglas de conexion entre dispositivos

- Si dos dispositivos no estan a la misma cota, no deben conectarse directamente entre si.
- En ese caso deben conectarse a traves de la octogonal.
- Si falta una octogonal y un toma esta junto a otro toma con octogonal, puede conectarse a ese toma cercano.


### 12. UI recurrente

- El formulario debe seguir el estandar de FreeCAD usado en ElectricCR.
- Debe preferirse panel lateral no modal.
- Debe permitir seleccionar tablero, caras y rutas guia con el panel abierto.
- Debe mantener visible que tablero, caras y rutas estan activas.
- Debe ser compacto y no ocupar mas espacio del necesario.


## Problemas recurrentes

### A. Regresion de cruces en el tablero

Sintoma:

- los ramales quedan bien organizados
- pero al llegar al tablero las tuberias se cruzan

Causa probable:

- orden local correcto en la guia, pero orden inconsistente en los puntos de entrada al tablero


### B. Llegada inclinada al tablero

Sintoma:

- en vista lateral la tuberia sube inclinada

Causa probable:

- falta un remate ortogonal final
- se uso un punto correcto pero una transicion geometrica incorrecta


### C. Offset global incorrecto

Sintoma:

- las lineas se separan en rectas pero se montan o cruzan en curvas

Causa probable:

- offset aplicado en `X` o `Y` global
- offset aplicado por segmentos en lugar de a la polilinea completa


### D. Seleccion incorrecta del punto del tablero

Sintoma:

- el circuito mas a la derecha termina entrando por la izquierda, o viceversa

Causa probable:

- punto de tablero elegido por cercania global
- no se respeto el orden de la seccion
- no se respeto la orientacion real del tablero


### E. Regresion por arquitectura nueva

Sintoma:

- una macro nueva limpia vuelve a introducir problemas ya resueltos antes

Causa probable:

- la nueva arquitectura no heredo aun las reglas funcionales maduras de la version anterior


## Lista minima de verificacion para cada cambio

Antes de dar por bueno un cambio en la `v2`, verificar:

1. No aparecieron circuitos falsos como `Sin_Circuito`.
2. No se usan cajas master o plantilla como origen.
3. Los alimentadores de un mismo canal siguen paralelos.
4. Las curvas no se montan.
5. La subida al tablero no queda inclinada.
6. Las guias siguen actuando como canales y no como autoruteo libre.
7. La cara seleccionada del tablero se respeta.
8. El orden de secciones y circuitos se refleja en la tapa del tablero.
9. No reaparecen cruces sobre `Top` a nivel de `3 m`.


## Prioridades para la v2

Orden recomendado de implementacion:

1. respetar circuitos y origenes validos
2. respetar guias como canales
3. fijar orden monotono por canal
4. fijar entrada ortogonal al tablero
5. resolver separacion por offset correcto
6. resolver orden y bloques sobre `Top`
7. agregar orden manual solo despues de que lo automatico sea estable

- Alimentadores: el offset no debe salir de un eje fijo; debe derivarse de la orientacion real de la guia o seccion activa. La entrada a la octogonal debe mirar la proyeccion sobre la guia, no el siguiente vertice de la polilinea.
