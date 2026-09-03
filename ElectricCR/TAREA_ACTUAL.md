# TAREA VIGENTE - ElectricCR / Prototipo luminaria semantica + arbol idempotente

Fecha: 2026-09-01 America/Costa_Rica
Proyecto: `Programacion en FreeCAD`
Componente principal: `ElectricCR`
Relacionados: `CRBIMCore 0.1.0`, `FacilArquitecturaWB`
FreeCAD objetivo: `1.1.3`
Estado: `CERRADA / IMPLEMENTADA / VERIFICADA MCP`

## Punto de partida obligatorio

La fase 2A de RoomResolver esta cerrada y verificada. La fase 2B de diseno en Drive tambien esta cerrada.

Leer antes de modificar:

- `AGENTS.md`;
- skill `$freecad-cr-workbench-architecture`;
- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md`;
- `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md`;
- `ElectricCR/ESTADO_PROYECTO.md`;
- codigo vigente `ElectricCR/electriccr/features/objeto_toma_uno.py`;
- `registry_electric.json` vigente.

Regla ya aprobada:

> Las relaciones semanticas son la verdad; el arbol del modelo es una vista reproducible de esas relaciones.

Y otra regla de esta tarea:

> No crear un segundo objeto electromecanico generico. Evolucionar/reutilizar el nucleo existente y probarlo de forma reversible.

## Objetivo

Construir y verificar en FreeCAD 1.1.3 un prototipo minimo con **una sola luminaria temporal** que demuestre que la instancia `App::Link` actual puede conservar su funcionamiento 2D/3D y masters, mientras recibe identidad y relacion espacial persistente suficientes para proyectar una rama electrica idempotente.

En paralelo, crear solo en el documento temporal un comparador `Arch Equipment` equivalente para medir que aporta BIM/IFC. No sustituir la luminaria Link ni decidir una migracion masiva en esta tarea.

## Alcance A - luminaria App::Link piloto

Usar el flujo real de `objeto_toma_uno.py` y el registro vigente para crear o reproducir una luminaria `App::Link` con master oculto.

La instancia piloto debe conservar sin cambios conceptuales:

- `LinkedObject` / master reutilizable;
- `Placement`;
- simbolo 2D;
- modelo 3D;
- `AlturaRel` y mecanismo actual de relink cuando aplique;
- `Tipo`, `Categoria`, `KeyRegistro`, `ModoVisual`, orientacion y metadatos legacy que ya funcionen.

Agregar solamente el contrato minimo necesario para el prototipo, preferentemente de forma reusable y no acoplada a GUI:

- `ElementUID`: identificador persistente y unico de la instancia;
- `Space`: `App::PropertyLink` al `Arch/BIM Space` canonico.

No agregar por ahora `Level` ni `Panel` a la luminaria:

- `Level` se deriva de `Space`;
- `Panel` se derivara de `Circuit` cuando exista un contrato de Circuit consolidado.

Para circuito/control, reutilizar la autoridad vigente y no inventar aun un nuevo tipo productivo:

- `CircuitoID` / propiedad equivalente existente para identificar el circuito del piloto;
- `ControlID` / `ApagadorID` y los `PropertyLinkList` existentes del Control cuando corresponda.

Si para la prueba hace falta un objeto Circuit o Control temporal, crearlo solo como fixture/probe del documento de prueba, claramente marcado como no productivo. No consolidar su clase como arquitectura definitiva.

## Alcance B - asignacion espacial

Usar `CRBIMCore.RoomResolver` para resolver el Space del punto/Placement de la luminaria piloto.

Comportamiento:

- `RESOLVED` -> asignar `Space` solo en la luminaria temporal;
- `AMBIGUOUS` -> no escribir enlace;
- `NOT_FOUND` -> no escribir enlace;
- no escribir propiedades ElectricCR sobre el Space;
- no duplicar ni mover el Space.

Probar persistencia de `ElementUID` y `Space` despues de guardar/cerrar/reabrir el documento temporal.

## Alcance C - arbol idempotente minimo

Implementar o prototipar, reutilizando primero organizadores existentes, una proyeccion minima para iluminacion:

```text
electrico
  Iluminacion
    Circuitos
      IL-TEST
        Recintos
          <RoomName>
            Apagadores
              S1
                Luminarias
                  <luminaria piloto>
