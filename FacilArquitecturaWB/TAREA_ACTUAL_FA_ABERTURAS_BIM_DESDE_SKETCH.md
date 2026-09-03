# TAREA_ACTUAL - FA Aberturas BIM desde Sketch

Fecha y hora: 2026-08-12 17:55 -06:00
Proyecto: Macros-de-Freecad / FacilArquitecturaWB
FreeCAD objetivo: 1.1.3
Estado inicial: PENDIENTE DE EJECUCION
Prioridad: Alta

## Objetivo

Implementar en Facil Arquitectura una herramienta nueva para crear **aberturas BIM reales en muros, sin puerta ni ventana**, a partir de uno o varios Sketches fuente.

Nombre visible recomendado:

`FA Aberturas BIM desde Sketch`

Nombre interno recomendado:

`FA_CreateOpeningsFromSketch`

Codex puede ajustar el nombre interno si existe una convencion mejor en el Workbench, pero debe mantener el nombre visible claro y coherente con los comandos actuales de puertas y ventanas.

## Regla funcional principal

En Facil Arquitectura se adopta esta regla general:

`1 Sketch = 1 tipo/familia de elemento + N instancias`

Por tanto:

- un Sketch de puertas contiene lineas que representan puertas del mismo tipo/configuracion;
- un Sketch de ventanas contiene lineas que representan ventanas del mismo tipo/configuracion;
- un Sketch de aberturas contiene lineas que representan **solo vanos/buques**, sin hoja, marco ni ventana.

La herramienta de esta tarea procesa un Sketch de aberturas.

## Entrada

Aceptar uno o varios `Sketcher::SketchObject` seleccionados.

Cada Sketch puede contener **muchas lineas rectas**.

Cada linea representa una abertura independiente.

Para cada linea:

- el ancho de la abertura se obtiene de la longitud de la linea;
- la posicion se obtiene de la posicion real de la linea;
- la orientacion se obtiene de la propia linea;
- la altura se toma del dialogo;
- la altura desde piso se toma del dialogo;
- se busca automaticamente el muro BIM anfitrion.

No mezclar tipos dentro del mismo Sketch.

## Parametros del dialogo

Valores iniciales:

- `Altura`: 2100 mm.
- `Altura desde piso`: 0 mm.
- `Tolerancia para buscar muro`: reutilizar el criterio ya usado por puertas/ventanas, salvo que la implementacion actual justifique otro valor.
- `Reemplazar solamente aberturas creadas por este comando`: activado por defecto.

La altura de 2100 mm es **solo valor predeterminado** y debe poder variarse.

La altura desde piso tambien debe ser editable, aunque el uso normal de una abertura de paso sera 0 mm.

El ancho NO se introduce manualmente: cada linea del Sketch controla su propio ancho.

## Resultado geometrico

Crear **solo el buque/vano**.

No crear:

- hoja;
- marco;
- vidrio;
- simbolo de puerta;
- arco de giro;
- herrajes;
- objeto decorativo que simule el hueco.

El resultado debe producir un **corte real en el Wall BIM anfitrion**.

Preferir mecanismos BIM/Arch nativos de FreeCAD para `Opening Element` / `Opening only`, o el mecanismo nativo equivalente disponible en FreeCAD 1.1.3.

No implementar cortes booleanos propietarios de FA si FreeCAD ya ofrece el mecanismo BIM correcto.

El objeto debe conservar semantica BIM de abertura, host y trazabilidad.

## Investigacion obligatoria antes de programar

Antes de modificar codigo:

1. Leer `AGENTS.md`.
2. Activar/usar las skills requeridas por el repositorio, especialmente la skill de arquitectura FreeCAD si `AGENTS.md` la exige.
3. Revisar `TAREA_ACTUAL.md`, `ESTADO_PROYECTO.md`, `RESULTADO_CODEX.md`, `DOCUMENTACION_WORKBENCH.md` y README relacionados.
4. Buscar en Internet/documentacion oficial y codigo fuente actual de FreeCAD 1.1.x si existe ya:
   - `Opening only`;
   - `Opening Element`;
   - Arch/BIM Window sin marco/hoja;
   - comando o preset equivalente;
   - macro/workbench/plugin que haga aberturas desde ejes.
5. Documentar brevemente lo encontrado antes de escoger la implementacion.
6. Reutilizar APIs nativas antes que inventar una geometria propia.

Para preguntas tecnicas sobre FreeCAD, preferir fuentes primarias:
- documentacion oficial;
- repositorio oficial de FreeCAD;
- codigo fuente oficial.

## Revisar primero la implementacion existente de puertas y ventanas

No escribir esta herramienta desde cero sin estudiar los patrones ya probados.

Localizar y revisar como minimo los modulos/comandos actuales equivalentes a:

