# ElectricCR - Auditoria y migracion documental controlada

Fecha: 2026-10-07 (America/Costa_Rica)
Estado: DIAGNOSTICO DOCUMENTAL; NO HAY MIGRACION OPERATIVA APROBADA
Alcance: solo ElectricCR. No se modifica codigo, macros, documentos FCStd ni el historial vigente.

## 1. Fuente primaria examinada

Google Drive (carpeta de trabajo con estructura ElectricCR):
https://drive.google.com/drive/folders/1-xvTG4Py-20TgdiWi84AHr7gDSC6JzOW

Esta carpeta es hija de una carpeta "Macros-de-Freecad" en Drive. Hay varias carpetas homonimas y respaldos: no asumir que cualquiera de ellas es la copia activa sin contrastar rutas, modificaciones y el entorno local.

Inventario de la carpeta examinada (nombre existente -> ID Drive):
- AGENTS.md -> 1Zy0mW33QXTDv4dkf9G3DsXg9jt2VHlBT (2026-09-22)
- ESTADO_PROYECTO.md -> 1Z0dM4j52f8JdcJ1-gLo2ysjSr8FtWdEn (2026-09-26)
- DECISIONES_TECNICAS.md -> 1IwDcsglrC83LUbawuJD5UgM7zemcmDKT (2026-09-22)
- TAREA_ACTUAL.md -> 14Uoc-joqvsb-ILK8ooynjRAJvrwL2In- (2026-09-22)
- RESULTADO_CODEX.md -> 1Mfg_vyYySI_o6qhD5hlGhZHw5tHqYTl- (2026-09-26)
- HISTORIAL_CAMBIOS.md -> 1XpmGDoXEIcmkJ1WivALAW8NcspLlqM8v (2026-09-14)
- MAPA_WORKBENCH.md -> 1ek_1pj4rW5OPqy367khId78rUEca2llR (2026-09-03)
- RECURRENT_NOTES.md -> 1Dx0d39VqBjCZBM0kI8RcqtqKsvGMjx2o (2026-09-10)
- REVISION_MACROS.md -> 1UlTLuZI5oz7UQThQBJO4Y_j39e3DfwFg (2026-09-03)
- MACROS_CATALOGO.md -> 1U5Jdm3WGMfScgbnp4-q43hwNv1cngBnj (2026-09-20)

Carpeta de contratos y disenos existentes:
https://drive.google.com/drive/folders/1ITAskj45k-KodjWCWZeOnDSGcGxrpLgp
- CONTRATO_ARBOL_SEMANTICO.md
- DISENO_OBJETO_ELECTROMECANICO_COMUN.md
- RESUMEN_DISPOSITIVO_ELECTROMECANICO.md
- DISENO_ADAPTADOR_IFC_A1.md
- informes TechDraw y visibilidad PLAN.

Repositorio GitHub consultado: MVM444/Macros-de-Freecad.
Sus documentos examinados en main no se toman como prueba de vigencia frente a Drive, que muestra revisiones posteriores. Cualquier sincronizacion futura debe comparar contenido, no sobrescribir Drive con una rama Git antigua.

## 2. Diagnostico

1. AGENTS.md tiene unas 17.7 kB y obliga a leer de entrada siete documentos antes del codigo: esto contradice la lectura selectiva deseada.
2. ESTADO_PROYECTO.md (aprox. 66.9 kB) mezcla el estado vigente con numerosos cierres historicos.
3. TAREA_ACTUAL.md (aprox. 138.2 kB) conserva multiples tareas que en su momento se denominaron "vigentes"; la primera es de 2026-09-22 y se refiere a tomacorrientes BIM multinivel + A1 por defecto.
4. RESULTADO_CODEX.md (aprox. 149.2 kB) tambien contiene intervenciones atribuidas a GPT y resultados de muchas tareas. No debe interpretarse como una sola prueba ni como garantia de validacion.
5. DECISIONES_TECNICAS.md (aprox. 19.2 kB) incluye dos encabezados DT-014: renumerar cuidadosamente al migrar sin perder referencias historicas.
6. MAPA_WORKBENCH.md y algunos otros documentos contienen descripciones antiguas de A1 "opt-in", mientras la decision del 2026-09-22 indica A1 por defecto para dispositivos nuevos.
7. Existe informacion de pruebas valiosa en RECURRENT_NOTES.md, tests, informes y RESULTADO_CODEX.md, pero falta un PRUEBAS.md breve con casos de regresion, evidencia, resultado y estado de validacion GUI.
8. Hay respaldos/carpeta homonimos de Drive; no borrar, fusionar ni renombrar basandose solamente en coincidencias de nombre.

