# ElectricCR - Estado actual del proyecto

**Proposito:** Resumir la arquitectura vigente y el estado de integracion que debe conocerse antes de modificar objetos ElectricCR.

**Version:** 2026-08-08 13:01, America/Costa_Rica.

## Entorno

- Version objetivo actual: FreeCAD 1.1.1.
- Repositorio: `MVM444/Macros-de-Freecad`.
- Workbench principal en esta carpeta: `ElectricCR/`.
- Macros auxiliares relacionadas se encuentran tambien en carpetas como `Objetos/`, `Deteccion/`, `Iluminacion/` y `Resources/`.
- El flujo obligatorio de trabajo y validacion se documenta en `FLUJO_GPT_CODEX.md`.
- El mapa operativo vivo del Workbench se documenta en `MAPA_WORKBENCH.md`.
- Las decisiones de depuracion y migracion macro por macro se registran en `REVISION_MACROS.md`.

## Memoria operativa del proyecto

ElectricCR adopta como regla que el repositorio debe contener suficiente contexto para que Marco, GPT y Codex puedan retomar el proyecto sin reconstruir de memoria como funciona el Workbench.

Codex debe reconstruir el contexto desde la documentacion y el codigo antes de pedirle al usuario explicaciones que pueda obtener por inspeccion tecnica.

`MAPA_WORKBENCH.md` describe como funciona el sistema actual.

`REVISION_MACROS.md` registra que se ha decidido sobre cada macro durante la depuracion y migracion.

Si el codigo actual contradice la documentacion, debe describirse el comportamiento real desde el codigo y corregirse la documentacion.

## Estado arquitectonico del Workbench

ElectricCR ya funciona como un Workbench Python mediante `ElectricCR/InitGui.py` y `Gui::PythonWorkbench`.

Sin embargo, una parte importante de sus herramientas se incorpora actualmente mediante el registro dinamico de archivos `.FCMacro` realizado por `ElectricCR/commands/macros.py`.

Esto significa que el Workbench actual es hibrido:

- infraestructura Python propia del Workbench;
- modulos Python internos;
- objetos ElectricCR propios;
- macros registradas como comandos;
- herramientas de soporte, pruebas y recursos.

El auto-registro de macros se considera una arquitectura de transicion. La existencia de una macro en una carpeta escaneada no demuestra que deba pertenecer al Workbench definitivo.

## Estrategia de evolucion adoptada

No se reinicia ElectricCR desde cero.

Se conserva y respalda el Workbench actual y se realiza una migracion progresiva.

La secuencia adoptada es:

```text
reconstruir contexto
  -> revisar macro dentro de su familia
  -> clasificar
  -> decidir destino ElectricCR
  -> migrar solo si corresponde
  -> probar tecnicamente
  -> validar funcionalmente
  -> aceptar e integrar
```

La revision se realiza inicialmente en este orden:

1. Areas
2. Objetos
3. Iluminacion
4. Tomacorrientes
5. Deteccion
6. Cajas
7. Tableros y Configuracion del proyecto
8. Conectar

`Conectar` se deja para una fase avanzada debido a la cantidad de estrategias geometricas, solapamientos y dependencias historicas.

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

Regla vigente:

- Cambiar `AlturaRel` directamente en el enlace no garantiza que cambie la geometria si el enlace conserva el mismo maestro.
- La geometria pertenece al `LinkedObject`.
- Los cambios de altura semantica en enlaces deben resolver o crear un maestro compatible y reasignar `LinkedObject` cuando corresponda.

## Herramienta de altura y rotacion

Archivo:

- `Objetos/cambiar_altura_y_rotacion_objetos.FCMacro`

La version modernizada implementa tratamiento semantico por familia:

- ElectricCR directo: modifica `AlturaRel` y conserva el `Placement` base.
- ElectricCR `App::Link`: localiza o crea el maestro adecuado y relinka la instancia.
- HVAC MEP: utiliza la API existente de altura de instalacion.
- Objeto simple: conserva compatibilidad mediante `Placement.Base.z`.
- Rotacion: compone yaw sobre Z global conservando orientaciones tecnicas existentes.

Estado de esta herramienta:

- Implementada.
- Probada tecnicamente con FreeCAD 1.1.3 en la estacion utilizada por Codex.
- Version objetivo del proyecto: FreeCAD 1.1.1.
- Validacion visual y funcional de Marco con objetos reales todavia pendiente.
- Clasificacion provisional: `NUCLEO / CANDIDATA / PROMETEDORA`.

No debe promoverse a `ESTABLE / COMPROBADA` hasta completar la validacion funcional correspondiente.

## Referencia existente en MEPWorkbenchCR

Archivo principal revisado:

- `MEPWorkbenchCR/MEP/hvac/hvac_equipment.py`

El sistema HVAC maneja propiedades y funciones semanticas de altura de montaje y maestros compatibles. Este patron debe reutilizarse conceptualmente para ElectricCR, evitando copiar codigo sin revisar dependencias.

## Control de integracion de nuevas herramientas

ElectricCR adopta formalmente tres ejes de evaluacion:

1. Rol funcional.
2. Madurez.
3. Resultado comprobado.

Adicionalmente, durante la migracion se asigna una `Decision ElectricCR` independiente, registrada en `REVISION_MACROS.md`.

El inventario de herramientas utiliza estos ejes para distinguir herramientas productivas, candidatas, experimentales, duplicadas, incompletas, fallidas, abandonadas o pendientes de verificar.

Reglas vigentes:

- Una herramienta nueva no sustituye automaticamente una anterior.
- Una ejecucion correcta no equivale a validacion funcional.
- Un numero alto de ejecuciones puede provenir de pruebas o depuracion y no demuestra uso operativo.
- Los resultados negativos deben documentarse, no ocultarse.
- Las herramientas `FALLIDA`, `DESVIADA`, `DUPLICADA`, `INCOMPLETA` o `ABANDONADA` pueden conservarse temporalmente como evidencia o respaldo, pero no deben presentarse como mejoras productivas.
- Cuando no exista evidencia suficiente debe utilizarse `POR VERIFICAR`.

## Ciclo de vida adoptado

```text
CONTEXTO RECONSTRUIDO
  -> DEFINIDA
  -> IMPLEMENTADA
  -> PROBADA TECNICAMENTE
  -> VALIDADA FUNCIONALMENTE
  -> REVISADA POR GPT
  -> ACEPTADA
  -> INTEGRADA
```

La documentacion de cada tarea debe reflejar con precision en que etapa se encuentra. `HISTORIAL_CAMBIOS.md` se reserva para cambios aceptados.
