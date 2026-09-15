## Actualizacion 2026-09-09 22:09 -0600 America/Costa_Rica - Demo canonica ElectricCR A1 disponible

Se implemento un banco de pruebas propio para que el desarrollo del dispositivo electromecanico comun deje de depender de modelos productivos. La demo v0.1 reproduce de forma determinista siete dispositivos sobre dos Spaces BIM y reutiliza exclusivamente el contrato A1 aprobado.

```text
Demo spec pura
   -> Building / Level / 2 Spaces / 5 Walls
   -> 2 Toma + 2 Apagador + 2 Luminaria + 1 Sensor
   -> Owner App::Link + master + ElementUID + Space/Host + PLAN
   -> auditor read-only
```

El instrumento queda pensado para crecer por capas. Primero debe aprobar A1 + Space/Host en FreeCAD 1.1.3; despues se podran agregar Circuit/Control y, en una fase separada, el adaptador IFC. No se mezcla todavia la prueba de interoperabilidad con la validez basica de la demo.

Pruebas puras: 7/7 aprobadas. Prueba FreeCAD real: pendiente.

---

## Actualizacion 2026-09-09 22:09 -0600 America/Costa_Rica - A1 como autoridad y IFC como adaptador

La investigacion posterior al experimento NativeIFC refuerza la decision de no sustituir A1 ni crear por ahora un espejo IFC persistente. La opcion de trabajo preferente es un adaptador de interoperabilidad/exportacion que lea el elemento A1 y construya su equivalente IFC de forma controlada.

```text
Elemento A1
  App::Link + master fisico
  ElementUID
  Placement
  Space / Host / relaciones
  PLAN documental
        |
        `-- adaptador IFC
              GlobalId <- ElementUID
              clase / PredefinedType <- registro + esquema
              ObjectPlacement <- Owner.Placement
              Representation <- geometria fisica A1
              Psets <- propiedades compatibles
              containment <- Space/IfcSpace
