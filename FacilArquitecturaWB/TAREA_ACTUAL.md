# TAREA VIGENTE - ElectricCR / RoomResolver fase 2A + contrato semantico del arbol

Fecha: 2026-09-01 America/Costa_Rica
Proyecto: `Programacion en FreeCAD`
Componentes: `ElectricCR`, `CRBIMCore 0.1.0`, compatibilidad con `FacilArquitecturaWB`
FreeCAD objetivo: `1.1.3`
Estado: `COMPLETADA / PROBADA / VERIFICADA MCP`

## Objetivo

Adoptar `CRBIMCore.RoomResolver` en el calculo de iluminacion de ElectricCR sin redefinir todavia los objetos fisicos de luminarias, tomacorrientes ni apagadores, y dejar definido el contrato semantico que permitira reconstruir el arbol electrico desde relaciones estables en vez de usar la posicion en grupos como fuente de verdad.

La regla central de esta fase es:

> Las relaciones semanticas son la verdad; el arbol del modelo es una vista reproducible de esas relaciones.

## Contexto que debe preservarse

Existe una estructura historica/canonica de iluminacion:

`electrico/Iluminacion/Circuitos/<Circuito>/Recintos/<Recinto>/Apagadores/<Apagador>/Luminarias`

Tambien existen herramientas reales que ya organizan el arbol, entre otras:

- `Configuracion del proyecto/Organizar_Documento_Electrico.FCMacro`;
- `Configuracion del proyecto/Ordenar_Arbol_Electrico_Auto.FCMacro`;
- `Configuracion del proyecto/Ordenar_Grupos_ElectricCR.FCMacro`;
- `Configuracion del proyecto/Mover_Seleccion_a_Circuito.FCMacro`;
- `Iluminacion/Organizar_Luminarias_por_Circuito_y_Apagador.FCMacro`;
- `Iluminacion/Actualizar_Iluminacion_Completa.FCMacro`;
- `Iluminacion/Hoja_Iluminacion.FCMacro` o su nombre real equivalente con acentos.

No crear un segundo sistema de arbol en paralelo. Auditar y reutilizar/extender lo existente.

## Principios de arquitectura

1. El `Arch/BIM Space` permanece en la jerarquia arquitectonica nativa, normalmente bajo Building/Level. No moverlo al arbol electrico.
2. Los elementos ElectricCR pueden organizarse visualmente bajo la rama electrica, pero su pertenencia a recinto, circuito, tablero, sistema o control debe poder existir independientemente de esa posicion visual.
3. El arbol electrico debe poder reconstruirse de forma idempotente desde relaciones/propiedades estables.
4. La jerarquia visual no debe ser la unica forma de determinar `Circuito`, `Recinto`, `Apagador`, `Panel` o `Sistema`.
5. `RoomResolver` debe ser la fuente comun para resolver el recinto fisico: `NATIVE_SPACE` primero, `LEGACY_AREA` como fallback.
6. No crear objetos de recinto duplicados dentro del arbol electrico. Si se necesita un nodo `Recintos/<Recinto>`, debe ser un contenedor/vista electrica, no una segunda identidad arquitectonica.
7. No fijar todavia el modelo final de luminaria/toma/apagador sin auditar los App::Link, masters, propiedades y herramientas actuales.
8. Conservar el flujo 2D -> 3D y la futura posibilidad de que una sola identidad electromecanica tenga representacion documental 2D y representacion 3D.

## Alcance funcional de fase 2A

### A. Integracion piloto de RoomResolver

Auditar e integrar solamente la capa de calculo/lectura de iluminacion que actualmente obtiene datos de Areas, rotulos, grupos o tablas.

Objetivo minimo:

- obtener recinto mediante `CRBIMCore.RoomResolver`;
- leer nombre, area y los metadatos disponibles del recinto resuelto;
- mantener compatibilidad con Areas heredadas por el fallback del resolver;
- conservar los contratos actuales de `DatosRecintos`, hoja de iluminacion y calculo de cantidad/filas/columnas;
- no cambiar en esta fase la logica de colocacion fisica de luminarias.

### B. Contrato semantico del arbol

