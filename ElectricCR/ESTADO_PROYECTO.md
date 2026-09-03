# ElectricCR - Estado actual del proyecto

## Barra comun Espacios y Recintos v0.1

Ultima actualizacion: 2026-09-02 America/Costa_Rica
Estado: **INTEGRADA Y VERIFICADA MCP EN FREECAD 1.1.3**.

ElectricCR puede cargar los comandos comunes sin activar Facil Arquitectura.
El registro es idempotente y la barra fue verificada visualmente. Se conserva
visible `PoligonosRecintosDesdeArchWalls.FCMacro` como **Recintos desde muros
BIM**, sin cambiar su algoritmo, metadatos, enlaces ni regeneracion.

Esta integracion no migra Areas, no crea Spaces y no modifica dispositivos.

## Estado vigente - Prototipo luminaria semantica y arbol idempotente

Ultima actualizacion: 2026-09-02 America/Costa_Rica
FreeCAD objetivo: 1.1.3
Estado: **CERRADO / IMPLEMENTADO / VERIFICADO MCP EN FREECAD 1.1.3**.

Revalidado el 2026-09-02 sin cambios funcionales: modulos cargados desde DEV,
pruebas puras y smoke integral aprobados, cero documentos/temporales residuales.

La fase 2A de RoomResolver permanece cerrada y verificada. No se reabre ni se modifica su baseline.

Hallazgo principal de esta fase: ElectricCR ya posee un nucleo generico en
`electriccr/features/objeto_toma_uno.py`. El modulo soporta dispositivos directos
`Part::FeaturePython` y `App::Link` con masters ocultos, combina simbolo 2D y modelo
3D en una sola identidad geometrica, mantiene el 2D en Z local 0 y desplaza solo
el 3D mediante `AlturaRel`.

Por tanto, la direccion vigente es **auditar y evolucionar este nucleo**. `Arch
Equipment` se compara como posible capacidad nativa BIM/IFC o adaptador; no se
adopta como reemplazo automatico.

El contrato `relaciones -> arbol` permanece autoritativo. El trabajo actual define
los futuros enlaces `Space`, `Circuit`, `Panel`, `Control`, `System`, `Level` y
`Host`, la compatibilidad con masters/App::Link y la reconstruccion idempotente del
arbol. No se han modificado dispositivos, FCStd, masters ni codigo.

Documento de diseno:
`ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md`.

La matriz de decision ya se cerro a nivel de diseno: `App::Link` vigente es la identidad operativa preferida para el primer prototipo; `TomaUnoProxy` conserva el nucleo geometrico/masters y `Arch Equipment` se compara especificamente por BIM/IFC. El contrato minimo propone `ElementUID`, `Space` y `Circuit`, derivando Level/Panel cuando sea posible.

El prototipo reversible ya fue implementado y probado con una sola luminaria
temporal. La identidad operativa sigue siendo el `App::Link` actual, enriquecido
solo con `ElementUID` y `Space`. El arbol se deriva de `Space`, `CircuitoID` y
los LinkList existentes de Control, usa claves estables y es idempotente.

La rama visual utiliza un `App::Link` de indice marcado como referencia de
proyeccion. Esto evita retirar la luminaria fisica de su grupo manual, porque
los `App::DocumentObjectGroup` de FreeCAD mantienen pertenencia visual
exclusiva. Los masters permanecen ocultos en `_lib/_lib_devices`.

El comparador `Arch Equipment` confirma propiedades BIM/IFC y `IfcType=Light
Fixture`, pero requiere Base/copia geometrica. No sustituye el esquema de master
compartido. No se autoriza desde este cierre una migracion de dispositivos ni
el inicio de tomacorrientes/apagadores.

---

## Estado vigente - RoomResolver fase 2A

Ultima actualizacion: 2026-09-01 America/Costa_Rica
FreeCAD: 1.1.3 revision 20260725
Estado: **CERRADA / VERIFICADA MCP**.

El calculo integral de iluminacion enumera recintos mediante `CRBIMCore`.
Space tiene prioridad sobre Area heredada, la hoja `DatosRecintos` conserva su
contrato de 12 columnas y el comando no escribe propiedades de layout en
Spaces. La compatibilidad legacy de Areas permanece.

