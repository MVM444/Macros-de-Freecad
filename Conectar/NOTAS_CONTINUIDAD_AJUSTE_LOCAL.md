# Notas de continuidad - Ajuste local de alimentador/ramal

Fecha: 2026-03-19

Macro principal:
- `Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro`

Estado actual:
- El resultado mas reciente fue aceptable por el usuario ("este resultado me gusto").
- Se deja esta parte pausada para continuar en otra ocasion.

Cambios tecnicos aplicados en esta iteracion:
- Seleccion robusta de ruta vs caja, sin depender del orden de seleccion.
- Salida perpendicular desde caja (octogonal/rectangular) al iniciar reruteo.
- Preservacion de tramo cercano a tablero con bloqueos de prefijo/sufijo.
- Preferencia por corte en tramo (en vez de pegar siempre en vertice fijo).
- Penalizacion fuerte de zigzag tipo escalera `A-B-A`.
- Colapso geometrico de patrones tipo escalera cuando se puede reemplazar por menos codos.
- Deteccion y colapso de backtrack (llega al final y se devuelve en el mismo eje).
- Penalizacion adicional para evitar seleccionar candidatos con backtrack.
- Ajuste de radio de curvatura: intento de heredar valor util y tope por geometria posible.

Comportamiento observado en logs:
- Aparecen advertencias de Draft en algunos casos:
  - `DraftGeomUtils.fillet: Warning: edges have same direction. Did nothing`
- En casos con segmentos cortos, el radio aplicado puede bajar por limite geometrico (`radio_max`).

Pendientes para proxima sesion (si reaparece el problema):
1. Revisar caso donde una sola curva ideal termina en dos codos.
2. Afinar heredado de fillet para respetar mejor el radio original cuando la geometria lo permita.
3. Si vuelve un backtrack, capturar log `[AJUSTE_LOCAL]` y captura para ajustar score por ese patron.

Notas recurrentes:
- Problema recurrente de icono: verificar ruta de icono en header de macro (`# Icon:`) y resolucion del workbench al recargar comandos.