```

El master A1 no se considera automaticamente un `IfcTypeProduct`: hoy su firma mezcla definicion de familia con valores de ocurrencia como altura/orientacion. La definicion IFC Type, si se adopta, debe derivarse de la familia/registro y probarse aparte.

PLAN sigue siendo documentacion A1 y no debe duplicar el producto electrico en IFC. Una exportacion como `IfcAnnotation` puede investigarse posteriormente solo si aporta valor documental.

Como estrategia de prueba se propone una Demo ElectricCR autocontenida, semejante a la Demo Casa de 2 Plantas, para generar un modelo pequeno/reproducible y validar de extremo a extremo los contratos A1 + Space + IFC. No implementada aun.

---

## Actualizacion 2026-09-05 - pendiente UX 2D editable

La sincronizacion espacial PLAN/Owner ya esta corregida, pero se identifica un
requisito adicional de producto: la representacion 2D debe ser tambien una
interfaz de edicion de la misma identidad.

Estado deseado:

```text
clic 3D  -> seleccionar/mover Device
clic PLAN -> seleccionar/mover el mismo Device
```

PLAN no debe presentarse como segunda identidad. La opcion de diseno preferida
es ocultarlo del arbol (`ShowInTree=false`) y redirigir su seleccion al `Owner`.
El movimiento desde 2D debe modificar `Owner.Placement`; la expresion vigente
mantiene PLAN derivado y evita ciclos.

Primera alternativa de movimiento: reutilizar `Draft Move`, con el punto base en
el origen local `(0,0,0)` del simbolo 2D. Los prototipos deben auditarse para
confirmar que ese origen contiene un vertice/punto utilizable. No se agregara
geometria visible automaticamente sin revisar el impacto documental/DXF.

La seleccion redirigida debe probarse en FreeCAD 1.1.3 con varios documentos
abiertos. Si se usa `Gui.Selection` como mediador, sera acotado a PLAN ElectricCR,
con guardia de recursion y sin modificar el documento durante la seleccion.

Por este requisito de UX, A1 continua opt-in hasta que se compruebe que puede
trabajarse con el 3D oculto y el PLAN visible como en un plano normal.

---

## Actualizacion 2026-09-05 - autoridad espacial A1 corregida

El defecto de campo de `TomaBIM_011` quedo corregido mediante una dependencia
nativa persistente. PLAN sigue siendo un objeto documental separado, pero su
Placement se expresa desde `Owner.Placement` para X/Y/orientacion y desde
`Owner.DocumentationPlaneZ` para Z.

La firma documental esquema 2 ya no contiene coordenadas, rotacion, UID ni Z;
solo describe la geometria del simbolo y su escala. `PlanSymbolScale` permanece
independiente de la Shape fisica.

Una copia temporal de Chomes reprodujo el delta de 259 mm y aprobo correccion,
movimiento, giro, altura, Z, escala, Undo/Redo, save/reopen, tres recomputes,
una toma, un apagador, DXF y cero huerfanos. No se modifico el original.

Resultado: **A1 APTO PARA SER DEFAULT DE OBJETOS NUEVOS**, aunque continua
opt-in hasta autorizacion separada. Los PLAN esquema 1 se actualizan al pasar
por la sincronizacion A1; no se ejecuto migracion productiva.

---

## Actualizacion historica 2026-09-03 - A1 no pasaba aun a default

La recomendacion anterior de considerar A1 apto para default queda suspendida
por un hallazgo de campo posterior en `Chomes-Segundo Piso.FCStd`.

`TomaBIM_011` conserva una sola identidad y `PLAN.Owner` correcto, pero tras
mover la toma el PLAN quedo 259 mm atras:

```text
Owner X = 19263
PLAN X  = 19004
```

`PLAN.ExpressionEngine=[]` y `RepresentationSignature` conserva la posicion
anterior, por lo que el PLAN no tiene actualmente una dependencia espacial
dinamica suficiente con el Owner.

Esto no invalida lo ya aprobado de A1:

- Shape fisica solo 3D;
- PLAN sin volumen/solidos;
- Owner correcto;
- UID/Space/Host;
- save/reopen;
- Undo/Redo;
- DXF documental;
- idempotencia de sincronizacion explicita.

Si invalida la conclusion de que la representacion ya se comporta como una sola
identidad espacial durante edicion manual.

Contrato vigente corregido:

```text
Device.Placement -> unica autoridad espacial
3D               -> derivado
PLAN              -> derivado en X/Y/orientacion
DocumentationPlaneZ / PlanSymbolScale -> independientes y documentales
```

Pendiente prioritario antes de hacer A1 default:
`A1 sincronizacion espacial PLAN-Owner`.

No migrar legacy ni corregir Chomes manualmente como sustituto de la causa raiz.

---

# RESUMEN - Dispositivo electromecanico comun de ElectricCR

Fecha de consolidacion: 2026-09-03
Proyecto: Programacion en FreeCAD  
Workbench principal: ElectricCR  
FreeCAD objetivo y verificado: 1.1.3  
Estado general: A1 FISICO/DOCUMENTAL CON AUTORIDAD ESPACIAL PROBADA Y APTO PARA DEFAULT NUEVO, AUN OPT-IN / BARRA ESPACIOS V0.1 INTEGRADA / MIGRACION GENERAL NO INICIADA

---

## 0. Aceptacion funcional GUI cerrada

El 2026-09-03 los comandos registrados reales de tomacorrientes en paredes BIM
y apagadores junto a puertas BIM aprobaron sus dialogos completos en FreeCAD
1.1.3. Legacy siguio siendo el default real, la casilla A1 no persistio y las
instancias A1 creadas por la GUI cumplieron el contrato ya consolidado.

La prueba temporal sobre Upala dejo 32 identidades A1 y 32 PLAN independientes,
sin huerfanos y con UID unicos. Se verificaron Shape fisica, Host, Space,
PuertaOrigen, Placement, alturas, App::Link/master, Undo/Redo, save/reopen e
invariancia de Volume/BoundBox/Solids. El contrato PLAN producido es el mismo
que ya aprobo el DXF documental del baseline A1.

No se cambio arquitectura ni codigo. El original de Upala permanecio byte a
byte igual y los temporales se eliminaron. La decision de cierre es **A1 APTO
PARA SER DEFAULT DE OBJETOS NUEVOS**, sin activar aun ese default y sin migrar
legacy.

---

## 1. Proposito de este documento

Este archivo resume el trabajo realizado alrededor del concepto de **dispositivo electromecanico comun** de ElectricCR para poder continuar en otro chat sin reconstruir el contexto.

La idea central es representar luminarias, tomacorrientes, apagadores, sensores, detectores, camaras y otros dispositivos mediante una arquitectura comun, manteniendo:

- una sola identidad por elemento fisico;
- representacion 2D documental;
- representacion 3D;
- masters reutilizables cuando convenga;
- relaciones semanticas estables con Space, Circuit, Control, Panel, System y Host;
- compatibilidad con las herramientas y objetos ElectricCR que ya funcionan;
- una estructura de arbol reconstruible desde relaciones, no al contrario.

No se pretende sustituir lo que ya funciona ni crear una segunda arquitectura paralela.

---

## 2. Hallazgo principal: el nucleo comun ya existia

La revision del proyecto demostro que el archivo:

`ElectricCR/electriccr/features/objeto_toma_uno.py`

ya funciona en la practica como un nucleo electromecanico generico, aunque su nombre provenga historicamente de los tomacorrientes.

`TomaUnoProxy` admite actualmente tipos logicos como:

- Toma;
- Apagador;
- Luminaria;
- Sensor;
- Rociador;
- Altavoz;
- Camara.

Por tanto, se decidio **evolucionar este nucleo y no crear otro objeto electromecanico paralelo**.

---

## 3. Contratos de representacion: legacy y A1

El nucleo historico conserva una ruta legacy necesaria para compatibilidad, pero
esa ruta ya no es el objetivo arquitectonico.

### LegacyCompound

```text
Placement del elemento
    |
    +-- simbolo 2D: Z local = 0
    `-- modelo 3D: Z local = AlturaRel
             \
              -> ambos dentro de obj.Shape
```