```

Autoridades para este prototipo:

1. `Space` explicito de la luminaria para el recinto;
2. `CircuitoID` o contrato legacy estable vigente para el circuito;
3. relacion existente de Control (`PropertyLinkList`) y/o `ControlID` seguro para el apagador;
4. el padre visual actual solo como fallback diagnosticable, nunca como verdad.

Reglas:

- el Space real permanece en Building/Level;
- `Recintos/<RoomName>` es un contenedor visual, no un segundo Space;
- masters y `_lib` permanecen fuera de la rama funcional;
- repetir la reconstruccion debe reutilizar los mismos contenedores y no crear duplicados;
- una segunda ejecucion sin cambios debe reportar cero cambios materiales;
- la reconstruccion no debe modificar `ElementUID`, `Space`, `LinkedObject`, master ni `Placement`.

La herramienta/prototipo de arbol debe ofrecer `dry_run=True` por defecto si se materializa como helper reusable.

## Alcance D - comparador Arch Equipment

Solo en documento temporal, crear un `Arch Equipment` equivalente a la luminaria piloto, reutilizando cuando sea razonable la misma geometria/master o una copia controlada de la representacion.

Comparar y documentar:

- identidad y propiedades BIM nativas;
- comportamiento de `Base`/Placement;
- posibilidad de conservar una representacion 2D y 3D coherente;
- `IfcType` aplicable a luminaria en FreeCAD 1.1.3;
- guardar/reabrir;
- Undo/Redo;
- impacto en rendimiento/duplicacion geometrica a nivel cualitativo para este prototipo;
- viabilidad de salida IFC/2D sin asumir que deba sustituir `App::Link`.

No migrar la luminaria piloto hacia Equipment. El resultado debe ser comparativo.

## Salida documental 2D

Verificar que la luminaria piloto conserva una representacion 2D identificable y exportable. Para este prototipo basta comprobar una ruta documental basica existente (por ejemplo DXF/TechDraw/Shape 2D segun lo que ya use ElectricCR) sin redisenar el sistema de planos.

Si la ruta actual no exporta correctamente un `App::Link`, documentar el limite y no improvisar una solucion grande dentro de esta tarea.

## Arquitectura de codigo

Preferencia:

`core/helper semantico independiente de GUI -> adaptador FreeCAD -> comando/probe pequeno`

No introducir Qt/FreeCADGui en logica reusable.

Antes de crear modulos nuevos, buscar helpers existentes de:

- identificadores persistentes;
- propiedades ElectricCR;
- organizacion del arbol;
- reconocimiento de dispositivos;
- controles/circuitos;
- transacciones/dry-run.

## Pruebas obligatorias

Como minimo:

1. suite actual de `CRBIMCore.RoomResolver` sigue pasando;
2. pruebas existentes relevantes de `objeto_toma_uno.py` siguen pasando;
3. crear luminaria `App::Link` piloto desde registro/master vigente;
4. `ElementUID` creado una vez y estable en recompute/save/reopen;
5. `Space` resuelto y persistente;
6. `AMBIGUOUS` no escribe Space;
7. `NOT_FOUND` no escribe Space;
8. `LinkedObject` del piloto no cambia por agregar semantica;
9. Placement no cambia;
10. 2D y 3D mantienen comportamiento actual;
11. cambio de `AlturaRel` mantiene el mecanismo actual sin elevar el simbolo 2D;
12. reconstruccion de arbol crea la rama minima esperada;
13. segunda reconstruccion produce cero duplicados y cero cambios materiales;
14. masters siguen en `_lib` y no se mezclan con la rama funcional;
15. Space permanece bajo su jerarquia arquitectonica y sin propiedades ElectricCR nuevas;
16. guardar/cerrar/reabrir conserva UID, Space, LinkedObject y arbol;
17. Undo/Redo aprobado en operaciones de escritura del prototipo;
18. comparador `Arch Equipment` creado y evaluado en documento temporal;
19. verificacion documental 2D basica;
20. no se abre/guarda/modifica ningun FCStd original del usuario.

## Modelos y seguridad

- Usar documento temporal/demo creado por la prueba.
- Si se inspecciona La Cruz u otro modelo real, hacerlo lectura solamente y no guardar.
- No ejecutar reorganizacion sobre proyectos reales.
- No cambiar ni borrar masters productivos.
- No migrar tomacorrientes ni apagadores.
- No cambiar `ColocarLuminarias_Link` salvo que el prototipo requiera un adaptador minimo y reversible; preferir no tocarlo.
- No hacer migracion masiva de propiedades.

## Criterio de decision al cierre

El resultado debe responder con evidencia a estas preguntas:

1. ¿Puede el `App::Link` actual ser la identidad operativa enriquecida de una luminaria sin perder ninguna funcion actual?
2. ¿Son suficientes `ElementUID + Space + relaciones legacy/control existentes` para iniciar la reconstruccion del arbol?
3. ¿Que aporta realmente `Arch Equipment` que justifique integrarlo, envolverlo o reservarlo para BIM/IFC?
4. ¿La rama electrica puede reconstruirse idempotentemente sin usar el padre visual como autoridad?
5. ¿Que minimo cambio se recomienda para la siguiente fase y cual debe evitarse?

No declarar una arquitectura definitiva si la evidencia no la sostiene.

## Cierre real 2026-09-01

La fase se implemento y verifico exclusivamente en documentos temporales con
FreeCAD 1.1.3. No se abrio ni modifico ningun FCStd del usuario.

Resultado:

- la luminaria `App::Link` vigente admite `ElementUID` y `Space` sin cambiar
  `LinkedObject`, `Placement`, tipo, registro, modo visual ni orientacion;
- RoomResolver asigna unicamente un Space nativo en estado `RESOLVED`;
  `AMBIGUOUS` y `NOT_FOUND` dejan el enlace vacio;
- el cambio de `AlturaRel` conserva UID/Space/Placement y reenlaza al master
  inmutable esperado, manteniendo el simbolo 2D en Z local 0;
- el arbol se proyecta con claves estables y `dry_run=True` por defecto;
- como `App::DocumentObjectGroup` tiene pertenencia visual exclusiva, la rama
  contiene una referencia indice `App::Link` a la luminaria fisica. Este patron
  reutiliza el organizador existente y evita sacar la instancia de su grupo
  manual;
- la segunda proyeccion produjo cero cambios y cero objetos adicionales;
- los masters permanecen en `_lib/_lib_devices` y ahora conservan visibilidad
  oculta tambien despues de recompute/reapertura;
- guardar/cerrar/reabrir, Undo/Redo y exportacion DXF del Link aprobaron;
- el comparador `Arch Equipment` aprobo como `Light Fixture`, con propiedades
  BIM/IFC nativas, pero requirio `Base`/copia geometrica y no reemplazo al Link.

Las pruebas y decisiones completas quedaron en `RESULTADO_CODEX.md`. La tarea
se detiene aqui; no se iniciaron tomacorrientes, apagadores ni migraciones.

### Revalidacion 2026-09-02

Se releyo la tarea desde la fuente DEV sincronizada y se comprobo que seguia
cerrada. Sin modificar codigo, se repitieron el nucleo semantico, las 11 pruebas
de RoomResolver y el smoke integral en FreeCAD 1.1.3. Todos aprobaron; el
documento y los archivos temporales fueron eliminados por la prueba. No se
abrieron modelos originales ni se inicio una fase posterior.

## Documentacion de cierre

Al terminar:

- actualizar este `TAREA_ACTUAL.md` con resultado real;
- actualizar `ElectricCR/RESULTADO_CODEX.md`;
- actualizar `ElectricCR/ESTADO_PROYECTO.md`;
- actualizar `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md` con la decision basada en pruebas;
- actualizar `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md` solo si el prototipo confirma cambios de contrato;
- registrar memoria reusable si se confirma la arquitectura;
- no hacer commit/push salvo instruccion posterior.

## Instruccion final a Codex

Implementar y probar **solo este prototipo de una luminaria en documento temporal**. Diagnosticar y reutilizar lo existente antes de crear codigo. No migrar dispositivos reales, no reorganizar modelos originales, no iniciar tomacorrientes/apagadores ni una fase posterior. Detenerse al documentar la comparacion y la recomendacion.
