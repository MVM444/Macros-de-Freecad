# TAREA - MEJORA DEL PANEL DE MACROS ELECTRICCR

Fecha/hora: 2026-08-12 10:17 America/Costa_Rica
FreeCAD objetivo: 1.1.3
Estado: IMPLEMENTADA / PROBADA TECNICAMENTE / VALIDADA VISUALMENTE EN MCP

## Objetivo

Mejorar `Panel de macros ElectricCR` para que siga siendo un lanzador rapido y sencillo, pero tambien sirva como herramienta de inspeccion y diagnostico de las herramientas registradas en ElectricCR.

La mejora debe priorizar la usabilidad diaria. La informacion tecnica adicional debe quedar disponible en un modo de diagnostico o panel de detalles, evitando convertir la vista normal en una tabla excesivamente ancha.

## Contexto actual a revisar

Antes de modificar codigo, reconstruir el estado LOCAL actual y no asumir que GitHub `main` contiene los ultimos cambios no publicados.

Revisar como minimo:

- `ElectricCR/commands/macro_launcher.py`
- `ElectricCR/commands/macros.py`
- `ElectricCR/usage_log.py`
- configuracion/preferencias existentes de ElectricCR que puedan reutilizarse para persistencia
- iconos actuales de `ElectricCR/icons/`
- `ElectricCR/MEJORAS_PENDIENTES.md`
- `ElectricCR/REVISION_MACROS.md`
- `RESULTADO_CODEX.md`
- `ESTADO_PROYECTO.md`

Preservar cualquier mejora local ya existente, en especial el icono propio del Panel si ya fue implementado. No regresar al icono `Rayo` si el Panel ya tiene un icono especifico valido.

## Investigacion previa obligatoria

Antes de implementar, revisar brevemente soluciones equivalentes del ecosistema FreeCAD y documentar que se reutiliza conceptualmente y que no.

Como referencia, el ecosistema oficial de macros/Addon Manager usa metadatos de macro, iconos, descripcion, estado y filtros de busqueda. No copiar el Addon Manager ni crear una dependencia con el; usarlo solo como referencia de presentacion y metadatos.

Tambien revisar si el proyecto ya tiene un patron de persistencia de preferencias. Preferir una solucion integrada con FreeCAD y compatible con recargas del Workbench.

## Alcance funcional - Fase 1

### 1. Vista normal mejorada

Mantener busqueda, agrupacion y doble clic para ejecutar.

Mostrar como minimo:

- primera columna: icono + nombre de herramienta;
- grupo/barra;
- cantidad de usos;
- ultimo uso.

El icono debe verse claramente, aproximadamente 24-32 px, sin romper temas claros/oscuros.

### 2. Ancho de columnas automatico y persistente

Comportamiento esperado:

- primera apertura sin preferencias guardadas: ajustar columnas al contenido con limites razonables;
- si el usuario cambia anchos manualmente: guardar los anchos;
- al volver a abrir el panel: restaurar esos anchos;
- agregar una accion simple `Ajustar columnas` para volver al autoajuste;
- si es sencillo y consistente con el patron de preferencias existente, persistir tambien tamano de ventana y/o posicion del divisor del panel de detalles.

No guardar configuraciones fragiles dependientes de indices si puede usarse una clave estable por nombre de columna.

### 3. Panel de detalles de la herramienta seleccionada

Agregar un panel inferior o lateral, compacto y redimensionable, que muestre datos utiles sin llenar la tabla principal.

Como minimo:

- nombre visible;
- grupo/barra efectiva;
- ruta relativa del archivo `.FCMacro` cuando aplique;
- ID del comando FreeCAD;
- icono resuelto;
- estado del icono: especifico / Rayo generico / sin resolver;
- cantidad de usos;
- primer uso si existe;
- ultimo uso si existe;
- tipo de transaccion si puede determinarse de forma segura: propia / wrapper ElectricCR / desconocida;
- existencia del archivo fuente.

Agregar acciones pequenas:

- `Ejecutar`;
- `Copiar ruta` cuando exista;
- `Copiar diagnostico`.

`Copiar diagnostico` debe generar texto legible listo para pegar en GPT/Codex, por ejemplo con nombre, grupo, archivo, comando, icono, usos y observaciones detectadas.

### 4. Modo Diagnostico

Agregar un control claro `Diagnostico` que permita ver informacion adicional sin afectar la vista normal.

En modo diagnostico se pueden mostrar columnas adicionales o indicadores para:

- estado general: OK / REVISAR / ERROR;
- icono: ESPECIFICO / RAYO / NO RESUELTO;
- archivo existe: SI / NO;
- toolbar/grupo efectivo;
- comando registrado.

Reglas importantes:

- usar `Rayo.svg` NO es por si solo un error;
- si la funcion o el icono apropiado son dudosos, mantener Rayo y marcar como pendiente/revisar, no inventar un icono;
- no mover, archivar ni renombrar macros automaticamente desde este panel;
- `REVISAR` es una observacion, no una falla de ejecucion.

### 5. Filtros utiles

Agregar filtros sencillos, sin hacer compleja la interfaz. Como minimo evaluar:

- Todas;
- Mas usadas;
- Nunca usadas;
- Con Rayo;
- Con problemas/errores de registro.

La busqueda actual por grupo/nombre debe continuar funcionando y combinarse correctamente con el filtro.

### 6. Reutilizar estadisticas existentes

Usar `ElectricCR/usage_log.py` como fuente de conteos y fechas. No crear un segundo sistema de estadisticas para la Fase 1.

La ausencia de uso NO significa que una macro deba eliminarse. Solo debe mostrarse como dato de auditoria.

### 7. Metadatos internos de herramientas

El Panel necesita mas informacion de la que hoy recibe como `grupo -> lista de comandos`.

