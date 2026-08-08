# ElectricCR - Revision macro por macro

**Proposito:** Registrar de forma persistente la revision funcional de cada macro antes de decidir si se incorpora al Workbench, permanece como macro, se fusiona, se archiva o se excluye.

**Version:** 2026-08-08 15:24, America/Costa_Rica.

## Principio

No se debe asumir que Marco recuerda que hace cada macro ni por que fue creada.

Codex debe reconstruir primero el contexto tecnico de cada herramienta utilizando codigo, documentacion, historial, pruebas y relaciones con otras macros.

El usuario aporta principalmente la validacion funcional que no puede deducirse del repositorio: uso real, resultado esperado, comportamiento visual y decisiones historicas no documentadas.

## Metodo de revision

Las macros se revisan una por una, pero siempre dentro de su familia funcional para detectar:

- duplicacion;
- solapamiento;
- reemplazos historicos;
- dependencias;
- capacidades unicas;
- intentos experimentales;
- desviaciones del objetivo original.

Antes de decidir el destino de una macro, responder como minimo:

1. Que problema pretendia resolver originalmente.
2. Que hace realmente el codigo actual.
3. Que objetos crea o modifica.
4. Que entradas requiere y que salida produce.
5. Que otras macros o modulos hacen algo parecido.
6. Si otras herramientas dependen de ella.
7. Si existe evidencia de uso real.
8. Si existe evidencia de pruebas solamente de desarrollo.
9. Si produce el resultado esperado.
10. Si tiene alguna capacidad unica que deba conservarse.
11. Si debe ser visible para el usuario final.
12. Si merece migrarse a codigo propio del Workbench.

## Tres ejes de clasificacion

Mantener los tres ejes ya adoptados:

### Rol funcional

- NUCLEO
- OPERATIVA
- SOPORTE
- ESPECIALIZADA
- MANTENIMIENTO
- SISTEMA

### Madurez

- ESTABLE
- ACTIVA
- CANDIDATA
- BETA
- REVISAR
- REVISAR-SOLAPAMIENTO
- REVISAR-INTEGRIDAD
- LEGACY-DEPENDENCIA
- LEGACY-REEMPLAZADA
- DESARROLLO
- ARCHIVADA / ARCHIVABLE

### Resultado comprobado

- COMPROBADA
- COMPROBADA-PARCIAL
- PROMETEDORA
- EXPERIMENTAL
- DESVIADA
- DUPLICADA
- INCOMPLETA
- FALLIDA
- ABANDONADA
- POR VERIFICAR
- NO APLICA

## Decision ElectricCR

Agregar una decision independiente de los tres ejes anteriores.

Valores permitidos:

- `INCORPORAR`: merece convertirse en comando o modulo propio del Workbench.
- `INCORPORAR DESPUES`: es util, pero depende de consolidacion, validacion o migraciones previas.
- `MANTENER COMO MACRO`: sigue siendo util, pero por ahora no justifica migracion.
- `EXPERIMENTAL`: se conserva en laboratorio/desarrollo y no debe formar parte del flujo productivo normal.
- `FUSIONAR`: su capacidad debe integrarse con otra herramienta antes de decidir su retiro.
- `LEGACY`: se conserva por compatibilidad o dependencia.
- `RESPALDO`: ya no debe formar parte del flujo normal, pero se conserva historicamente.
- `EXCLUIR`: no debe aparecer en ElectricCR productivo.
- `DESCARTABLE`: no aporta funcionalidad que justifique mantenerla activa; cualquier eliminacion requiere respaldo y autorizacion.
- `POR VERIFICAR`: falta evidencia suficiente para decidir.

## Regla de seguridad

El inventario previo es una preclasificacion tecnica. No equivale automaticamente a una decision definitiva de Marco.

No convertir `CANDIDATA`, `PROMETEDORA`, `REVISAR`, `POR VERIFICAR` o `REVISAR-SOLAPAMIENTO` en `INCORPORAR` sin completar la revision correspondiente.

No convertir `DUPLICADA`, `FALLIDA`, `DESVIADA`, `ABANDONADA` o `LEGACY-REEMPLAZADA` en eliminacion fisica sin respaldo y autorizacion expresa.

## Registro por herramienta

Para cada macro revisada agregar una entrada con esta estructura:

```text
### <ruta/archivo.FCMacro>

Familia:
Objetivo original:
Funcion real confirmada:
Entradas:
Salidas / objetos modificados:
Herramientas relacionadas:
Dependencias:
Uso conocido:
Pruebas conocidas:
Validacion de Marco:

Rol funcional:
Madurez:
Resultado comprobado:
Decision ElectricCR:
Destino o reemplazo:
Confianza:

Motivo de la decision:
Pendientes:
Fecha de revision:
```

## Estado de revision por familias

| Familia | Estado | Observacion |
|---|---|---|
| Areas | PENDIENTE DE REVISION DETALLADA | Primera familia recomendada para establecer el metodo definitivo. |
| Objetos | PENDIENTE | Revisar despues de Areas. |
| Iluminacion | PENDIENTE | Tiene varias herramientas ya documentadas como activas y legacy. |
| Tomacorrientes | PENDIENTE | Comparar insercion, etiquetas, organizacion y rotacion. |
| Deteccion | PENDIENTE | Revisar variantes NFPA y relacion con Areas. |
| Cajas | PENDIENTE | Revisar despues de Deteccion/Tomacorrientes. |
| Tableros / Configuracion | PENDIENTE | Revisar comandos de tablero, calculo y organizacion. |
| Conectar | EN REVISION - ALTA COMPLEJIDAD | Revisar por familias funcionales; Alimentadores tiene prioridad especial. |

## Notas funcionales confirmadas por Marco

### Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro

Familia: Conectar / Alimentadores

Confirmacion de Marco:

- Esta macro es IMPORTANTE dentro del flujo de conexiones.
- No debe tratarse como una variante secundaria, descartable o reemplazada solamente por ser antigua o por no localizarse facilmente en el `main` actual.
- Antes de cualquier limpieza, migracion o fusion, Codex debe reconstruir su arquitectura completa y verificar su presencia real en la copia local, ramas, respaldos y GitHub.

Evidencia tecnica ya documentada:

- Existe `Conectar/DOCUMENTACION_ALIMENTADORES_TABLERO.md` con una documentacion extensa del flujo.
- La documentacion describe una arquitectura de tres piezas:
  1. `Conectar_Alimentadores_a_Tablero_Auto.FCMacro` como interfaz y orquestacion.
  2. `alimentadores_backend.py` como backend especializado.
  3. `Conectar_Cajas_a_Tablero_Auto.FCMacro` como backend legado que contiene parte de la logica geometrica estable reutilizada.
- La documentacion de cierre del 2026-03-19 indica un estado funcional general bueno y que la etapa se considero concluida, aunque con mejoras futuras posibles de interfaz y mantenibilidad.

Clasificacion definitiva: PENDIENTE DE REVISION DETALLADA.

Decision ElectricCR: POR VERIFICAR.

Regla especial: no eliminar, ocultar permanentemente, fusionar ni migrar esta familia hasta reconstruir y validar primero el flujo funcional completo.

Fecha de nota: 2026-08-08.

## Registro de decisiones confirmadas

Todavia no asumir decisiones definitivas solamente a partir del inventario general.

Las decisiones se agregaran aqui conforme Marco, GPT y Codex revisen cada herramienta con evidencia suficiente.

## Relacion con el inventario

El inventario externo contiene una clasificacion amplia de herramientas y sirve para priorizar la auditoria.

`REVISION_MACROS.md` es el registro de decisiones funcionales confirmadas durante la depuracion y migracion.

Cuando una decision se confirme:

1. actualizar esta ficha;
2. actualizar el inventario cuando corresponda;
3. actualizar `MAPA_WORKBENCH.md` si cambia la arquitectura o el flujo principal;
4. actualizar `RESULTADO_CODEX.md` si la decision forma parte de una tarea activa;
5. actualizar `HISTORIAL_CAMBIOS.md` solamente cuando exista un cambio funcional aceptado.

## Regla para Codex al comenzar una revision

Antes de preguntarle a Marco que hace una macro, Codex debe inspeccionarla y presentar un resumen breve con esta forma:

```text
Lo que puedo confirmar por el codigo:
- ...

Herramientas relacionadas encontradas:
- ...

Lo que todavia no puedo saber por el repositorio:
- ...

Necesito de Marco solamente confirmar:
- uso real;
- resultado esperado;
- si existe alguna razon historica no documentada para conservarla.
```

El objetivo es reducir la carga de memoria del usuario y convertir el repositorio en la memoria operativa del proyecto.