- puertas BIM desde Sketch;
- ventanas BIM desde Sketch;
- `opening_utils.py` o equivalente;
- deteccion de muro anfitrion;
- validacion de corte real;
- reemplazo seguro mediante `FA_GeneratedBy`;
- insercion dentro de Building/Level;
- organizacion del arbol;
- dialogos de puertas/ventanas;
- manejo de transacciones;
- logging `[FACILARQ]`.

Reutilizar el motor comun cuando sea adecuado.

Si el motor de puertas/ventanas ya abstrae "linea -> host -> opening", extenderlo limpiamente en vez de duplicarlo.

## Deteccion del muro anfitrion

Para cada linea del Sketch:

1. Convertir correctamente la geometria a coordenadas globales respetando `Placement`.
2. Calcular centro, direccion y longitud.
3. Buscar candidatos Wall BIM cercanos.
4. Validar geometricamente que la linea pertenece/cruza/se alinea con el muro correcto.
5. Evitar seleccionar muros cercanos pero incorrectos.
6. Si hay ambiguedad real, omitir esa linea y reportarla; no adivinar.
7. Si no se encuentra host, omitir esa linea y reportarla sin abortar necesariamente todas las demas.

Reutilizar el algoritmo ya probado por puertas y ventanas siempre que sea posible.

## Muchas lineas en un mismo Sketch

Requisito obligatorio.

Ejemplo:

```text
Sketch_Centros_Aberturas
|-- Linea 1 = 1200 mm
|-- Linea 2 = 900 mm
|-- Linea 3 = 1800 mm
`-- Linea N
```

Con:

```text
Altura = 2100 mm
Altura desde piso = 0 mm
```

debe crear N aberturas, cada una con su ancho individual segun la linea.

Todas las lineas del Sketch comparten la misma altura y altura desde piso configuradas en esa ejecucion.

## Uno o varios Sketches seleccionados

Si los comandos actuales de puertas/ventanas ya permiten varios Sketches fuente en una sola ejecucion y ese patron es estable, adoptar el mismo comportamiento.

Cada Sketch seleccionado representa un unico tipo/configuracion de abertura.

En esta primera version todos los Sketches procesados en la misma ejecucion pueden usar los mismos parametros del dialogo.

No mezclar automaticamente alturas distintas dentro de un mismo Sketch.

## Reemplazo seguro

Agregar una opcion equivalente a:

`Reemplazar solamente aberturas creadas por este comando`

Cuando esta activa:

- borrar/regenerar solo objetos con metadatos inequivocos de esta herramienta;
- no borrar puertas;
- no borrar ventanas;
- no borrar aberturas manuales;
- no borrar objetos historicos de Puriscal;
- no tocar objetos creados por otros comandos.

Usar metadatos claros, por ejemplo:

- `FA_GeneratedBy`;
- `FA_SourceSketch`;
- `FA_SourceGeometryIndex`;
- `FA_HostWall`;
- propiedades equivalentes segun la arquitectura existente.

## Parametricidad y actualizacion

El Sketch debe conservarse como fuente.

Objetivo minimo:

- si se cambia la geometria del Sketch y se vuelve a ejecutar el comando con reemplazo, las aberturas se actualizan sin duplicados;
- si se cambia la altura en el dialogo, las nuevas aberturas reflejan esa altura;
- si se cambia `Altura desde piso`, el hueco se desplaza verticalmente.

Si la arquitectura actual permite dependencias expresadas directamente sin comprometer estabilidad, aprovecharlas.

No forzar una refactorizacion grande si el patron actual de puertas/ventanas usa regeneracion segura.

## Arbol y semantica BIM

El resultado debe integrarse en el arbol BIM nativo y mantenerse compacto.

No crear grupos auxiliares visibles innecesarios.

Cada abertura puede aparecer como objeto BIM individual si FreeCAD lo requiere semanticamente, pero no deben aparecer Sketches auxiliares, cajas de corte ni objetos booleanos temporales visibles.

El objeto debe clasificarse correctamente como abertura/opening segun las propiedades IFC/BIM disponibles en FreeCAD 1.1.3.

## UI

Agregar el comando a Facil Arquitectura junto a las herramientas de puertas y ventanas.

Dialogo simple y consistente con la UI existente:

- Sketches fuente: cantidad.
- Muros BIM candidatos: cantidad, si ya existe esta informacion en otros dialogos.
- Altura: 2100 mm.
- Altura desde piso: 0 mm.
- Tolerancia para buscar muro.
- Reemplazo seguro.

Mensajes claros:

```text
[FACILARQ][ABERTURAS] Sketches fuente: 1
[FACILARQ][ABERTURAS] Lineas detectadas: 8
[FACILARQ][ABERTURAS] Aberturas creadas: 7
[FACILARQ][ABERTURAS] Lineas omitidas: 1
[FACILARQ][ABERTURAS] Host ambiguo para geometria 5
```

No bloquear toda la operacion por una unica linea fallida si las demas son validas.

## Rendimiento

Procesar por lotes.

Evitar `doc.recompute()` despues de cada abertura si no es necesario.

Preferir:

`leer Sketches -> analizar lineas -> precalcular hosts -> crear aberturas -> recompute final`

Si la operacion tarda perceptiblemente, usar el patron de progreso ya definido por Facil Arquitectura.

## Casos de prueba obligatorios

Crear pruebas automatizadas y, cuando sea posible, smoke tests en FreeCAD real para:

1. Un Sketch con 1 linea.
2. Un Sketch con muchas lineas.
3. Anchos diferentes en el mismo Sketch.
4. Altura predeterminada 2100 mm.
5. Altura modificada, por ejemplo 2400 mm.
6. Altura desde piso 0 mm.
7. Abertura elevada con altura desde piso distinta de 0.
8. Linea horizontal.
9. Linea vertical.
10. Linea diagonal.
11. Sketch con `Placement` trasladado.
12. Sketch con `Placement` rotado.
13. Muros BIM multiples.
14. Linea sin muro anfitrion.
15. Dos muros candidatos ambiguos.
16. Reejecucion con reemplazo sin duplicados.
17. Confirmar que puertas existentes no se borran.
18. Confirmar que ventanas existentes no se borran.
19. Confirmar que aberturas manuales no se borran.
20. Guardar, cerrar y reabrir FCStd.
21. Confirmar que el Wall queda realmente perforado.
22. Confirmar semantica IFC/BIM de Opening.
23. Regresion de comandos existentes de puertas y ventanas.

No reducir cobertura existente.

## Compatibilidad

No romper:

- `FA Puertas BIM desde Sketch`;
- `FA Ventanas BIM desde Sketch`;
- puertas dobles;
- plataforma de atencion;
- reconstruccion BIM;
- modelos historicos de Puriscal;
- modelos actuales de La Cruz.

No modificar ElectricCR, MEPWorkbenchCR ni GameEngineExportWB para esta tarea.

## Codigo

- FreeCAD 1.1.3.
- Python compatible con FreeCAD.
- Sin tildes ni caracteres especiales en identificadores, comentarios de codigo, nombres internos o strings que puedan intervenir en expresiones.
- Encabezado de los modulos nuevos con descripcion, instrucciones de mantenimiento, fecha/hora y version.
- Codigo bien comentado.
- Logging de depuracion en consola.
- Comandos GUI delgados.
- Logica reutilizable en `core/` cuando corresponda.
- Transacciones seguras.
- No modificar archivos ajenos.
- No eliminar codigo historico sin demostrar que ya no es necesario.
- Actualizar version/build siguiendo exactamente el esquema actual del Workbench.

## Icono

Antes de crear un icono nuevo:

1. revisar iconos existentes en FacilArquitecturaWB;
2. revisar recursos nativos de FreeCAD si es tecnicamente limpio reutilizarlos;
3. si se requiere uno nuevo, crear SVG simple y consistente con la barra actual.

Debe representar un vano/hueco en pared, no una puerta.

## Archivos/documentacion a actualizar

Como minimo, segun la arquitectura real encontrada:

- `FacilArquitecturaWB/InitGui.py`
- modulo/comando nuevo de aberturas;
- dialogo nuevo o reutilizado;
- core compartido si se extiende;
- icono si aplica;
- README;
- `DOCUMENTACION_WORKBENCH.md`;
- pruebas;
- version/build;
- `RESULTADO_CODEX.md` o el archivo de resultado indicado por `AGENTS.md`.

No asumir rutas absolutas del usuario. Usar rutas relativas al repositorio.

## Resultado Codex

Al terminar, actualizar el resultado del proyecto con:

- fecha y hora;
- objetivo;
- investigacion previa;
- archivos leidos;
- archivos modificados;
- arquitectura elegida;
- API nativa FreeCAD utilizada;
- como se representa el Opening;
- como se busca el host;
- como se maneja un Sketch con muchas lineas;
- como funciona el reemplazo seguro;
- pruebas ejecutadas;
- resultados;
- version/build resultante;
- pendientes reales;
- instrucciones exactas para recargar y probar en FreeCAD.

## Criterio de aceptacion

La tarea se aprueba cuando:

1. el usuario selecciona un Sketch con muchas lineas;
2. ejecuta `FA Aberturas BIM desde Sketch`;
3. indica una altura, con 2100 mm como valor inicial;
4. cada linea genera unicamente un vano real del ancho de esa linea;
5. cada abertura encuentra y perfora su Wall BIM correcto;
6. no se genera puerta, marco, hoja ni ventana;
7. la altura puede variarse;
8. la altura desde piso puede variarse;
9. la reejecucion no duplica objetos;
10. no se eliminan puertas, ventanas ni aberturas manuales;
11. el resultado es BIM nativo, editable y persistente al guardar/reabrir;
12. las herramientas actuales de puertas y ventanas siguen funcionando.

**No reinventar el sistema de openings. Reutilizar los mecanismos nativos de FreeCAD y los patrones ya validados en Facil Arquitectura.**
