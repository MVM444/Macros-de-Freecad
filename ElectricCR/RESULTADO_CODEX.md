# ElectricCR - Resultado de Codex

**Estado:** Implementado y probado.

**Fecha de ejecucion:** 2026-08-06, America/Costa_Rica.

**Tarea relacionada:** `TAREA_ACTUAL.md`

## Busqueda previa

- Se reviso la documentacion oficial de `App::Link`: el enlace reutiliza la geometria y representacion del objeto enlazado. Por ello, cambiar solo un metadato de altura en la instancia no modifica la forma del maestro.
- Se reviso el patron oficial de objetos `FeaturePython`: la forma se actualiza desde `execute()` durante la recomputacion.
- Se reviso la guia oficial de objetos de documento y recomputacion para mantener una sola transaccion y una recomputacion controlada.
- Fuentes:
  - https://freecad.github.io/SourceDoc/df/d9b/classApp_1_1Link.html
  - https://freecad.github.io/SourceDoc/de/d80/classFeaturePython_1_1Box.html
  - https://freecad.github.io/Addon-Academy/Guides/Code/Document-Objects/

## Causa confirmada

La macro anterior aplicaba el mismo tratamiento a todos los objetos: cambiaba `Placement.Base.z` y reemplazaba la rotacion completa por una rotacion nueva sobre Z. Esto producia tres fallos:

1. En objetos ElectricCR directos elevaba conjuntamente la representacion 2D y el modelo 3D, en vez de cambiar `AlturaRel`.
2. En `App::Link`, cambiar el metadato `AlturaRel` de la instancia no cambiaba la geometria compartida por el maestro.
3. Al reemplazar la rotacion completa se perdian pitch y roll tecnicos existentes.

MEPWorkbenchCR ya tenia el patron correcto para altura: `InstallationElevation` en milimetros, `Height` como alias historico y relink a un maestro compatible, sin reconstruir ni mover `Symbol2D`/`Info2D`.

## Plan aplicado

1. Clasificar la seleccion como equipo MEP HVAC, dispositivo ElectricCR directo, dispositivo ElectricCR `App::Link` u objeto simple.
2. Usar la propiedad o API semantica de cada familia.
3. Para `App::Link`, recuperar metadatos modernos o heredados desde el maestro y relinkar solo la instancia seleccionada.
4. Componer el giro solicitado alrededor del eje Z global con la rotacion existente.
5. Ejecutar toda la seleccion dentro de una transaccion, una recomputacion y rollback total ante cualquier error.
6. Probar altura/rotacion absoluta y delta, undo/redo y persistencia.

## Archivos revisados

- `Objetos/cambiar_altura_y_rotacion_objetos.FCMacro`
- `Objetos/cambiar_altura_y_rotacion_objetos.svg`
- `ElectricCR/electriccr/features/objeto_toma_uno.py`
- `Deteccion/ColocarDetectores_NFPA.FCMacro`
- `Iluminacion/ColocarLuminarias_Link.FCMacro`
- `MEPWorkbenchCR/MEP/hvac/hvac_equipment.py`
- `MEPWorkbenchCR/tests/test_hvac_evaporator_installation_elevation.py`

## Archivos modificados

- `Objetos/cambiar_altura_y_rotacion_objetos.FCMacro`
- `ElectricCR/electriccr/features/objeto_toma_uno.py`
- `ElectricCR/tests/test_cambiar_altura_rotacion_semantica.py`
- `ElectricCR/RESULTADO_CODEX.md`

## Cambios realizados

- La interfaz ahora muestra y precarga la altura semantica de instalacion.
- Se agrego el icono SVG homonimo para que el cargador dinamico no use el icono generico.
- ElectricCR directo modifica `AlturaRel`, conserva `Placement` y ejecuta `touch()`.
- ElectricCR `App::Link` obtiene o crea un maestro por tipo, modo, orientacion y altura; relinka solo la instancia y conserva XY, cota base, rotacion, etiqueta y grupo.
- Los enlaces de luminarias heredados sin metadatos en la instancia se reconocen desde `LnkMasterKey`, `LnkMasterAltura`, `LnkMasterMode` y las propiedades del maestro.
- HVAC usa `installation_elevation_mm()` y `set_installation_elevation()` existentes.
- Los objetos sin semantica de altura conservan la compatibilidad mediante `Placement.Base.z`.
- La rotacion absoluta o delta se compone alrededor de Z global y conserva pitch/roll.
- La consola informa objeto, tipo detectado, propiedad usada, valor anterior/nuevo, maestro anterior/nuevo y resultado.
- Ante un fallo individual se aborta la transaccion completa para evitar estados parciales.
- No se agrego ninguna migracion automatica al abrir documentos.

