# Organizacion de grupos - Requisitos recurrentes

Este documento consolida reglas recurrentes para macro de organizacion por grupos.

## Objetivo funcional

Permitir reubicar objetos seleccionados (aunque vengan de grupos distintos) hacia un grupo destino para mantener el arbol limpio y consistente.

## Reglas funcionales recurrentes

1. La macro debe aceptar seleccion mixta (objetos y grupos).
2. Si se selecciona un grupo, debe poder mover su contenido no-contenedor de forma recursiva.
3. Debe soportar:
   - mover a grupo existente
   - crear grupo nuevo y mover ahi
4. Al mover, debe poder sacar objetos de sus grupos anteriores para evitar duplicados.
5. Debe borrar grupos vacios al finalizar (al menos los afectados por el movimiento).
6. Debe conservar opcion de proteger grupos base vacios (`electrico`, `_lib`, `instancias`).
7. El selector de destino debe mostrar lista filtrada por contexto de seleccion
   (padres/ancestros/grupos relacionados), no toda la lista global por defecto.

## Criterio recurrente de iconos

Para evitar regresion de icono no visible:

1. Guardar icono junto a la macro.
2. Guardar copia del icono en `ElectricCR/icons/<carpeta_macro>/`.
3. Declarar encabezado `# Icon:` en la macro con ruta estable.
