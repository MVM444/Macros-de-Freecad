# ElectricCR - Flujo de trabajo GPT-Codex

**Proposito:** Definir el ciclo obligatorio de reconstruccion de contexto, analisis, revision, implementacion, prueba, validacion y aceptacion de cambios realizados con ChatGPT, Codex u otros agentes.

**Version:** 2026-08-08 13:01, America/Costa_Rica.

## Principio general

Una herramienta nueva no es automaticamente una mejora.

```text
"Nueva" no significa "mejor".
"Ejecuta sin errores" no significa "resuelve el problema".
La solucion que permanece debe ser la que mejor funcione en el trabajo real.
```

El proyecto debe distinguir siempre entre:

- codigo que existe;
- codigo que ejecuta;
- codigo probado tecnicamente;
- solucion validada funcionalmente;
- solucion aceptada para integracion definitiva.

El repositorio debe funcionar como memoria operativa del proyecto. Marco no debe tener que reconstruir de memoria como funciona ElectricCR en cada nueva sesion.

## Flujo obligatorio

### 0. Reconstruccion del contexto

Antes de analizar una macro, desarrollar codigo o preguntarle al usuario como funciona una parte de ElectricCR, Codex debe:

1. Leer los archivos definidos en el orden obligatorio de `AGENTS.md`.
2. Leer `MAPA_WORKBENCH.md` para reconstruir la arquitectura vigente.
3. Leer `REVISION_MACROS.md` para conocer decisiones confirmadas y pendientes.
4. Inspeccionar el codigo real de la familia o herramienta involucrada.
5. Buscar dependencias, herramientas relacionadas y versiones anteriores cuando sean relevantes.
6. Presentar un resumen breve de lo que puede confirmar por evidencia tecnica.
7. Separar claramente hechos confirmados, inferencias y preguntas que realmente requieran conocimiento de Marco.

Codex no debe preguntarle al usuario que hace una macro antes de inspeccionar su codigo, salvo que el archivo no pueda localizarse o la informacion funcional no pueda deducirse razonablemente.

### 1. GPT analiza y define la tarea

GPT organiza el contexto historico y tecnico antes de pedir cambios.

La tarea debe describirse en `TAREA_ACTUAL.md` como un problema a resolver, no solamente como la instruccion de crear una macro nueva.

Antes de programar debe determinarse:

- cual es el objetivo funcional original;
- que herramienta actual intenta resolverlo;
- si existe una macro anterior que pueda corregirse o ampliarse;
- que otros archivos, modulos o Workbenches se relacionan con el problema;
- como se verificara que la solucion realmente mejora el trabajo real.

### 2. Busqueda previa obligatoria

Antes de crear una macro, comando, modulo o variante nueva se debe:

1. Buscar dentro del repositorio si ya existe una solucion total o parcial.
2. Revisar versiones anteriores, documentacion y resultados relacionados.
3. Revisar especialmente `ElectricCR`, `MEPWorkbenchCR` y macros de la misma familia funcional.
4. Buscar en Internet si FreeCAD, un Workbench, macro, plugin o patron oficial ofrece una solucion similar.
5. Preferir corregir, ampliar o reutilizar una herramienta existente cuando sea tecnicamente razonable.

Si se decide crear una nueva variante, Codex debe explicar por que era necesaria y que mejora funcional concreta pretende aportar.

### 3. Revision macro por macro antes de migrar

Durante la depuracion y migracion del Workbench, cada macro debe revisarse dentro de su familia funcional antes de convertirla a codigo propio de ElectricCR.

Para cada herramienta Codex debe reconstruir y documentar:

- objetivo original;
- funcion real confirmada por el codigo;
- entradas y salidas;
- objetos creados o modificados;
- herramientas relacionadas;
- dependencias;
- uso conocido;
- pruebas conocidas;
- capacidades unicas;
- resultado funcional conocido;
- aspectos que requieren validacion de Marco.

La decision debe registrarse en `REVISION_MACROS.md` utilizando uno de estos destinos:

- INCORPORAR
- INCORPORAR DESPUES
- MANTENER COMO MACRO
- EXPERIMENTAL
- FUSIONAR
- LEGACY
- RESPALDO
- EXCLUIR
- DESCARTABLE
- POR VERIFICAR

El inventario general sirve para priorizar la revision, pero no constituye por si solo una decision definitiva.

No convertir automaticamente las macros actuales a comandos Python.

### 4. Implementacion por Codex

Codex puede trabajar:

- directamente sobre la copia local del proyecto; o
- sobre una rama sincronizada con GitHub cuando el trabajo sea remoto.

Durante la implementacion:

- respetar `AGENTS.md`, `MAPA_WORKBENCH.md`, `DECISIONES_TECNICAS.md`, `REVISION_MACROS.md` y `TAREA_ACTUAL.md`;
- evitar crear herramientas paralelas sin justificacion;
- mantener cambios pequenos, reversibles y verificables;
- conservar compatibilidad con soluciones anteriores mientras la nueva no haya sido validada;
- no continuar desarrollando una solucion que se haya desviado del objetivo sin documentar primero esa desviacion.

En la migracion macro-a-codigo, preferir extraer la logica util a modulos Python reutilizables y mantener temporalmente un envoltorio `.FCMacro` cuando facilite compatibilidad y pruebas.