Auditar las herramientas actuales del arbol y documentar, sin migracion masiva, que relaciones ya existen y cuales faltan para reconstruir la jerarquia.

Como minimo estudiar:

- elemento -> Space/Recinto;
- elemento -> Circuito;
- circuito -> Tablero;
- luminaria -> Apagador/control cuando exista;
- elemento -> Sistema/Disciplina cuando corresponda;
- elemento -> Level cuando corresponda.

Preferir `App::PropertyLink` o mecanismos nativos equivalentes cuando ya existan o sean compatibles, pero no agregar propiedades nuevas masivamente en esta fase sin justificarlo y probarlo.

## Fuera de alcance

- No redefinir todavia el objeto electromecanico generico definitivo.
- No migrar luminarias actuales a un tipo nuevo.
- No migrar tomacorrientes ni apagadores.
- No modificar la geometria, Placement, master ni LinkedObject de elementos existentes salvo que una prueba temporal controlada lo requiera y sea explicitamente reversible.
- No cambiar `ColocarLuminarias_Link` ni otras herramientas de colocacion para usar nuevos objetos.
- No reorganizar automaticamente proyectos reales del usuario.
- No mover `Arch Space` al arbol electrico.
- No eliminar Areas legacy, grupos, macros o propiedades existentes.
- No convertir la jerarquia visual en fuente autoritativa de relaciones.
- No modificar MEPWorkbenchCR/HVAC en esta tarea.

## Auditoria obligatoria antes de programar

1. Leer `AGENTS.md` y `$freecad-cr-workbench-architecture`.
2. Leer la documentacion vigente de `CRBIMCore.RoomResolver`.
3. Inspeccionar codigo real de las macros/herramientas citadas y cualquier backend comun que ya usen.
4. Inventariar como se identifican hoy luminarias, tomas y apagadores: `App::Link`, master, propiedades, nombres, grupos, circuito, recinto, etc.
5. Identificar donde se construye/actualiza `DatosRecintos` y la hoja de iluminacion.
6. Identificar exactamente que logica usa hoy `Actualizar_Iluminacion_Completa` para detectar recintos.
7. Identificar como `Organizar_Documento_Electrico` y `Organizar_Luminarias_por_Circuito_y_Apagador` derivan la ruta del arbol.
8. Revisar muestras de arbol existentes, especialmente La Cruz y capturas recientes, sin modificar los FCStd originales.
9. Confirmar si ya existe un helper neutral o ElectricCR para relaciones semanticas antes de crear otro.

## Comportamiento esperado del piloto

El calculo de iluminacion debe funcionar en tres escenarios controlados:

1. documento con solo `Arch Space` nativo;
2. documento con solo Area legacy compatible;
3. documento con Space + Area legacy superpuestos, donde gana el Space.

Ademas:

- `AMBIGUOUS` no debe elegir silenciosamente un recinto;
- `NOT_FOUND` debe conservar un comportamiento seguro y diagnosticable;
- los resultados legacy deben mantenerse cuando solo existan Areas;
- no debe ser necesario crear luminarias para probar la resolucion espacial y el calculo.

## DatosRecintos y compatibilidad

Conservar columnas, nombres y contratos existentes salvo necesidad comprobada. Si se requiere informacion adicional para trazabilidad, preferir una extension compatible y documentada, por ejemplo una fuente de recinto o UID, sin romper consumidores actuales.

No asumir que `Largo` y `Ancho` existen para todos los Spaces. Para recintos no rectangulares, el calculo debe distinguir entre datos geometricos realmente disponibles y aproximaciones legacy. No inventar dimensiones sin una regla explicita.

## Contrato objetivo del arbol, aun no migrado

La rama historica de iluminacion se conserva conceptualmente:

```text
electrico
  Iluminacion
    Circuitos
      <Circuito>
        Recintos
          <Recinto>
            Apagadores
              <Apagador>
                Luminarias
                  <Luminaria...>
```

Pero los nodos deben ser una proyeccion de relaciones. El `Arch Space` real sigue en Building/Level y no se duplica ni se mueve.

Para otros sistemas no forzar esta misma forma si su semantica es distinta. Ejemplo ya definido: sensores de humo pueden organizarse por zonas.

