# ElectricCR - Estado actual del proyecto

**Proposito:** Resumir la arquitectura vigente que debe conocerse antes de modificar objetos ElectricCR.

**Version:** 2026-08-06 12:41, America/Costa_Rica.

## Entorno

- Version objetivo actual: FreeCAD 1.1.1.
- Repositorio: `MVM444/Macros-de-Freecad`.
- Workbench principal en esta carpeta: `ElectricCR/`.
- Macros auxiliares relacionadas se encuentran tambien en carpetas como `Objetos/`, `Deteccion/`, `Iluminacion/` y `Resources/`.

## Arquitectura de dispositivos ElectricCR

El modulo central revisado es:

- `ElectricCR/electriccr/features/objeto_toma_uno.py`

Este modulo permite representar tomacorrientes, apagadores, luminarias, sensores, rociadores, altavoces y camaras mediante:

- Un simbolo 2D cargado desde el registro.
- Un modelo 3D cargado desde el registro.
- Un objeto `Part::FeaturePython` directo o una instancia `App::Link` hacia un maestro oculto.

## Geometria local

En los objetos directos creados por `TomaUnoProxy`:

- El simbolo 2D se construye en `Z = 0` del sistema local del objeto.
- El modelo 3D se traslada en Z segun `AlturaRel`.
- `OffsetX`, `OffsetY` y `Giro` se aplican en coordenadas locales.
- El `Placement` posiciona y rota el conjunto completo en el documento.

Consecuencia:

- Cambiar `AlturaRel` debe mover solamente el componente 3D.
- Cambiar `Placement.Base.z` mueve tanto el simbolo 2D como el componente 3D.

## Objetos directos

La macro:

- `Deteccion/ColocarDetectores_NFPA.FCMacro`

crea actualmente sensores mediante `crear_toma_uno`, es decir, como objetos directos `Part::FeaturePython`. Despues asigna `AlturaRel`, `ModoVisual`, `Categoria`, `Placement` y ejecuta `touch()`.

Para estos objetos, cambiar `AlturaRel` y recomputar deberia reconstruir la geometria sin elevar el simbolo 2D.

## Objetos App::Link

La funcion `crear_toma_link` crea una instancia `App::Link` hacia un maestro oculto. El maestro se identifica mediante una combinacion de:

- Clave de registro.
- Tipo logico.
- Modo visual.
- Orientacion.
- Altura relativa.

La instancia recibe propiedades informativas como `Tipo`, `KeyRegistro`, `ModoVisual`, `AlturaRel` y `OrientacionPared`.

Limitacion vigente:

- Cambiar `AlturaRel` directamente en el enlace no cambia automaticamente el maestro vinculado.
- La geometria continua perteneciendo al `LinkedObject` anterior.
- La propiedad visible en el enlace puede quedar diferente de la altura real de su geometria.

## Herramienta antigua de altura y rotacion

Archivo:

- `Objetos/cambiar_altura_y_rotacion_objetos.FCMacro`

Comportamiento actual:

- Selecciona objetos que tengan `Placement`.
- Modifica directamente `Placement.Base.z`.
- Sustituye la rotacion por un yaw sobre el eje Z.

Limitaciones:

- Eleva tambien el simbolo 2D.
- No distingue objetos directos, enlaces, maestros ni equipos MEP.
- Puede perder componentes de rotacion que no correspondan exclusivamente a yaw Z.
- No utiliza propiedades semanticas de altura de instalacion.

## Referencia existente en MEPWorkbenchCR

Archivo principal revisado:

- `MEPWorkbenchCR/MEP/hvac/hvac_equipment.py`

El sistema HVAC ya maneja:

- Propiedad `Height` para altura de montaje.
- Propiedad `BaseLevel` para referencia de nivel.
- Maestros diferenciados por modelo, altura, tamano de simbolo y modo visual.
- Verificacion y reasignacion del `LinkedObject` esperado.
- Funciones de saneamiento y sincronizacion.

Este patron debe reutilizarse conceptualmente para ElectricCR, evitando copiar codigo sin revisar dependencias.

## Problema actual confirmado

Al modificar Z mediante `Placement`, el simbolo 2D cambia de altura porque forma parte del mismo conjunto transformado.

Al modificar propiedades del sensor o enlace, pueden ocurrir dos casos:

- Objeto directo: requiere `touch()` y `recompute()` para regenerar la geometria.
- `App::Link`: requiere localizar o crear el maestro correcto y reasignar `LinkedObject`.

## Estado de esta rama

La rama `agent/electriccr-altura-simbolo-2d-context` agrega por ahora solamente documentacion de coordinacion. No modifica codigo funcional.