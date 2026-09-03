# ElectricCR - Mapa operativo del Workbench

**Proposito:** Servir como memoria tecnica viva para Marco, GPT, Codex y otros agentes. Este archivo debe permitir reconstruir como funciona ElectricCR sin depender de la memoria del usuario ni de conversaciones anteriores.

**Version:** 2026-08-08 18:06, America/Costa_Rica.

## Regla principal

Marco no debe tener que recordar ni explicar nuevamente la arquitectura completa del Workbench cada vez que se retoma el proyecto.

Antes de pedirle al usuario que recuerde como funciona una herramienta, Codex debe reconstruir el contexto leyendo este archivo, la documentacion vigente y el codigo relacionado.

Si la documentacion y el codigo difieren, prevalece el codigo actual y la discrepancia debe documentarse.

## Como funciona ElectricCR actualmente

ElectricCR ya es registrado por FreeCAD como un Workbench Python.

Archivo principal:

- `ElectricCR/InitGui.py`

Responsabilidades principales de `InitGui.py`:

- registrar `ElectricCRWorkbench`;
- crear menus y barras de herramientas;
- integrar comandos de Draft/BIM cuando estan disponibles;
- cargar configuracion desde `config.json`;
- registrar herramientas ElectricCR;
- mantener acceso al lanzador de macros;
- aplicar modos de interfaz;
- registrar estadisticas de uso;
- gestionar recarga y acciones contextuales.

La clase del Workbench devuelve:

```text
Gui::PythonWorkbench
```

Por tanto, ElectricCR no es solamente una carpeta de macros. Actualmente es un Workbench Python que utiliza muchas macros como comandos ejecutables.

## Capa actual de macros

Archivo principal:

- `ElectricCR/commands/macros.py`

Este modulo registra archivos `.FCMacro` como comandos de FreeCAD y actualmente descubre herramientas a partir de carpetas del repositorio.

Consecuencia importante:

- que una macro exista en una carpeta escaneada puede hacer que aparezca en ElectricCR;
- esto no demuestra que la macro sea estable, productiva, necesaria ni mejor que otra;
- pueden coexistir herramientas antiguas, experimentales, duplicadas, desviadas o creadas durante pruebas con IA.

Esta forma de auto-registro debe considerarse una arquitectura de transicion, no el criterio final de seleccion del Workbench.

El Panel de macros mantiene un catalogo informativo versionado en
`ElectricCR/data/macros_catalog.json` y su vista humana generada en
`ElectricCR/MACROS_CATALOGO.md`. El catalogo puede contener herramientas activas
e historicas sin ejecutar decisiones de movimiento o retiro. Las estadisticas de
`usage_log.py` conservan el conteo previo como historico sin clasificar y
separan las nuevas ejecuciones en uso real y pruebas.

## Capas conceptuales actuales

### 1. Capa Workbench

Incluye principalmente:

- `ElectricCR/InitGui.py`
- `ElectricCR/config.json`
- `ElectricCR/commands/`
- `ElectricCR/ui/`

Gestiona la integracion con FreeCAD, menus, barras, comandos, modos y herramientas de sistema.

### 2. Capa de macros de compatibilidad y trabajo

Incluye macros distribuidas en familias como:

- `Areas/`
- `Objetos/`
- `Iluminacion/`
- `Tomacorrientes/`
- `Deteccion/`
- `Cajas/`
- `Tableros/`
- `Configuracion del proyecto/`
- `Conectar/`
- otras carpetas relacionadas.

Estas macros no deben considerarse automaticamente parte del Workbench definitivo.

### 3. Capa de objetos y logica Python propia

Incluye modulos Python internos, por ejemplo:

- `ElectricCR/electriccr/features/`
- `ElectricCR/electriccr/connections/`

Aqui existen comportamientos propios de objetos ElectricCR, incluyendo objetos `FeaturePython`, `App::Link`, maestros y propiedades semanticas.

Esta capa es parte de la evolucion hacia un Workbench mas formal y mantenible.

El analisis rectangular historico se conserva bajo
`Xcluidos/Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` como respaldo;
su logica reusable vive en `FacilArquitecturaWB/core/rectangular_area_analysis.py`.
El lanzador archivado ya no se registra en la interfaz y el motor no depende de
`Scripts Varios` ni reemplaza el analisis poligonal.

La familia `connections/` separa asignaciones, tableros, puertos, ruteo,
alimentadores y backbone. TP, TCOM y otros codigos son datos, no algoritmos.
Las guias de ruta son opcionales y los objetos generados viven bajo
`ElectricCR_Conexiones` para evitar ciclos entre grupos y `PropertyLink`.

En la barra normal `Conectar` deben quedar como flujo principal:

- `Conectar Alimentadores...`;
- `Conectar Circuito / Backbone...`;
- `Ajustar Ruta...`.