## Pruebas

Motor probado: FreeCAD `1.1.3` (`20260725`, compilacion disponible en esta estacion).

| Prueba | Objeto | Resultado | Evidencia o mensaje de consola |
|---|---|---|---|
| Sensor NFPA directo | Creado mediante `insert_sensor()` de `ColocarDetectores_NFPA.FCMacro` | OK | `sensor_direct: True`; `AlturaRel=3100/3200`, `Placement.Base.z=0` |
| Dispositivo ElectricCR App::Link | Link moderno en prueba MCP | OK | `MCP_SMOKE_PASS=True`; instancia relinkada y link hermano mantuvo el maestro original |
| Luminaria con simbolo 2D | Link heredado con maestro `TomaUnoProxy` | OK | `legacy_luminaire_link: True`; conserva XY, Z=0, etiqueta, grupo y metadatos |
| Equipo HVAC MEP | Evaporadora `Pared_12000`, seleccion tambien desde `Symbol2D` | OK | `hvac_symbol_2d_plane: True`; altura fisica cambia y Z del simbolo permanece |
| Objeto sencillo | `Part::Feature` sin altura semantica | OK | `simple_fallback: True`; usa `Placement.Base.z` |
| Altura absoluta | Seleccion mixta | OK | `absolute_and_delta: True` |
| Altura delta | Seleccion mixta, +100 mm | OK | `absolute_and_delta: True` |
| Rotacion absoluta | Yaw 90 grados con pitch/roll existentes | OK | `technical_rotation_preserved: True` |
| Rotacion delta | +15 grados despues del absoluto | OK | yaw 105 grados; pitch/roll sin cambio |
| Undo y redo | Transaccion completa | OK | `undo_redo: True` |
| Guardar y reabrir | Documento temporal FCStd | OK | `save_reopen: True` |
| Rollback por fallo | Link sin `KeyRegistro` recuperable | OK | `ok=False`, objeto previo regreso de Z=999 a Z=100 |
| Prueba MCP en GUI | Documento temporal, sesion grafica activa | OK | `MCP_SMOKE_PASS=True`; documento activo restaurado a `Puriscal_03_08_2026` |
| Regresion HVAC existente | `test_hvac_evaporator_installation_elevation.py` | OK | todas las banderas devueltas en `True` |

Comandos principales ejecutados:

```text
FreeCAD 1.1/bin/python.exe ElectricCR/tests/test_cambiar_altura_rotacion_semantica.py
FreeCAD 1.1/bin/python.exe MEPWorkbenchCR/tests/test_hvac_evaporator_installation_elevation.py
```

## Riesgos y limitaciones

- Un `App::Link` ElectricCR heredado que haya perdido tanto sus metadatos como los de su maestro se rechaza de forma segura; no se adivina el tipo y se revierte la transaccion.
- La prueba completa con HVAC mediante MCP excedio el tiempo de respuesta de 90 segundos por la carga STEP en la sesion grafica. El documento temporal se cerro correctamente; la misma prueba completa paso con el Python incluido en FreeCAD y la prueba MCP ligera paso en la GUI.
- No se modifico ni guardo el documento `Puriscal_03_08_2026`.

## Pendientes

- Validacion visual del usuario con uno o dos objetos reales de Puriscal desde el icono de la macro.
- No actualizar `HISTORIAL_CAMBIOS.md` hasta que el usuario acepte el resultado.

## Conclusion

La herramienta mantiene compatibilidad con objetos simples y ahora cambia la altura fisica 3D de sensores, luminarias enlazadas y equipos HVAC sin elevar el simbolo 2D. La rotacion ya no elimina orientaciones tecnicas existentes.