Propiedades como `ModoVisual`, `AlturaRel`, `OrientacionPared`, `KeyRegistro`,
`RecursoProto2D` y `RecursoProto3D` siguen siendo importantes para compatibilidad.

### PhysicalDocumentationA1

Verificado en FreeCAD 1.1.3 el 2026-09-03:

```text
App::Link = identidad unica
  |-- LinkedObject -> master fisico A1
  |                    `-- Shape = solo model3D fisico
  |-- ElementUID
  |-- Space
  |-- Host
  `-- PLAN DocumentationOnly
       `-- Owner -> App::Link
```

Reglas cerradas:

- la Shape fisica no contiene el simbolo 2D;
- PLAN no tiene ElementUID ni semantica funcional propia;
- PLAN puede cambiar visibilidad/escala sin modificar Volume, BoundBox o Solids;
- `ModelScale` permanece 1:1;
- la representacion documental puede tener escala propia para legibilidad;
- los servicios `is_electriccr_device()`, `installation_elevation_mm()` y
  `set_installation_elevation()` siguen siendo reutilizables;
- `LegacyCompound` permanece disponible solo para no romper llamadas/documentos
  existentes mientras A1 se integra gradualmente.

## 4. Registro de familias y representaciones

`registry_electric.json` ya separa la definicion de familia/tipo del objeto colocado.

El registro contiene, segun la familia:

- clave de tipo;
- categoria;
- recurso de simbolo 2D;
- recurso de modelo 3D;
- altura por defecto;
- modo visual;
- orientacion;
- datos electricos;
- datos dimensionales;
- clase IFC cuando existe.

Ejemplos ya presentes incluyen clasificaciones como:

- `IfcOutlet`;
- `IfcSwitchingDevice`;
- `IfcLightFixture`.

Por tanto, el registro debe mantenerse como fuente de definicion de familias y no duplicarse en otra estructura.

---

## 5. Estrategia de masters y App::Link

Para dispositivos repetitivos, especialmente luminarias, ya existe una arquitectura de masters reutilizables.

La evidencia del modelo La Cruz confirma una estructura equivalente a:

```text
electrico
  _lib
    Luminarias_Link_Masters
      Master ...
  Luminaria_Link
    Luminaria001 -> App::Link
    Luminaria002 -> App::Link
    ...
