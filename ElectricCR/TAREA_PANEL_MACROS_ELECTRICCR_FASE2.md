# TAREA PANEL DE MACROS ELECTRICCR - FASE 2

Fecha/hora: 2026-08-12 11:39 America/Costa_Rica
FreeCAD objetivo: 1.1.3
Estado inicial: FASE 1 IMPLEMENTADA Y VALIDADA VISUALMENTE POR MARCO
Estado final: FASE 2 IMPLEMENTADA / PROBADA TECNICAMENTE / VALIDADA VISUALMENTE EN MCP

Correccion posterior verificada: el comentario se guarda contra la macro
anterior al cambiar de seleccion y la busqueda reutiliza las filas cacheadas.

## Tarea actual

Convertir el Panel de macros ElectricCR en un inventario vivo de herramientas,
con descripcion funcional, comentarios de revision, estado manual, registro
legible por GPT/Codex y estadisticas que separen uso real de pruebas.

La Fase 1 ya funciona visualmente y debe conservarse: busqueda, filtros,
iconos, estadisticas, modo Diagnostico, detalles, copiar ruta, copiar
diagnostico y persistencia de interfaz.

## 1. Fuentes que deben revisarse antes de modificar codigo

Reconstruir el estado actual antes de programar. Revisar como minimo:

- `ElectricCR/commands/macro_launcher.py`
- `ElectricCR/commands/macros.py`
- `ElectricCR/usage_log.py`
- `ElectricCR/REVISION_MACROS.md`
- `ElectricCR/MEJORAS_PENDIENTES.md`
- `ElectricCR/RESULTADO_CODEX.md`
- `ElectricCR/ESTADO_PROYECTO.md`
- tarea anterior del Panel si existe en el repositorio;
- `Inventario_Clasificacion_ElectricCR_2026-08-08.xlsx`, si esta disponible en
  la copia local de trabajo.

El inventario Excel de 2026-08-08 contiene 152 elementos y campos como:

- Grupo
- Archivo
- Familia / funcion
- Rol funcional
- Madurez
- Resultado comprobado
- Visibilidad recomendada
- Prioridad
- Riesgo de retiro
- Uso conocido
- Ultimo uso
- Dependencias / solapamientos
- Accion recomendada
- Confianza
- Observacion tecnica
- Fuente

IMPORTANTE: el Excel es una base historica, no la verdad final. Algunas
clasificaciones fueron revisadas despues del 2026-08-08. Aplicar esta
precedencia:

1. codigo y estado actual del repositorio;
2. decisiones mas recientes documentadas en `MEJORAS_PENDIENTES.md`,
   `REVISION_MACROS.md`, `RESULTADO_CODEX.md` y tareas recientes;
3. inventario Excel como fuente de contexto y clasificacion historica;
4. inferencia nueva solo despues de leer la macro/codigo relacionado.

No retirar ni archivar automaticamente una macro porque el Excel antiguo lo
recomiende.

## 2. Investigacion previa obligatoria

Antes de implementar, revisar si FreeCAD, Addon Manager, FreeCAD-macros u otro
componente oficial ya ofrece un patron reutilizable para metadatos de macros,
descripciones, ayuda o catalogos.

Tomar como referencia, sin copiar innecesariamente, el patron oficial de
metadatos de macros de FreeCAD (`__Name__`, `__Comment__`, `__Help__`,
`__Status__`, `__Requires__`, `__Icon__`, etc.).

Para Qt/PySide6, usar APIs estandar para expandir/contraer arboles y persistir
estado. No crear soluciones caseras si `QTreeWidget`, `QSettings` u otras APIs
Qt ya resuelven el problema.

## 3. Catalogo estructurado de macros

Crear un registro estructurado versionado dentro de ElectricCR.

Ruta recomendada:

`ElectricCR/data/macros_catalog.json`

La ruta relativa de la macro debe ser la clave estable principal, por ejemplo:

`Deteccion/ColocarDetectores_Poligonos_NFPA.FCMacro`

El JSON debe tener version de esquema y fecha de actualizacion.

Por cada macro/herramienta guardar, cuando exista informacion confiable:

- `path`
- `name`
- `group`
- `description`
- `description_source`
- `comment`
- `manual_status`
- `decision`
- `role`
- `maturity`
- `verified_result`
- `recommended_visibility`
- `priority`
- `retirement_risk`
- `dependencies`
- `recommended_action`
- `confidence`
- `technical_note`
- `source`
- `last_reviewed`

No duplicar en este JSON estadisticas de ejecucion que ya pertenecen a
`usage_log.py`, salvo referencias/resumen estrictamente necesario para exportar
reportes.

### Valores manuales sugeridos

`manual_status`:

- `SIN_REVISAR`
- `REVISAR`
- `REVISADA`

`decision`:

- `SIN_DECISION`
- `MANTENER`
- `MEJORAR`
- `MOVER`
- `FUSIONAR`
- `OCULTAR`
- `ARCHIVAR`

No ejecutar ninguna decision destructiva desde el Panel. El registro es
informacion, no autorizacion para borrar/mover archivos.

## 4. Descripcion de que hace cada macro

Cada herramienta debe poder mostrar una descripcion corta y objetiva de su
funcion.

No usar `Accion recomendada` ni `Comentario` como descripcion funcional.

Orden de fuentes recomendado:

1. descripcion manual ya guardada en `macros_catalog.json`;
2. metadato oficial `__Comment__` / `__Help__`, si existe;
3. encabezado existente `# Description:` u otro encabezado equivalente;
4. `ToolTip` / `MenuText` del comando;
5. informacion util del Excel (`Familia / funcion`, `Observacion tecnica`);
6. si sigue siendo insuficiente, analizar el codigo de la macro y dependencias
   para redactar una descripcion de 1 a 3 frases.

Guardar `description_source`, por ejemplo:

- `manual`
- `macro_metadata`
- `header`
- `tooltip`
- `excel`
- `code_review`

No inventar comportamiento que el codigo o las fuentes no respalden.

### Migracion inicial

Usar el Excel como semilla, pero reconciliar cada entrada con las rutas
actuales. No crear duplicados solo porque el nombre cambie o una macro haya
sido movida.

Las herramientas activas registradas por ElectricCR y las entradas historicas
no activas deben poder coexistir en el catalogo. El Panel puede mostrar por
defecto las activas y ofrecer filtros para historicas/ocultas cuando sea
apropiado.

## 5. Catalogo Markdown para lectura humana y Codex

Generar tambien:

`ElectricCR/MACROS_CATALOGO.md`

Este archivo debe derivarse del JSON, no convertirse en una segunda fuente de
verdad editable manualmente.

Agrupar por Grupo e incluir como minimo:

- herramienta;
- ruta;
- descripcion;
- comentario;
- estado manual;
- decision;
- clasificacion tecnica principal;
- observacion/recomendacion cuando exista.

Incluir al inicio fecha de generacion y version del esquema JSON.

Crear una funcion/helper pequeno que regenere el Markdown de forma
determinista cuando cambie el catalogo.

## 6. Comentarios por macro desde el Panel

Agregar al panel de detalles un campo editable `Comentario` para la herramienta
seleccionada.

Requisitos:

- multilinea;
- cargar automaticamente el comentario existente;
- guardar de forma segura en `macros_catalog.json`;
- no perder cambios al cambiar de seleccion o cerrar el dialogo;
- proporcionar boton `Guardar comentario` o un mecanismo de autosave claro;
- registrar fecha de revision;
- una escritura fallida debe mostrar aviso en consola y no destruir el JSON.

Usar escritura atomica (archivo temporal + reemplazo) o estrategia equivalente.

## 7. Estado/decision manual

Agregar controles sencillos para editar:

- Estado manual: Sin revisar / Revisar / Revisada.
- Decision: Sin decision / Mantener / Mejorar / Mover / Fusionar / Ocultar /
  Archivar.

Estos campos NO sustituyen el diagnostico automatico `OK / REVISAR / ERROR`.
Mostrar claramente ambos conceptos por separado:

- estado tecnico automatico;
- estado/decision humana.

## 8. Contraer y expandir grupos

Agregar botones visibles:

- `Contraer grupos`
- `Expandir grupos`

Objetivo: permitir ver rapidamente solo los nombres de grupos y navegar por
ellos.

Comportamiento deseado:

- Contraer grupos cierra todos los grupos del arbol.
- Expandir grupos abre todos.
- Al escribir una busqueda, expandir automaticamente solo los grupos con
  coincidencias utiles.
- No romper la persistencia existente del Panel.

## 9. Separar uso real de pruebas

El contador actual no debe usarse como evidencia fuerte durante la auditoria,
porque las pruebas manuales pueden inflarlo.

Evolucionar `usage_log.py` sin perder historial.

Clasificar nuevas ejecuciones como:

- `real`: uso normal desde barra, menu o boton `Ejecutar` del Panel;
- `test`: ejecucion deliberada mediante nuevo boton `Probar` o prueba tecnica;
- `legacy/unclassified`: conteos historicos anteriores a esta separacion.

No reclasificar retroactivamente conteos antiguos como uso real.

Conservar el conteo historico existente como dato no clasificado.

El Panel debe mostrar o poder mostrar:

- Uso real
- Pruebas
- Historico sin clasificar
- Ultimo uso real
- Ultima prueba

### Botones

- `Ejecutar`: cuenta como uso real.
- `Probar`: ejecuta la misma herramienta pero registra la ejecucion como prueba.

Las ejecuciones normales desde las barras/menu de ElectricCR cuentan como uso
real.