### 5. Prueba tecnica

Los cambios deben probarse dentro de FreeCAD cuando corresponda.

Una ejecucion sin excepciones, un test automatico exitoso o varias ejecuciones durante depuracion no demuestran por si solos que la herramienta sea una mejora.

Las pruebas tecnicas deben verificar como minimo:

- que el codigo ejecuta;
- que no rompe el documento ni funciones relacionadas;
- que las operaciones pueden deshacerse o recuperarse cuando aplique;
- que los resultados tecnicos coinciden con lo implementado;
- que no se introducen regresiones conocidas.

### 6. Resultado de Codex

`RESULTADO_CODEX.md` debe registrar siempre:

1. Objetivo original.
2. Contexto reconstruido y archivos consultados.
3. Busqueda previa realizada.
4. Archivos revisados, creados y modificados.
5. Solucion implementada o decision de revision.
6. Pruebas ejecutadas.
7. Resultado tecnico observado.
8. Limitaciones y riesgos.
9. Herramientas anteriores relacionadas.
10. Si la solucion reemplaza, complementa, duplica o se desvia de otra.
11. Aspectos que requieren validacion de Marco en FreeCAD.
12. Clasificacion provisional por Rol funcional, Madurez y Resultado comprobado.
13. Decision ElectricCR cuando corresponda.
14. Cambios realizados o pendientes en `MAPA_WORKBENCH.md` y `REVISION_MACROS.md`.

Codex no debe ocultar resultados negativos ni presentar como terminada una solucion que no resuelva el objetivo original.

## 7. Tres ejes de clasificacion

Toda herramienta relevante debe poder describirse mediante tres ejes independientes.

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

- COMPROBADA: se usa realmente y produce el resultado esperado.
- COMPROBADA-PARCIAL: resuelve el problema solo en parte o bajo condiciones conocidas.
- PROMETEDORA: tiene buenas senales, pero falta validacion suficiente en trabajo real.
- EXPERIMENTAL: fue creada para probar una idea o estrategia y no debe tratarse como herramienta productiva.
- DESVIADA: el desarrollo termino resolviendo algo diferente del objetivo original.
- DUPLICADA: repite una funcion ya cubierta sin una mejora demostrada.
- INCOMPLETA: no constituye una solucion reproducible o faltan piezas necesarias.
- FALLIDA: fue probada y no produjo el resultado esperado.
- ABANDONADA: se dejo de desarrollar porque se eligio otra estrategia o reemplazo.
- POR VERIFICAR: no existe evidencia suficiente para afirmar si resolvio el objetivo.
- NO APLICA: elemento interno, prueba o soporte donde este eje no describe una macro de usuario.

Las herramientas nuevas no deben declararse automaticamente ESTABLES o COMPROBADAS.

Cuando no exista evidencia suficiente debe utilizarse `POR VERIFICAR` en lugar de asumir exito o fracaso.

## 8. Validacion funcional por Marco

Despues de la prueba tecnica se debe comprobar si la herramienta resuelve el trabajo real para el que fue creada.

La validacion funcional puede concluir que la solucion:

- funciona y mejora el flujo;
- funciona parcialmente;
- solo sirve para un caso especializado;
- duplica una herramienta anterior;
- se desvio del objetivo original;
- no produjo el resultado esperado;
- debe volver a desarrollo.

Una prueba tecnica de Codex no sustituye esta validacion cuando la tarea depende de comportamiento visual, geometria real, flujo de usuario o documentos reales de FreeCAD.

Marco no necesita reconstruir la arquitectura tecnica para realizar esta validacion. Codex debe presentar primero el contexto ya investigado y pedir solamente las confirmaciones funcionales necesarias.

## 9. Revision por GPT y decision de integracion

GPT revisa el resultado de Codex, la evidencia de prueba, la validacion funcional y el contexto historico.

La decision debe determinar si la solucion:

- se integra al flujo principal de ElectricCR;
- permanece como herramienta especializada;
- permanece en laboratorio o desarrollo;
- se fusiona con otra herramienta;
- sustituye una solucion anterior;
- se conserva solo como respaldo;
- se clasifica como fallida, desviada, duplicada, incompleta o abandonada.

La version anterior no se elimina solamente porque exista una version nueva.

## 10. Estados del ciclo de vida

El ciclo recomendado es:

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

Una tarea puede retroceder a `DESARROLLO` desde cualquier etapa si se detectan errores, desviaciones o regresiones.

## 11. Publicacion y documentacion

Los cambios y resultados se publican en GitHub para mantener sincronizados:

- el codigo;
- `AGENTS.md`;
- `MAPA_WORKBENCH.md`;
- `ESTADO_PROYECTO.md`;
- `DECISIONES_TECNICAS.md`;
- `FLUJO_GPT_CODEX.md`;
- `REVISION_MACROS.md`;
- `TAREA_ACTUAL.md`;
- `RESULTADO_CODEX.md`;
- `HISTORIAL_CAMBIOS.md`;
- el inventario y clasificacion de herramientas cuando corresponda.

`HISTORIAL_CAMBIOS.md` registra solamente cambios aceptados. Los intentos, pruebas fallidas y soluciones pendientes permanecen documentados en `RESULTADO_CODEX.md`, `REVISION_MACROS.md`, el inventario o documentacion de desarrollo correspondiente.