```

Los masters se identifican por combinaciones como:

- clave de registro;
- tipo logico;
- modo visual;
- orientacion;
- altura relativa.

Regla importante:

- el master compartido no debe mutarse para cambiar una instancia;
- si cambia `AlturaRel`, la instancia puede reenlazarse a otro master compatible;
- la identidad del `App::Link` debe mantenerse;
- `Placement` y relaciones semanticas de la instancia deben conservarse.

---

## 6. Arquitectura semantica vigente y pendiente

La identidad comun debe separar propiedades comunes de propiedades especificas por familia.

### Contrato comun

Confirmado en A1:

```text
ElementUID
Space
Host
Placement
LinkedObject/master fisico
PLAN documental asociado
```

Contrato comun a consolidar progresivamente:

```text
ElementClass
Family / TypeCode
Circuit
Control
System
```

Datos que deben derivarse antes de duplicarse:

- `Level` desde `Space`;
- `Panel` desde `Circuit` cuando sea posible.

No conviene duplicar datos que ya pertenecen a otra entidad.

### Relaciones

Preferencia futura:

```text
Elemento
  Space   -> App::PropertyLink
  Circuit -> App::PropertyLink cuando exista objeto Circuit estable
  Panel   -> derivado o App::PropertyLink cuando corresponda
  Control -> App::PropertyLink / PropertyLinkList segun contrato
  Host    -> App::PropertyLink cuando corresponda
```

Durante la transicion se conservan propiedades legacy como:

- `CircuitoID`;
- `ControlID`;
- `ApagadorID`;
- `Recinto`;
- otras propiedades existentes que sigan siendo necesarias.

No se eliminan automaticamente.

---

## 7. Relacion con RoomResolver y Space

Se adopto como regla que el recinto fisico canonico es el `Arch/BIM Space` cuando existe.

`CRBIMCore.RoomResolver` resuelve:

```text
NATIVE_SPACE
   >
LEGACY_AREA
   >
NOT_FOUND
```

Para un dispositivo:

- `RESOLVED` puede asignar el `Space`;
- `AMBIGUOUS` no debe escribir asignacion;
- `NOT_FOUND` no debe escribir asignacion;
- no se agregan propiedades ElectricCR al Space;
- el Space no se mueve ni se duplica.

---

## 8. Contrato del arbol

Regla aprobada:

> Las relaciones semanticas son la verdad; el arbol del modelo es una vista reproducible de esas relaciones.

Ejemplo conceptual:

```text
Luminaria L1
  Space   -> Oficina
  Circuit -> IL-01
  Control -> S1
```

Proyeccion visual posible:

```text
electrico
  Iluminacion
    Circuitos
      IL-01
        Recintos
          Oficina
            Apagadores
              S1
                Luminarias
                  L1
```

El nodo `Oficina` dentro de ElectricCR es solo una vista/contenedor.

El `Space` real permanece en la jerarquia arquitectonica, normalmente bajo Building/Level.

---

## 9. Prototipo de luminaria semantica implementado

Se implemento y verifico en FreeCAD 1.1.3 un prototipo temporal con una luminaria real creada mediante:

`objeto_toma_uno.crear_toma_link()`

usando el registro real:

`Luminaria LED Redonda 1000lm`

La instancia `App::Link` recibio solamente:

- `ElementUID`;
- `Space`.

Se conservaron:

- `LinkedObject`;
- master compartido;
- `Placement`;
- representacion 2D;
- representacion 3D;
- `AlturaRel`;
- `Tipo`;
- `KeyRegistro`;
- `ModoVisual`;
- orientacion.

---

## 10. Resultados verificados del prototipo

### Identidad

- `ElementUID` se crea una vez.
- Es unico.
- Persiste tras recompute.
- Persiste tras guardar, cerrar y reabrir.

### Space

- RoomResolver usa el `Placement` global de la instancia.
- `RESOLVED` enlaza el Space.
- `AMBIGUOUS` no escribe.
- `NOT_FOUND` no escribe.
- El Space no recibe propiedades ElectricCR.

### Altura

Se probo cambio de altura de 2700 a 2850 mm.

Resultado:

- se reutilizo el mecanismo de relink a master compatible;
- el `App::Link` mantuvo identidad;
- `ElementUID` se mantuvo;
- `Space` se mantuvo;
- `Placement` se mantuvo;
- el simbolo 2D siguio en Z local 0;
- el modelo 3D cambio de altura correctamente.

### 2D documental

- el `App::Link` se exporto correctamente a un DXF temporal no vacio.

### Masters

- permanecieron bajo `_lib/_lib_devices`;
- se corrigio un detalle por el cual `TomaUnoProxy.execute()` podia volver visible un master al recomputar;
- la marca `EsPrototipo=True` permite mantener el ViewProvider oculto.

### Guardado y Undo/Redo

- guardar/cerrar/reabrir aprobo;
- Undo/Redo aprobo.

---

## 11. Proyeccion idempotente del arbol probada

Se materializo temporalmente una rama:

```text
electrico
  Iluminacion
    Circuitos
      IL-TEST
        Recintos
          Sala de Espera
            Apagadores
              S1
                Luminarias