## Pruebas obligatorias

Como minimo:

1. `RoomResolver` sigue aprobando su suite existente.
2. Calculo iluminacion con Space-only.
3. Calculo iluminacion con legacy-only.
4. Space + Area -> Space autoritativo.
5. `AMBIGUOUS` -> sin asignacion silenciosa.
6. `NOT_FOUND` -> resultado seguro.
7. `DatosRecintos` conserva contrato esperado.
8. Recalculo no duplica filas/objetos ni cambia luminarias existentes.
9. Firma documental de los elementos fisicos permanece sin cambios en pruebas read-only de calculo.
10. Auditoria del arbol demuestra que el organizador puede evolucionar hacia reconstruccion por relaciones sin depender solo del padre visual.
11. Smoke real FreeCAD 1.1.3 mediante MCP sobre documento temporal/demo; no guardar originales.

## Documentacion y cierre

Al terminar:

- actualizar este `TAREA_ACTUAL.md` con resultado real;
- actualizar `RESULTADO_CODEX.md` y `ESTADO_PROYECTO.md` del componente correspondiente;
- actualizar documentacion de ElectricCR y/o `CRBIMCore` cuando cambie un contrato;
- registrar una decision reusable en `Memoria_FreeCAD/` si se confirma el principio `relaciones -> arbol`;
- documentar claramente que el rediseño del objeto electromecanico sigue pendiente;
- dejar una recomendacion concreta para la siguiente fase: auditoria/diseno del objeto electromecanico comun y posterior reconstruccion idempotente del arbol.

## Criterio de cierre

Cerrar solamente cuando:

- ElectricCR use RoomResolver en el calculo piloto de iluminacion sin perder compatibilidad legacy;
- ningun elemento fisico haya sido migrado o reemplazado;
- el arbol actual haya sido auditado y exista un contrato documentado que separe relaciones semanticas de jerarquia visual;
- las pruebas controladas y el smoke FreeCAD 1.1.3 aprueben;
- no haya regresion de CRBIMCore ni del calculo de iluminacion existente.

## Instruccion a Codex

Implementar y probar solo esta fase 2A. Diagnosticar primero. Reutilizar las herramientas reales del arbol y de iluminacion. No redefinir todavia luminarias/tomas/apagadores, no migrar elementos y no reorganizar FCStd originales. Detenerse al documentar el resultado.

## Resultado de cierre 2026-09-01

- `Actualizar_Iluminacion_Completa.FCMacro` usa el adaptador read-only
  `ElectricCR.electriccr.lighting.room_calculation`, basado en `CRBIMCore`.
- Space-only, legacy-only y Space sobre Area aprobaron; el Space es autoritativo.
- `AMBIGUOUS` y `NOT_FOUND` quedan diagnosticados sin asignacion silenciosa.
- `DatosRecintos` conserva exactamente 12 encabezados; la tabla legacy y la
  formula existente de cantidad/filas/columnas permanecen.
- Areas heredadas conservan sus propiedades de layout. Los Spaces no reciben
  `Rows`, `Columns` ni propiedades ElectricCR nuevas.
- El comando completo se ejecuto dos veces sin duplicar hojas/objetos y sin
  crear luminarias.
- Firma de Shape, Placement, Name, TypeId y propiedades del Space: estable,
  incluyendo guardar/cerrar/reabrir.
- La auditoria confirma propiedades explicitas antes que padre visual,
  `PropertyLinkList` en controles y faltantes de enlaces uniformes para Room,
  Panel, Level y System.
- Contrato documentado en `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md`.
- Las copias locales de La Cruz revisadas contienen arquitectura/plataforma,
  pero no un arbol electrico util para inferir relaciones historicas; no se
  abrieron ni guardaron modelos originales.

Pruebas: 17 pruebas puras, smoke RoomResolver fase 1, smoke legacy de Areas,
smoke fase 2A y smoke read-only del contrato semantico, todos aprobados en
FreeCAD 1.1.3 cuando aplica.

La fase se detiene aqui. Sigue pendiente, fuera de alcance, el diseno del objeto
electromecanico comun y la reconstruccion idempotente del arbol desde relaciones.