## 3. Reglas vigentes que deben sobrevivir

- Objetivo FreeCAD 1.1.3 (segun AGENTS.md de Drive, 2026-09-22).
- Dispositivo electromecanico comun A1: implementacion canonica en ElectricCR/electriccr/features/electromechanical_device.py.
- ElectricCR/electriccr/features/objeto_toma_uno.py es shim legacy: no agregarle funcionalidad nueva.
- Para dispositivos nuevos, A1 es el contrato por defecto desde 2026-09-22; no migrar automaticamente objetos legacy.
- Owner A1 / App::Link conserva identidad; PLAN es representacion documental auxiliar, no miembro de grupos de usuario.
- BIM nativo es autoridad de niveles, y Space/Host/relaciones semanticas gobiernan la asignacion; el arbol visible es proyeccion.
- No sustituir un cambio de codigo o pruebas puras por validacion visual/funcional real.
- La aceptacion depende de pruebas reales en FreeCAD 1.1.3 y revision posterior.
- No modificar archivos originales de Chomes, Upala u otros proyectos como parte de una auditoria.
- Las macros ya funcionales y sus contratos deben preservarse.

## 4. Estado verificable de interes (documentos Drive, no revalidado ahora)

- La cabecera mas reciente de ESTADO_PROYECTO.md (2026-09-25) identifica un hotfix candidato en plan_level_visibility.py v0.1.1 para visibilidad PLAN por Building Storey, con pruebas aisladas PASS y validacion grafica en copia de Chomes pendiente.
- El estado anterior (2026-09-23) describe TechDraw por sistema implementado en Drive con prueba real en FreeCAD pendiente.
- La tarea principal en la cabecera de TAREA_ACTUAL.md (2026-09-22) se enfoca en InstalarTomacorrientesEnParedesBIM.FCMacro para multinivel + A1 default; no consta cierre de la tarea en el tramo de referencia examinado.
- La validacion del usuario del 2026-09-14 declara que Alinear en planta v0.2 funciona para la prueba visual realizada; no implica que Undo/Redo y otros casos hayan sido comprobados.

Estas entradas NO prueban que la herramienta este actualmente operativa en el FreeCAD del usuario. Antes de cerrar o implementar, comprobar resultado real y version/codigo cargados.

## 5. Organizacion objetivo (sin duplicar autoridad)

ElectricCR/
  AGENTS.md       reglas permanentes y mapa de lectura selectiva
  ARQUITECTURA.md  arquitectura vigente, interfaces y referencias a contratos
  ESTADO.md        resumen corto: operativo / en prueba / falla / pendiente, evidencia
  DECISIONES.md    decisiones de largo plazo con ID unico
  TAREAS.md        solo trabajos activos, alcance, responsables y aceptacion
  PRUEBAS.md       matriz de regresion manual/automatica vinculada a tests
  (fuentes historicas y reportes existentes conservados hasta migracion validada)

Politica de autoridad:
- Cada dato debe tener una sola ubicacion operativa. Los documentos historicos dejan de ser editables como "estado vigente" una vez cerrada la migracion.
- ESTADO.md resume el estado, no copia la cronologia completa.
- PRUEBAS.md contiene IDs, escenarios, verificacion objetiva, estado y enlaces; no copia scripts.
- TAREAS.md solo conserva tareas abiertas. Resultados y cronologias quedan en archivos historicos.
- AGENTS.md debe ser breve. Lectura por defecto: AGENTS.md + encabezado de ESTADO.md + tarea concreta de TAREAS.md; ARQUITECTURA/DECISIONES/PRUEBAS se leen solo en las secciones necesarias.