```

Autoridades usadas:

1. `Space`;
2. `CircuitoID`;
3. `PropertyLinkList` del control temporal.

El helper de proyeccion usa:

`dry_run=True`

por defecto.

Resultado de una segunda ejecucion:

- 0 cambios materiales;
- 0 duplicados.

No se modificaron:

- `ElementUID`;
- `Space`;
- master;
- `LinkedObject`;
- `Placement`.

---

## 12. Detalle importante sobre App::DocumentObjectGroup

FreeCAD mantiene pertenencia visual exclusiva para objetos dentro de `App::DocumentObjectGroup`.

Por esa razon, mover la luminaria fisica a cada rama del arbol no es una buena estrategia.

La solucion probada fue usar dentro de la rama visual una referencia indice:

- `App::Link`;
- marcada como `ECR_ProjectionReference`;
- enlazada a la luminaria real mediante `LinkedObject`;
- asociada mediante `ECR_SourceElementUID`.

Esto permite que el arbol sea una proyeccion sin cambiar la ubicacion fisica/organizativa principal de la instancia.

No representa una segunda familia ni una segunda identidad electromecanica.

---

## 13. Comparacion con Arch Equipment

Tambien se creo en un documento temporal un `Arch Equipment` equivalente.

Resultados:

- `Arch.makeEquipment()` produjo `Part::FeaturePython`;
- `Proxy.Type = Equipment`;
- dispone de `Base`;
- dispone de `GlobalId`;
- dispone de `IfcProperties`;
- dispone de `IfcType`;
- se configuro exitosamente como `Light Fixture`;
- el valor observado por defecto fue `Furniture`;
- guardar/reabrir aprobo;
- Undo/Redo aprobo.

Conclusion:

`Arch Equipment` aporta semantica BIM/IFC nativa, pero en el prototipo requirio `Base` o copia controlada de geometria.

El `App::Link` actual conserva mejor la estrategia ligera de master compartido.

**No existe evidencia que justifique sustituir actualmente los App::Link por Arch Equipment.**

Equipment puede reservarse para futura integracion BIM/IFC si aparece una necesidad concreta.

---

## 14. Modulos nuevos del prototipo

Se implementaron:

`ElectricCR/electriccr/semantic/device_core.py`

- nucleo semantico puro;
- JSON-compatible;
- independiente de GUI.

`ElectricCR/electriccr/semantic/freecad_adapter.py`

- adaptador FreeCAD;
- UID;
- Space;
- proyeccion del arbol.

Pruebas:

`ElectricCR/tests/test_semantic_device_core.py`

`ElectricCR/tests/freecad_semantic_luminaire_prototype_smoke.py`

Tambien se modifico de forma puntual:

`ElectricCR/electriccr/features/objeto_toma_uno.py`

para preservar la ocultacion de masters despues de recompute.

---

## 15. Pruebas aprobadas

Entre las pruebas registradas:

- `ROOM_RESOLVER_CORE_TESTS_OK 11`;
- `ECR_LIGHTING_ROOM_TESTS_OK 6`;
- `ECR_SEMANTIC_DEVICE_CORE_OK`;
- `ROOM_RESOLVER_FREECAD_SMOKE_OK`;
- `ECR_ROOMRESOLVER_PHASE2A_OK`;
- regresion de altura/rotacion semantica;
- `PASS ColocarLuminarias_Link altura`;
- `ECR_SEMANTIC_LUMINAIRE_PROTOTYPE_OK`;
- inspeccion visual en planta e isometrica;
- guardar/cerrar/reabrir;
- Undo/Redo;
- DXF temporal.

El 2026-09-02 Codex revalido el prototipo sin cambios funcionales y las pruebas volvieron a aprobar.

No quedaron documentos temporales abiertos.

---

## 16. Decision arquitectonica actual

La decision vigente es:

> **ElectricCR debe evolucionar el nucleo existente en lugar de crear un segundo objeto electromecanico. Para dispositivos repetitivos, App::Link + master es la identidad operativa preferida; las relaciones semanticas pertenecen a la instancia. Arch Equipment queda como capacidad BIM/IFC complementaria, no como sustituto automatico.**

Arquitectura conceptual:

```text
registry_electric.json
        |
        v
