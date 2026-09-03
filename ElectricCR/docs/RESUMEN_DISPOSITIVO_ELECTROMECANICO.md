# RESUMEN - Dispositivo electromecanico comun de ElectricCR

Fecha de consolidacion: 2026-09-02  
Proyecto: Programacion en FreeCAD  
Workbench principal: ElectricCR  
FreeCAD objetivo y verificado: 1.1.3  
Estado general: ARQUITECTURA DEFINIDA / PROTOTIPO DE LUMINARIA IMPLEMENTADO Y VERIFICADO / MIGRACION GENERAL NO INICIADA

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

## 3. Contrato geometrico actual que debe conservarse

El nucleo existente ya cumple una regla importante del proyecto: 2D y 3D son representaciones de una misma identidad.

Conceptualmente:

```text
Placement del elemento
    |
    +-- simbolo 2D: Z local = 0
    |
    `-- modelo 3D: Z local = AlturaRel
```

Propiedades y comportamientos relevantes:

- un solo `Placement` global;
- `AlturaRel` controla la altura del 3D;
- el simbolo 2D permanece en Z local 0;
- `ModoVisual = Ambos | Solo2D | Solo3D`;
- `Categoria` permite Pared, Cielo, Piso, etc.;
- `Giro`, `OffsetX`, `OffsetY` y `OrientacionPared`;
- `KeyRegistro` enlaza con `registry_electric.json`;
- `RecursoProto2D` y `RecursoProto3D` mantienen trazabilidad de representacion;
- el flujo directo usa `Part::FeaturePython`;
- el flujo repetitivo usa `App::Link` hacia masters ocultos.

Tambien existen servicios reutilizables para reconocer dispositivos y manejar altura semantica:

- `is_electriccr_device()`;
- `installation_elevation_mm()`;
- `set_installation_elevation()`.

---

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

## 6. Arquitectura semantica propuesta

La identidad comun debe separar propiedades comunes de propiedades especificas por familia.

### Contrato comun conceptual

```text
ElementUID
ElementClass
Family / TypeCode
Space
Circuit
Control
System
Host
```

Otros datos pueden derivarse:

- `Level` preferentemente desde `Space`;
- `Panel` preferentemente desde `Circuit`.

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

Cuando se retome **dispositivo_electromecanico** en otro chat, no volver a diseñar desde cero.

Orden recomendado:

### Fase A - refactor de nombre sin cambio funcional

1. Auditar todos los imports de `objeto_toma_uno.py`.
2. Crear `dispositivo_electromecanico.py` como fuente de verdad.
3. Mantener `objeto_toma_uno.py` como shim.
4. Mantener aliases de funciones/clases antiguas.
5. Ejecutar todas las regresiones de directos, Links, masters, altura y 2D/3D.
6. No migrar objetos reales.

### Fase B - consolidar contrato semantico de instancia

1. Formalizar `ElementUID`.
2. Formalizar `Space`.
3. Definir objeto/contrato estable `Circuit`.
4. Formalizar `Control`.
5. Derivar `Panel` de Circuit cuando sea posible.
6. Derivar `Level` de Space cuando sea posible.
7. Definir `System` y `Host`.
8. Mantener compatibilidad legacy.

### Fase C - herramienta opt-in de enriquecimiento

1. `dry_run` por defecto.
2. Detectar dispositivos existentes.
3. Resolver Space con RoomResolver.
4. Proponer relaciones.
5. Clasificar MATCH / AMBIGUOUS / NO_MATCH.
6. Escribir solo casos seguros.
7. No sustituir masters ni LinkedObject.
8. Probar primero sobre copia controlada.

### Fase D - extender a familias

Despues de validar luminarias:

- tomacorrientes;
- apagadores;
- detectores/sensores;
- camaras;
- otros dispositivos.

Cada familia debe conservar sus propiedades especificas fuera del nucleo comun.

---

## 20. Separacion respecto a la tarea actual de barras comunes

Este tema debe continuar en un chat propio.

La tarea activa actual del proyecto es distinta:

**CRBIMCore / Barra comun de Espacios y Recintos**

Por tanto:

- no mezclar la refactorizacion de `dispositivo_electromecanico` con la barra comun;
- la barra comun sigue trabajando sobre Space/RoomResolver;
- el dispositivo electromecanico queda como linea paralela ya documentada y con prototipo verificado.

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

Quiero continuar el tema del dispositivo electromecanico comun.

Use como contexto principal el archivo:
RESUMEN_DISPOSITIVO_ELECTROMECANICO.md

El prototipo de luminaria semantica ya fue implementado y verificado.
No quiero rediseñar el objeto desde cero.

La arquitectura vigente conserva:
- objeto_toma_uno.py como nucleo historico comun;
- App::Link + masters para dispositivos repetitivos;
- ElementUID y Space en la instancia;
- RoomResolver para relacion espacial;
- relaciones -> arbol como regla autoritativa;
- Arch Equipment solo como complemento BIM/IFC.

El siguiente tema a revisar es el cambio de nombre/refactor no destructivo hacia
dispositivo_electromecanico.py y luego la consolidacion del contrato semantico comun.

Diagnosticar antes de modificar y preservar compatibilidad con todas las macros existentes.
```

---

## 23. Estado final para traspaso

```text
Nucleo comun existente:            CONFIRMADO
Luminaria App::Link semantica:     PROBADA
ElementUID persistente:            PROBADO
Space persistente:                 PROBADO
RoomResolver:                      INTEGRADO
Altura por relink de master:       PROBADA
2D + 3D misma identidad:           CONSERVADO
DXF del App::Link:                 PROBADO
Arbol idempotente:                 PROBADO
Arch Equipment:                    COMPARADO
Sustituir App::Link por Equipment: NO RECOMENDADO ACTUALMENTE
Renombre a dispositivo...:         PENDIENTE
Migracion de tomas/apagadores:     NO INICIADA
Migracion masiva:                  NO AUTORIZADA
```

Fin del resumen.