Implementar la minima arquitectura necesaria para que el registro de macros exponga metadatos confiables al Panel, sin duplicar logica de resolucion.

El registro ya conoce o puede conocer durante el registro:

- comando;
- grupo/barra;
- ruta de macro;
- MenuText/Label;
- ToolTip;
- icono resuelto;
- si el icono termina siendo Rayo generico;
- encabezado `# Toolbar:`;
- informacion suficiente para determinar la gestion de transaccion.

Preferir una fuente unica de metadatos en el registro de comandos. El Panel no debe volver a escanear todo el repositorio si esa informacion ya fue resuelta por `commands/macros.py`.

Mantener compatibilidad con el contrato actual de `register_macro_launcher()` o migrarlo de forma controlada sin romper el arranque del Workbench.

## Fuera de alcance - dejar preparado para Fase 2

No implementar en esta tarea, salvo que sea trivial y no aumente riesgo:

- conteo de ejecuciones correctas vs. fallidas;
- almacenamiento estructurado de ultimo error;
- historial de errores por herramienta;
- edicion de metadatos desde el panel;
- mover macros entre carpetas desde la interfaz;
- crear o cambiar iconos automaticamente;
- reemplazar el sistema de registro de comandos completo.

Documentar estos puntos como Fase 2 futura.

## Compatibilidad y calidad

- FreeCAD objetivo: 1.1.3.
- Mantener compatibilidad Qt usada por el proyecto, priorizando PySide6 sin romper PySide2 cuando el codigo actual lo soporte.
- Evitar tildes/caracteres especiales en identificadores internos nuevos, nombres de propiedades y claves de preferencias.
- Mensajes de depuracion claros en consola con prefijo consistente, por ejemplo `[ElectricCR][MacroPanel]`.
- No introducir `disconnect()` generales de señales Qt que puedan retirar receptores ajenos.
- Evitar conexiones duplicadas al abrir/cerrar/reabrir el panel o recargar ElectricCR.
- Mantener el panel util incluso si `usage_log.py` no tiene datos o algun recurso de comando no puede resolverse.

## Pruebas requeridas

### Pruebas estaticas

- `py_compile` de todos los archivos modificados/creados.
- validar SVG/iconos referenciados por el Panel.
- verificar que no se introduzcan rutas absolutas de la computadora.

### Pruebas FreeCAD 1.1.3

Usar el flujo MCP definido por el proyecto si esta disponible.

Validar como minimo:

1. ElectricCR inicia sin errores nuevos.
2. El Panel abre y cierra varias veces sin duplicados ni warnings Qt nuevos.
3. La busqueda existente sigue funcionando.
4. Los iconos de las herramientas se muestran.
5. Los conteos/fechas de uso se muestran cuando existen y no fallan cuando faltan.
6. Los anchos de columna se autoajustan en primera apertura.
7. Cambiar anchos manualmente, cerrar y reabrir: se restauran.
8. `Ajustar columnas` restaura autoajuste y actualiza la preferencia de forma coherente.
9. El panel de detalles cambia al seleccionar herramientas distintas.
10. `Copiar ruta` y `Copiar diagnostico` funcionan.
11. El modo Diagnostico se activa/desactiva sin perder seleccion ni romper busqueda.
12. Filtros `Todas`, `Nunca usadas`, `Con Rayo` y los implementados combinan correctamente con la busqueda.
13. Un comando con icono especifico se reporta como tal.
14. Un comando con Rayo se reporta como RAYO/REVISAR, no como ERROR.
15. Un archivo faltante simulado o metadata invalida se reporta como ERROR sin cerrar FreeCAD.

### Resultado de la validacion visual 2026-08-12

La primera captura con solo las columnas Macro y Grupo correspondia a la
prueba segura: el test habia llamado `register_macro_launcher` con un grupo
aislado y habia sustituido `_MACRO_GROUPS` en memoria. El registro de metadatos
si conservaba las herramientas reales. El comando `ElectricCR_TestPanelSafe`
quedo tambien registrado en la sesion, pero no es una herramienta real.

Al reconstruir los grupos desde `get_registered_macro_metadata()` y activar
`ElectricCR_MacroLauncher`, el Panel real se comprobo en MCP con FreeCAD 1.1.3:
12 grupos, 122 herramientas, filtros, casilla Diagnostico, panel de detalles,
botones de ajuste/copia/ejecucion/cierre y modo diagnostico de 7 columnas.
La evidencia visual esta en
`C:\Users\marco\AppData\Local\Temp\ElectricCR_Panel_Real_Validation.png` y
`C:\Users\marco\AppData\Local\Temp\ElectricCR_Panel_Real_Diagnostic_Validation.png`.

No ejecutar macros potencialmente destructivas solo para probar el Panel. Si hace falta probar `Ejecutar`, usar un comando seguro o un documento temporal controlado.

## Documentacion al finalizar

Actualizar como minimo:

- `ElectricCR/MEJORAS_PENDIENTES.md`;
- `ElectricCR/REVISION_MACROS.md` si cambia el contrato de registro;
- `RESULTADO_CODEX.md`;
- `ESTADO_PROYECTO.md`;
- esta tarea con estado final.

Registrar claramente:

- archivos modificados/creados;
- decisiones de arquitectura;
- preferencias persistentes agregadas;
- pruebas realizadas y resultado;
- validacion MCP/GUI;
- cualquier parte que quede solo PROGRAMADA o PROBADA y no validada visualmente.

## Restricciones Git

No hacer `commit`, `push`, merge, rebase ni borrar ramas sin autorizacion expresa de Marco.
No borrar macros, iconos o recursos durante esta tarea.
No modificar archivos `.FCStd` reales del usuario; usar documentos temporales para pruebas.