nucleo de dispositivo
        |
        +-- objeto directo Part::FeaturePython
        |
        `-- App::Link + master compartido
                 |
                 +-- ElementUID
                 +-- Space
                 +-- relaciones de circuito/control
                 +-- Placement
                 `-- LinkedObject -> master
```

---

## 17. Cambio de nombre pendiente

El nombre `objeto_toma_uno.py` ya no representa correctamente su funcion.

Nombre recomendado para la futura fuente de verdad:

`dispositivo_electromecanico.py`

Migracion recomendada, sin cambio funcional:

```text
dispositivo_electromecanico.py   <- fuente de verdad futura
          ^
          |
objeto_toma_uno.py               <- shim temporal de compatibilidad
```

Renombres conceptuales propuestos:

- `TomaUnoProxy` -> `DispositivoElectromecanicoProxy`;
- `VP_TomaUno` -> `VP_DispositivoElectromecanico`;
- `crear_toma_uno()` -> `crear_dispositivo()`;
- `crear_toma_link()` -> `crear_dispositivo_link()`.

Los nombres antiguos deben mantenerse temporalmente como aliases para no romper macros existentes.

**Este cambio de nombre no esta implementado todavia.**

Debe hacerse como tarea separada y con regresion completa.

---

## 18. Lo que NO se ha hecho

No se ha realizado:

- migracion masiva de luminarias;
- migracion de tomacorrientes;
- migracion de apagadores;
- sustitucion de App::Link por Arch Equipment;
- cambio general del registro;
- eliminacion de propiedades legacy;
- reconstruccion automatica del arbol en proyectos reales;
- cambio de nombre de `objeto_toma_uno.py`;
- commit/push asociado a este prototipo;
- modificacion de modelos originales durante las pruebas.

---

## 19. Proximos pasos recomendados para este tema

No volver a diseñar A1 desde cero. El prototipo fisico/documental ya aprobo.

### Fase inmediata - politica separada para activar el nuevo default

La integracion y la aceptacion funcional GUI ya estan cerradas. A1 fue
clasificado **APTO PARA SER DEFAULT DE OBJETOS NUEVOS**, pero esta tarea no
cambio el default. Una fase posterior, con autorizacion expresa, debe definir
el momento de activacion, el mensaje de compatibilidad y las regresiones de
instalacion; no debe migrar automaticamente ningun objeto legacy.

### Fase posterior - consolidar relaciones de proyecto

1. Definir objeto/contrato estable `Circuit`.
2. Formalizar `Control` sin competir con los LinkList existentes.
3. Derivar `Panel` de Circuit cuando sea posible.
4. Derivar `Level` de Space.
5. Definir `System` solo cuando exista autoridad clara.
6. Mantener propiedades legacy durante la transicion.

### Refactor de nombre - separado y posterior

El cambio `objeto_toma_uno.py` -> `dispositivo_electromecanico.py` sigue siendo
conveniente, pero ya no es prerequisito para probar la integracion A1 real. Debe
hacerse despues, como refactor no funcional con shim y regresion completa.

### Migracion legacy

Solo despues de integrar A1 en herramientas reales:

1. inventariar;
2. resolver Space/Host;
3. `dry_run`;
4. clasificar MATCH / AMBIGUOUS / NO_MATCH;
5. migrar solo casos seguros;
6. reconstruir arbol despues de consolidar relaciones.

---

## 20. Relacion con la barra comun Espacios y Recintos

La barra y el dispositivo conservan responsabilidades separadas, pero ya no son
lineas conceptualmente independientes. Comparten el contrato espacial:

- la barra/CRBIMCore resuelve la identidad `Space`;
- Facil Arquitectura produce y mantiene Space/Wall/Door/Window;
- ElectricCR consume `Space` y `Host` en la instancia A1;
- `Level` se deriva de Space;
- el arbol disciplinar proyecta las relaciones sin duplicar el Space.

No se debe mezclar el codigo GUI de la barra con el nucleo del dispositivo, ni
hacer que ElectricCR importe a FA para obtener estas relaciones. La integracion
se realiza por contratos y objetos BIM compartidos.

---

## 21. Archivos de referencia principales en Drive

Revisar primero:

- `ElectricCR/docs/DISENO_OBJETO_ELECTROMECANICO_COMUN.md`
- `ElectricCR/RESULTADO_CODEX.md`
- `ElectricCR/ESTADO_PROYECTO.md`
- `ElectricCR/docs/CONTRATO_ARBOL_SEMANTICO.md`
- `ElectricCR/electriccr/features/objeto_toma_uno.py`
- `ElectricCR/electriccr/semantic/device_core.py`
- `ElectricCR/electriccr/semantic/freecad_adapter.py`
- `ElectricCR/tests/test_semantic_device_core.py`
- `ElectricCR/tests/freecad_semantic_luminaire_prototype_smoke.py`
- `registry_electric.json`

---

## 22. Texto sugerido para iniciar el siguiente chat

```text
Proyecto: Programacion en FreeCAD
Workbench: ElectricCR
FreeCAD: 1.1.3