### Filtros

Revisar filtros para que no produzcan conclusiones engañosas.

Preferir:

- `Sin uso real registrado`
- `Con pruebas`
- `Nunca ejecutadas` solo cuando real=0, test=0 e historico=0
- `Con comentarios`
- `Pendientes de revisar`
- `Decision: Archivar`
- `Con Rayo`

No eliminar herramientas automaticamente por bajo uso.

## 10. Copiar diagnostico mejorado

Ampliar `Copiar diagnostico` para incluir, cuando corresponda:

- nombre;
- grupo/barra;
- ruta;
- comando;
- descripcion;
- fuente de descripcion;
- comentario del usuario;
- estado tecnico automatico;
- estado manual;
- decision;
- icono / estado del icono;
- uso real;
- pruebas;
- historico sin clasificar;
- ultimo uso real;
- ultima prueba;
- gestion de transaccion;
- dependencias/observacion tecnica resumida.

El texto debe ser limpio y util para pegar directamente en GPT/Codex.

## 11. Regla de Rayo.svg

Mantener la regla vigente:

- `Rayo.svg` NO significa error.
- Si no hay icono especifico confirmado, conservar Rayo.
- Marcar como `REVISAR` solamente cuando corresponda.
- No inventar iconos para satisfacer la auditoria.

## 12. Compatibilidad y seguridad

- FreeCAD objetivo: 1.1.3.
- Mantener compatibilidad razonable con PySide6 y la capa de compatibilidad
  existente cuando aplique.
- No modificar ni guardar `.FCStd` reales durante las pruebas.
- No eliminar macros, iconos ni recursos.
- No mover/archivar herramientas como efecto de editar `decision`.
- No cambiar la logica funcional de las macros inventariadas.
- No convertir el Excel en dependencia de runtime del Workbench.
- El Panel debe seguir abriendo aunque el catalogo JSON falte o este danado;
  usar fallback seguro y reportar en consola.
- Evitar rutas absolutas.

## 13. Pruebas minimas

Crear/ampliar smoke tests para verificar como minimo:

1. carga del catalogo JSON;
2. migracion/sembrado inicial sin duplicados;
3. descripcion y fuente de descripcion;
4. guardar/recuperar comentario;
5. escritura atomica y recuperacion ante JSON invalido;
6. estado manual y decision;
7. regeneracion determinista de `MACROS_CATALOGO.md`;
8. Contraer/Expandir grupos;
9. busqueda con expansion de coincidencias;
10. `Ejecutar` registra uso real;
11. `Probar` registra prueba;
12. conteo historico queda como no clasificado;
13. filtros nuevos;
14. `Copiar diagnostico` incluye descripcion/comentario/decision/estadisticas;
15. `Rayo.svg` sigue siendo REVISAR y no ERROR;
16. Panel sigue funcionando si JSON no existe o tiene error recuperable;
17. Undo/Redo del documento no debe verse afectado por el Panel;
18. ninguna prueba guarda un `.FCStd` real.

Realizar validacion GUI en FreeCAD 1.1.3 con herramientas reales, no solo un
comando Dummy.

## 14. Documentacion a actualizar

Actualizar como minimo:

- `ElectricCR/MEJORAS_PENDIENTES.md`
- `ElectricCR/REVISION_MACROS.md`
- `ElectricCR/RESULTADO_CODEX.md`
- `ElectricCR/ESTADO_PROYECTO.md`
- `ElectricCR/TAREA_PANEL_MACROS_ELECTRICCR_FASE2.md` si esta tarea se copia al
  repositorio;
- memoria de sesion correspondiente.

Documentar claramente:

- cantidad de entradas migradas del Excel;
- cantidad reconciliada con herramientas activas;
- entradas historicas no activas;
- descripciones por fuente;
- comentarios/estados conservados;
- cambios de esquema de `usage_log.py`;
- pruebas ejecutadas y resultado.

## 15. Git

NO hacer `commit`, `push`, merge, rebase ni borrar ramas.

Dejar los cambios locales listos para revision de Marco y GPT.

## Criterio de finalizacion

La tarea se considera tecnicamente completada cuando:

- el Panel conserva toda la funcionalidad de la Fase 1;
- existe `macros_catalog.json` con datos reconciliados y comentarios editables;
- existe `MACROS_CATALOGO.md` generado desde el JSON;
- cada herramienta activa puede mostrar una descripcion o indicar claramente
  que sigue sin descripcion;
- los comentarios y decisiones sobreviven al cierre/reapertura;
- hay Contraer/Expandir grupos;
- uso real, pruebas e historico no clasificado estan separados;
- `Copiar diagnostico` incluye la nueva informacion;
- los smoke tests pasan;
- Marco puede validar visualmente el Panel real en FreeCAD 1.1.3.
