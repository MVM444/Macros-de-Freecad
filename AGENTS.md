# Instrucciones de arquitectura FreeCAD CR

Estas instrucciones aplican a todo el repositorio.

Al analizar o modificar ElectricCR, MEPWorkbenchCR, FacilArquitecturaWB, macros compartidas o modelos relacionados, usar la habilidad personal `$freecad-cr-workbench-architecture` y leer su contrato antes de actuar.

Principios obligatorios:

- Mantener separados los Workbenches y compartir un núcleo neutral.
- Usar BIM/Arch nativo para IFC, Building Storey, Arch Space, Host y Equipment.
- Mantener una única identidad semántica por elemento y vincular 3D, Symbol2D e Info2D.
- Siempre que sea tecnicamente razonable, el 2D y el 3D deben ser representaciones del mismo objeto, con la misma identidad, Placement y propiedades; no mantener manualmente dos objetos independientes para representar un mismo elemento.
- Favorecer un flujo de trabajo 2D -> 3D: colocar y editar facilmente los elementos mediante simbologia tecnica en planta y usar el 3D para visualizacion, coordinacion y comprobacion espacial.
- Todo elemento calculado, dimensionado o disenado por un Workbench debe poder producir una representacion documental 2D comprensible, identificable y exportable.
- Usar PropertyLink para Space, Host, Circuit, Panel, System y equipos conectados.
- No sustituir el resultado térmico calculado por la capacidad del equipo seleccionado.
- Mantener comandos y migraciones idempotentes, con identificadores estables.
- Exportar IFC/DXF por propiedades y relaciones semánticas, no solo por nombres o visibilidad.
- Conservar compatibilidad heredada mediante adaptadores y migración no destructiva.
- No guardar ni modificar un FCStd original sin autorización explícita.

## Idiomas e internacionalizacion

Esta regla aplica a todos los Workbenches actuales y futuros del repositorio. Todo Workbench destinado a uso normal, distribucion o publicacion debe ofrecer, como minimo, una interfaz completa en **espanol e ingles**.

- El idioma visible debe seguir automaticamente el idioma configurado en FreeCAD/Qt; no mantener dos interfaces paralelas ni un selector propio salvo necesidad justificada.
- Deben ser traducibles, como minimo: nombre visible del Workbench, menus, barras de herramientas, comandos, tooltips, dialogos, Task Panels, mensajes de error y advertencia, mensajes de estado, Ayuda, Primeros pasos, Demo e Informacion/About.
- La documentacion publica basica de instalacion y uso debe estar disponible al menos en espanol e ingles. La documentacion tecnica interna de desarrollo puede mantenerse en un solo idioma mientras no forme parte de la distribucion orientada al usuario.
- Los identificadores internos no se traducen: IDs de comandos, nombres de propiedades, claves JSON, preferencias, nombres de modulos/archivos y demas contratos internos deben permanecer estables, preferiblemente ASCII y sin depender del idioma visible.
- Usar la infraestructura normal de internacionalizacion de FreeCAD/Qt (`translate`/`QT_TRANSLATE_NOOP`, catalogos `.ts` y compilados `.qm`, o el mecanismo oficial equivalente vigente) en lugar de duplicar textos o logica por idioma.
- Una herramienta nueva orientada al usuario no se considera lista para RELEASE mientras sus textos visibles principales no esten cubiertos en espanol e ingles.
- Antes de una RELEASE, verificar en FreeCAD real ambos idiomas y comprobar que no queden textos importantes hardcodeados en un solo idioma.

## Desarrollo y publicacion de Workbenches (DEV / RELEASE)

Todo Workbench que tenga una version publica debe manejar dos funciones claramente diferenciadas, pero no dos lineas de desarrollo paralelas:

- **DEV - Desarrollo:** la copia ubicada dentro de `Macros-de-Freecad` y sincronizada mediante Google Drive es la fuente de verdad para modificar, probar, depurar y desarrollar. Durante el desarrollo puede cargarse explicitamente mediante los loaders de Programacion.
- **RELEASE - Publicacion:** el repositorio GitHub dedicado contiene versiones estables, limpias, probadas y distribuibles, destinadas a Addon Manager, otras computadoras y usuarios externos.
- Las modificaciones se realizan primero en DEV. El repositorio publico no se usa como una segunda fuente independiente de desarrollo.
- No es necesario publicar cada cambio menor. Una nueva RELEASE se genera cuando exista una mejora significativa o un conjunto coherente de mejoras que haya superado las pruebas correspondientes.
- Flujo obligatorio: `DEV -> pruebas -> revision -> publicacion RELEASE -> validacion del Addon`.
- Si ambas copias existen fisicamente en una computadora, FreeCAD no debe cargar simultaneamente las dos versiones del mismo Workbench. Durante desarrollo se prioriza explicitamente DEV; para validar o usar la publicacion se utiliza la instalacion gestionada por Addon Manager.
- Google Drive conserva la autoridad como fuente de verdad de desarrollo; GitHub conserva la funcion de distribucion, historial, respaldo y publicacion.
- La publicacion debe hacerse desde una copia/staging limpio generado a partir de DEV, no mediante una bifurcacion manual mantenida en paralelo.

## Neutralidad institucional y publicacion

Ningun Workbench, Addon, repositorio publico ni documento destinado a publicacion debe identificar o permitir inferir la institucion de origen de los desarrollos.

Reglas obligatorias antes de publicar o distribuir:

- No incluir el acronimo `CCSS`, el nombre completo de la institucion ni referencias equivalentes.
- No incluir nombres de dependencias, unidades internas, codigos de procedimientos, enlaces institucionales, logotipos, metadatos, ejemplos, capturas o datos que permitan identificar directa o indirectamente a la institucion.
- Los ejemplos y archivos de demostracion deben usar nombres, datos y escenarios genericos o anonimizados.
- Revisar README, `package.xml`, codigo, comentarios, traducciones, recursos, ejemplos y documentacion antes de publicar.
- La documentacion interna de trabajo puede conservar referencias necesarias para desarrollo o trazabilidad, pero estas no deben copiarse a artefactos publicos sin una revision de sanitizacion previa.

La referencia canónica está en:

`C:\Users\marco\.codex\skills\freecad-cr-workbench-architecture\references\architecture-contract.md`

## Continuidad y diagnostico FreeCAD

Para continuar sesiones, diagnosticar FreeCAD mediante MCP, comparar equipos, probar cambios y preparar el traspaso hacia ChatGPT/GitHub, usar la skill `$freecad-project-memory`.

La skill de memoria no sustituye `$freecad-cr-workbench-architecture`; ambas se usan juntas cuando la tarea afecta arquitectura del Workbench.


## Feedback obligatorio en operaciones potencialmente largas

Esta regla aplica a todos los Workbenches y macros del repositorio. Cualquier operacion que normalmente pueda tardar varios segundos, o cuya duracion sea incierta, debe informar al usuario **antes** y durante el calculo.

- Antes de iniciar la fase costosa, mostrar un aviso equivalente a: `⏳ El siguiente proceso puede tardar varios segundos o algunos minutos. FreeCAD puede permanecer ocupado mientras se realiza el calculo.`
- El aviso debe estar **ya pintado y visible** antes de entrar al primer recompute, bucle geometrico, importacion/exportacion o fase costosa. En GUI Qt sincronica, forzar el repintado de la zona de estado y procesar los eventos pendientes (`repaint`/`FreeCADGui.updateGui`/`QApplication.processEvents` o mecanismo equivalente) antes de continuar.
- Mantener durante el trabajo un indicador visual inequívoco de actividad, preferiblemente reloj de arena, spinner o barra indeterminada, ademas del cursor de espera cuando corresponda.
- No ocultar ni sustituir inmediatamente el aviso previo por otro texto de forma que el usuario no alcance a verlo; los mensajes por etapa deben conservar una senal de que el proceso sigue activo.
- Los cambios de texto de estado no deben desplazar botones ni controles primarios. Reservar una zona de estado de tamano estable o usar un layout que mantenga las acciones siempre en la misma posicion.
- Emitir en la consola etapas utiles del proceso cuando existan fases reconocibles.
- No inventar porcentajes: usar porcentaje solo cuando exista una medida real del avance; en caso contrario usar progreso indeterminado o mensajes por etapa.
- Mantener la geometria FreeCAD en el hilo seguro de la aplicacion; no introducir hilos secundarios solo para aparentar respuesta de GUI.
- Restaurar cursor, barra de estado y cualquier estado visual incluso cuando ocurra una excepcion.
- Preferir un helper reutilizable compartido antes que duplicar logica de feedback en cada comando.