El contrato `relaciones -> arbol` esta documentado, pero no migrado. Controles
ya usan LinkList; Room, Panel, Level y System aun no tienen enlaces uniformes.
No se redefinieron ni migraron dispositivos y no se reorganizaron modelos.

Siguiente fase posible, no iniciada: objeto electromecanico comun y
reconstruccion idempotente del arbol desde relaciones.

---

**Proposito:** Resumir la arquitectura vigente y el estado de integracion que debe conocerse antes de modificar objetos ElectricCR.

**Version:** 2026-08-12 14:30, America/Costa_Rica.

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

## Estado de la tarea activa - Panel de macros ElectricCR

El lanzador de macros ya dispone de una implementacion local ampliada en
`ElectricCR/commands/macro_launcher.py`. La fuente de metadatos es
`ElectricCR/commands/macros.py` y las estadisticas siguen viniendo de
`ElectricCR/usage_log.py`; no se creo un segundo sistema de conteo ni se
escanea el repositorio desde el panel.

Estado: **PROGRAMADO / COMPILADO / PROBADO TECNICAMENTE / VALIDADO VISUALMENTE EN MCP**.

La prueba simulada con FreeCADCmd 1.1.3 registro 16 grupos y 122 comandos con
iconos especificos o `Rayo.svg`. El intento de validacion visual mediante MCP
expiró por timeout de la sesion GUI, por lo que la validacion visual en el
FreeCAD de Marco queda pendiente en ese primer intento. La verificacion
posterior esta documentada abajo. No se modificaron documentos FCStd.

## Arquitectura de dispositivos ElectricCR

## Estado de la tarea activa - Integracion de descripciones GPT

Estado: **IMPLEMENTADA / COMPILADA / PROBADA / VERIFICADA_MCP /
VALIDADA_VISUALMENTE**.

Se integraron por `ruta` las 192 entradas de
`ElectricCR/MACROS_DESCRIPCIONES_GPT.json`. El catalogo conserva 192
descripciones funcionales: 133 sustituyeron textos vacios o genericos y 59
descripciones locales concretas se mantuvieron. En 36 casos se registro la
alternativa GPT y la discrepancia sin reemplazar el texto local.

Los campos manuales de comentario, estado, decision y las estadisticas de
uso real, prueba e historico no fueron modificados. El Panel busca tambien
en la descripcion y muestra descripcion, fuente, confianza y discrepancias
en el detalle y en `Copiar diagnostico`.

La prueba en FreeCAD 1.1.3 valido 12 grupos, 192 filas catalogadas, una
busqueda por texto exclusivo de descripcion, diagnostico con descripcion y
comentario, y una herramienta visible de cada grupo principal. No se
modificaron documentos FCStd ni se hizo commit o push.

## Estado de la tarea activa - Panel Fase 2

Estado: **IMPLEMENTADA / COMPILADA / PROBADA / VERIFICADA_MCP /
VALIDADA_VISUALMENTE**.

El catalogo JSON contiene 192 entradas: 122 activas y 70 historicas. El Panel
lee descripciones, permite comentarios/estado/decision manuales, conserva la
Fase 1, separa uso real/pruebas/historico y ofrece filtros de auditoria,
historicas y contraer/expandir grupos. La prueba MCP con FreeCAD 1.1.3 mostro
12 grupos y 122 herramientas activas; la prueba de botones registro una
ejecucion real y una prueba en un log temporal. No se modificaron FCStd.

Correccion posterior: el comentario ahora se guarda contra el elemento
anterior de `currentItemChanged`, evitando que pase a la macro nueva. Las filas,
estadisticas, recursos de comandos y catalogo se cachean durante la apertura;
la busqueda ya no recalcula todo por cada tecla.

### Verificacion visual posterior del Panel

La validacion MCP posterior confirmo que la captura minima provenia de la
prueba segura: esa prueba habia sustituido en memoria `_MACRO_GROUPS` por un
grupo unico, aunque el registro de metadatos conservaba 122 comandos reales.
Al reconstruir los grupos desde el registro, el Panel real mostro 12 grupos y
122 filas, filtros, panel de detalles, botones y modo diagnostico. No se
modificaron documentos FCStd.

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