Los wrappers historicos se registran en `Conectar Legacy`, disponible por menu
pero no incluido en la configuracion compacta de barras.

### 4. Capa de soporte

Incluye:

- `ElectricCR/tests/`
- `ElectricCR/logs/`
- recursos e iconos;
- documentacion tecnica;
- herramientas de diagnostico y mantenimiento.

No todo elemento de soporte debe aparecer en la interfaz del usuario.

## Estado de transicion arquitectonica

La estrategia adoptada es:

```text
Workbench actual funcional
        |
        +-- conservar y respaldar
        |
        v
revision macro por macro
        |
        +-- incorporar al Workbench
        +-- incorporar despues
        +-- mantener como macro
        +-- fusionar
        +-- experimental
        +-- legacy
        +-- respaldo
        +-- excluir
        +-- descartable
        +-- por verificar
        |
        v
migracion progresiva a comandos y modulos Python
```

No se reinicia ElectricCR desde cero.

No se convierten todas las macros automaticamente.

La depuracion y la migracion son un mismo proceso: primero se determina si una herramienta merece sobrevivir y despues se decide si debe convertirse a codigo del Workbench.

## Politica de migracion

Una macro solamente debe migrarse a comando/modulo propio de ElectricCR cuando exista evidencia suficiente de que aporta valor real.

Candidatos prioritarios:

- `NUCLEO + COMPROBADA`;
- luego `OPERATIVA + COMPROBADA`;
- despues `ESPECIALIZADA + COMPROBADA` cuando tenga sentido integrarla.

No migrar automaticamente:

- `PROMETEDORA`;
- `EXPERIMENTAL`;
- `POR VERIFICAR`;
- `REVISAR-SOLAPAMIENTO`;
- `DESVIADA`;
- `DUPLICADA`;
- `FALLIDA`;
- `ABANDONADA`.

Las dependencias `LEGACY-DEPENDENCIA` se conservan mientras exista codigo que las requiera.

## Orden recomendado de revision por familias

1. Areas
2. Objetos
3. Iluminacion
4. Tomacorrientes
5. Deteccion
6. Cajas
7. Tableros y Configuracion del proyecto
8. Conectar

`Conectar` se deja para una etapa avanzada porque contiene muchas estrategias geometricas, solapamientos, pruebas historicas y dependencias.

## Como debe retomar Codex el proyecto

Cada vez que Codex retome ElectricCR despues de una pausa o en una nueva sesion debe:

1. Leer los archivos obligatorios definidos en `AGENTS.md`.
2. Leer este `MAPA_WORKBENCH.md`.
3. Revisar `REVISION_MACROS.md` para conocer decisiones ya tomadas y pendientes.
4. Inspeccionar el codigo real de la familia o herramienta involucrada.
5. Reconstruir sus dependencias y relaciones con otras herramientas.
6. Explicar brevemente al usuario como funciona actualmente la parte que se va a revisar.
7. Indicar que hechos estan confirmados y que puntos siguen siendo inferencias o desconocidos.
8. Solo despues proponer cambios o una decision de migracion.

Codex no debe utilizar preguntas al usuario como sustituto de una inspeccion que pueda realizar en el repositorio.

Preguntar al usuario solamente por informacion que no pueda deducirse razonablemente del codigo, documentacion, historial, pruebas o inventario, por ejemplo:

- si una herramienta realmente se usa en el trabajo cotidiano;
- si el resultado visual corresponde a lo esperado;
- por que una macro historica fue abandonada cuando no existe evidencia documental;
- preferencias funcionales que no esten expresadas en el proyecto.

## Jerarquia de evidencia

Para reconstruir el funcionamiento o decidir el estado de una herramienta utilizar, en este orden aproximado:

1. Codigo actual y dependencias reales.
2. Pruebas ejecutables y resultados reproducibles.
3. Documentacion tecnica vigente y decisiones aceptadas.
4. `REVISION_MACROS.md` y clasificacion aprobada.
5. `RESULTADO_CODEX.md` y documentacion de tareas.
6. Historial Git y versiones anteriores.
7. Registro de uso, considerando que puede incluir pruebas de desarrollo.
8. Nombres de archivos, fechas y otras inferencias debiles.

Nunca concluir que una macro es mejor solamente porque es mas nueva.

Nunca concluir que una macro es importante solamente porque tiene muchas ejecuciones.

## Responsabilidad de mantenimiento

Cuando una revision cambie de forma relevante la comprension de ElectricCR, Codex debe actualizar este archivo.

Ejemplos:

- una macro deja de ser la herramienta principal;
- una funcion se migra a un modulo Python;
- cambia el mecanismo de registro de comandos;
- se elimina una dependencia legacy;
- se consolida una familia de herramientas;
- cambia la estructura de carpetas o la arquitectura del Workbench.

Este archivo debe describir el sistema que existe realmente, no el sistema que se desea construir en el futuro.