Quiero continuar el dispositivo electromecanico comun usando como fuente:
RESUMEN_DISPOSITIVO_ELECTROMECANICO.md.

A1 ya fue implementado y verificado en FreeCAD real:
- PhysicalDocumentationA1;
- Shape solo fisica;
- PLAN DocumentationOnly;
- ElementUID, Space y Host;
- App::Link + master fisico;
- save/reopen, Undo/Redo y DXF.

La barra Espacios y Recintos v0.1 tambien esta integrada. Space BIM es la
identidad espacial canonica, Level se deriva de Space y FA conserva la autoria
de Wall/Door/Window/Space.

La integracion A1 opt-in en las herramientas reales de tomacorrientes sobre
muros BIM y apagadores junto a puertas BIM ya aprobo aceptacion funcional desde
los comandos registrados y sus dialogos. A1 es apto para ser default de objetos
nuevos, pero el default legacy y la compatibilidad permanecen sin cambios en
esta fase.
```

---

## 23. Estado final para traspaso

```text
Nucleo comun existente:            CONFIRMADO
A1 PhysicalDocumentation:          PROBADO MCP
Shape solo fisica:                 PROBADA
PLAN DocumentationOnly:            PROBADO
Tomacorriente A1 aislado:          PROBADO
Apagador A1 aislado:               PROBADO
ElementUID persistente:            PROBADO
Space persistente:                 PROBADO
Host persistente:                  PROBADO
RoomResolver:                      INTEGRADO
Level derivado de Space:           CONTRATO DEFINIDO
Altura por relink de master:       PROBADA
DXF desde PLAN:                    PROBADO
Arbol idempotente:                 PROBADO
Barra Espacios y Recintos v0.1:    INTEGRADA
Arch Equipment:                    COMPARADO
Sustituir App::Link por Equipment: NO RECOMENDADO ACTUALMENTE
Integracion A1 en herramientas:    PROBADA MCP / OPT-IN
Renombre a dispositivo...:         PENDIENTE POSTERIOR
Migracion de tomas/apagadores:     NO INICIADA
Migracion masiva:                  NO AUTORIZADA
```

Fin del resumen.


## 24. Contrato transversal FA / Espacios / objeto electromecanico

La relacion aprobada entre Workbenches es:

```text
Facil Arquitectura
  Space --------------> Device.Space
  Wall  --------------> Device.Host
  Door  --------------> Switch.PuertaOrigen
  Level <--- Space ----> derivacion contextual
              ^
              |
        CRBIMCore.RoomResolver
```

- FA produce/mantiene la arquitectura.
- CRBIMCore resuelve el recinto.
- ElectricCR consume enlaces y no crea un segundo recinto.
- Sketches, poligonos y Areas legacy pueden ayudar al calculo o compatibilidad,
  pero no sustituyen una identidad BIM valida.
- El arbol es una proyeccion de estas relaciones.

### Baseline Upala

Drive conserva el inventario historico de 48 tomacorrientes y 11 apagadores
legacy `LegacyCompound`. Al ejecutar la integracion, el FCStd vigente ya no los
contenia (187 objetos, cero dispositivos ElectricCR); esta discrepancia queda
registrada sin inferir una causa. Las herramientas reales ya pueden crear A1 de
forma opt-in y preservan una coincidencia legacy sin migrarla.

`Apagador - Rectangle006` no era una puerta mal identificada: la puerta era
`Window`, el host `Wall` y `Rectangle006` el `AreaRecinto` usado para el Label.
La diferencia de Placement historica queda sin correccion especulativa.