## 6. Plan de migracion in-place para Codex / entorno con escritura Drive

Etapa A - respaldo y trazabilidad (sin mutaciones):
1. Verificar que la carpeta Drive listada corresponde al proyecto vigente y que la copia local/OneDrive coincide.
2. Registrar ID, hash, fecha y enlaces de los documentos existentes.
3. Comparar el codigo real en Drive, GitHub y la estacion; nunca asumir que GitHub main es mas reciente.
4. Detectar todas las referencias cruzadas a los nombres actuales (AGENTS, tareas, scripts, guias, README).

Etapa B - extraccion y validacion:
1. Preparar resumentes cortos para los seis documentos objetivo con secciones e IDs estables.
2. Obtener ESTADO.md de la situacion mas reciente verificable, conservando etiquetas VALIDADO / PENDIENTE / FALLO.
3. Construir ARQUITECTURA.md desde codigo y contratos A1 vigentes, no desde el antiguo resumen "opt-in".
4. Extraer de RECURRENT_NOTES, tests e informes una matriz PRUEBAS.md; no inventar resultados.
5. Decidir si el renombrado de cada documento existente conserva su identidad o si conviene convertir el archivo anterior a historico y crear el resumen nuevo. No operar sin actualizar sus referencias.

Etapa C - migracion atomica:
1. Actualizar AGENTS.md existente in-place y sus rutas hacia documentos nuevos.
2. Crear/renombrar/actualizar documentos dentro de la misma carpeta, manteniendo identidades en los archivos reutilizados.
3. Cambiar referencias cruzadas en una sola tarea controlada. Preservar contenido historico y enlaces.
4. No eliminar archivos antiguos hasta verificar lectura por Codex y conservar sus IDs o copias historicas.
5. Dejar constancia de que RESULTADO_CODEX y HISTORIAL_CAMBIOS son fuentes de evidencia historica, no alternativas a ESTADO.

Etapa D - prueba funcional de la gobernanza:
1. Abrir una sesion nueva de Codex y pedir que identifique, sin historial de chat, la arquitectura A1 vigente y la fuente de verdad.
2. Pedir que enumere una tarea abierta sin tratar historicos como vigentes.
3. Pedir los criterios de regresion para visibilidad PLAN por nivel, TechDraw por sistema y tomacorrientes multinivel.
4. Comprobar que el agente no exige leer los historicos completos de entrada ni propone cambiar el shim legacy.
5. Confirmar Drive actualizado, repositorio sincronizado, commit Git y solo despues cerrar la tarea documental.

## 7. Criterios de aceptacion

- Seis documentos operativos cortos, sin perdida de informacion historica.
- Referencias internas correctas y sin documentos rivales que reclamen la misma autoridad.
- FreeCAD 1.1.3 y contrato A1 actual correctamente identificados.
- PRUEBAS.md distingue prueba automatica, prueba GUI real y aceptacion del usuario.
- Estado de Chomes PLAN y TechDraw no se convierte falsamente en "funciona" sin pruebas nuevas.
- AGENTS.md instruye lectura progresiva y rutas a detalles cuando hagan falta.
- Ningun codigo funcional ni FCStd modificado durante esta reorganizacion.

## 8. Limites de esta auditoria

Este archivo es un informe temporal de migracion, no es un nuevo ESTADO.md ni una fuente operativa alternativa. Se genero con lecturas de Drive y GitHub; no se verifico FreeCAD local ni MCP en esta etapa. Los archivos de Drive NO han sido renombrados o reemplazados por esta auditoria. La migracion in-place corresponde a la fase siguiente tras establecer un mecanismo de edicion que conserve los IDs originales y actualice sus referencias.
