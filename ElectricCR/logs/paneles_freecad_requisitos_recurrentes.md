# Requisitos Recurrentes - Paneles FreeCAD (Dock/Window)

Fecha base: 2026-03-28

## Objetivo
Evitar problemas repetitivos de UI en macros ElectricCR:
- panel que no se puede mover
- panel que no se puede desacoplar como ventana
- campos de texto/combo que no se ajustan al ancho

## Regla canonica
1. Si el flujo requiere interaccion con la vista 3D, usar panel no modal.
2. Preferir `QDockWidget` para permitir acoplar/desacoplar.
3. Mantener fallback a `QDialog` no modal si el dock falla.

## Reglas tecnicas obligatorias
1. Definir `setObjectName(...)` estable y unico por macro.
2. Habilitar features del dock:
   - `DockWidgetClosable`
   - `DockWidgetMovable`
   - `DockWidgetFloatable`
3. Permitir todas las areas de acople:
   - izquierda, derecha, arriba, abajo.
4. No fijar ancho maximo estricto del dock; solo `minimumWidth` razonable.
5. Formularios con crecimiento horizontal real:
   - `QFormLayout.AllNonFixedFieldsGrow`
   - `QSizePolicy.Expanding` en `QComboBox`, `QDoubleSpinBox`, listas.
6. Evitar ventanas modales (`exec_`) para operaciones de seleccion en 3D.
7. Persistir estado minimo del panel en preferencias:
   - flotante/acoplado
   - parametros clave de la macro.

## UX recomendada
1. Incluir accion visible para actualizar alcance/seleccion.
2. Incluir control explicito "Panel flotante (ventana)" cuando aplique.
3. Mantener textos introductorios cortos y orientados a accion.

## Checklist de verificacion
1. El panel se puede arrastrar a otra zona del main window.
2. El panel se puede convertir a ventana flotante y volver a acoplar.
3. Campos y combos se expanden al cambiar ancho del panel.
4. Cerrar/reabrir la macro conserva estado flotante esperado.
5. El panel no bloquea seleccion en vista 3D.

## Recurrente 2026-04-15: lista de seleccion sobredimensionada

Sintoma reportado:
- El cuadro/lista de elementos seleccionados ocupa casi todo el panel aunque haya solo 1-2 elementos.

Regla de UX para nuevos paneles:
1. La lista debe ajustar altura dinamicamente por cantidad de filas visibles.
2. Para 1-2 items usar altura compacta.
3. Aplicar limite maximo para que estrategias/botones no queden ocultos.

## Recurrente 2026-04-15: conexion en L se pega a cara incorrecta

Sintoma reportado:
- En reemplazo de una conexion existente, la nueva ruta en `L` puede salir por `North/South` cuando visualmente "viene del West/East".

Regla canonica para `L`/`L invertida`:
1. Si se reemplaza una conexion existente, priorizar puertos cardinales heredados (`PuertoOrigen/PuertoDestino`).
2. Si no hay metadata confiable, inferir direccion local desde la geometria de la ruta existente (vector del tramo cercano al endpoint).
3. Como fallback final, usar guia centro-a-centro y el eje principal de la estrategia (`L` normal vs `L invertida`) y cortar en cara cardinal (`N/S/E/W`).

Actualizacion aplicada 2026-04-15:
1. Para reemplazo, inferir cara por endpoint geometrico real (punto inicio/fin de la ruta vieja) y centro de cara mas cercano.
2. No forzar eje por metadata previa cuando contradice la geometria real.
3. Extender la misma logica a `snake` (preview y ejecucion), incluyendo puertos cardinales y corte en centro de cara.

## Recurrente 2026-04-15: preview difiere de ejecucion en L invertida

Sintoma reportado:
- La vista previa de `L invertida` muestra un trazo distinto al resultado final aplicado.

Regla canonica:
1. La vista previa debe calcularse con la misma funcion de jobs usada en ejecucion (`_strategy_jobs`).
2. Mantener `_preview_paths_for_strategy` solo como fallback de resiliencia.

## Recurrente 2026-04-15: puertos L cambian entre ejecuciones (efecto ping-pong)

Sintoma reportado:
- En reemplazo repetido, `L/L invertida` alterna puertos (`S/E` <-> `W/N`) aunque la seleccion no cambia.

Regla canonica:
1. Para `L`, `L invertida` y `snake`, el puerto base debe salir de la guia COM->COM (centro de masa a centro de masa).
2. En modo reemplazo, no heredar puertos de la ruta anterior para `L`, `L invertida` y `snake`; usar solo guia COM->COM.
3. `L` vs `L invertida` cambia el orden del codo, no el criterio de cara de salida.
4. En modo reemplazo, normalizar orden de endpoints (`A/B`) de forma canonica para evitar alternancia por ruta invertida.
5. En objetos rotados, no depender de nombres `PuertosJSON` para cardinales; resolver salida por cara local (`face center`) usando ejes del objeto.
6. Para robustez en piezas rotadas/no ortogonales, calcular endpoint cardinal con muestra de borde real de `Shape` en direccion mundial (no solo bounding box).
