# Diseno del objeto electromecanico comun - ElectricCR

Fecha: 2026-09-01 America/Costa_Rica
Estado: `PROTOTIPO DE LUMINARIA IMPLEMENTADO / VERIFICADO MCP`
FreeCAD objetivo: `1.1.3`

## 1. Problema

ElectricCR ya dispone de elementos funcionales para luminarias, tomacorrientes, apagadores, cajas, tableros y otros dispositivos, muchos de ellos basados en `App::Link` y masters reutilizables. Tambien existen propiedades y organizadores legacy que relacionan elementos con circuitos, recintos y controles.

El objetivo no es reemplazar lo que funciona, sino converger hacia una identidad electromecanica comun que permita:

- una sola identidad por elemento fisico;
- representacion 2D documental y 3D/BIM del mismo elemento;
- relaciones estables con Space, Circuit, Panel, Control, System y Host;
- masters reutilizables;
- reconstruccion idempotente del arbol;
- migracion no destructiva de objetos existentes.


## 2. Hallazgo principal del proyecto: el nucleo comun ya existe

La revision del codigo vigente cambia el punto de partida del diseno.

`ElectricCR/electriccr/features/objeto_toma_uno.py` ya implementa un nucleo comun que no esta limitado a tomacorrientes. `TomaUnoProxy` admite actualmente los tipos logicos:

- `Toma`;
- `Apagador`;
- `Luminaria`;
- `Sensor`;
- `Rociador`;
- `Altavoz`;
- `Camara`.

Dispone de un contrato geometrico valioso que debe preservarse:

```text
Placement del elemento
    |
    +-- simbolo 2D: Z local = 0
    |
    `-- modelo 3D: Z local = AlturaRel
```

Ademas:

- `ModoVisual` permite `Ambos`, `Solo2D` y `Solo3D`;
- `Categoria` distingue `Pared`, `Cielo` y `Piso`;
- `Giro`, `OffsetX`, `OffsetY`, `AlturaRel` y `OrientacionPared` son parametros locales;
- `KeyRegistro` vincula el elemento con `registry_electric.json`;
- `RecursoProto2D` y `RecursoProto3D` mantienen trazabilidad de representaciones;
- el simbolo y el modelo se combinan en una sola `Shape`, por lo que 2D y 3D ya son representaciones de una unica identidad directa;
- existe una ruta `App::Link` que crea masters ocultos reutilizables;
- los masters se identifican por clave de registro, tipo, modo visual, orientacion y altura;
- los cambios de altura de un Link relinkean la instancia hacia un master compatible sin mutar un master compartido;
- `is_electriccr_device()`, `installation_elevation_mm()` y `set_installation_elevation()` ya forman un pequeno servicio comun de dispositivos.

La evidencia de La Cruz confirma que la estrategia de masters no es teorica: `_lib/Luminarias_Link_Masters` esta oculta y las luminarias colocadas son instancias `App::Link`.

### Consecuencia de arquitectura

La prioridad de diseno pasa a ser:

> **evolucionar y refactorizar `objeto_toma_uno.py` como nucleo comun; integrar capacidades nativas donde aporten valor; evitar un segundo objeto electromecanico paralelo.**

La existencia de `Arch Equipment` sigue siendo importante, pero debe evaluarse contra este nucleo funcional. No se adopta como reemplazo automatico.


## 3. Hallazgo nativo complementario: Arch Equipment

FreeCAD incluye `Arch Equipment` y `Arch.makeEquipment(baseobj=None, placement=None, name=None)`.

La implementacion de FreeCAD describe Equipment como objeto para mobiliario y aparatos electricos o hidraulicos de un edificio. La clase `_Equipment` hereda de `ArchComponent.Component` y define `Type = "Equipment"`.

Propiedades nativas relevantes observadas:

- `Base` heredada de Arch Component;
- `Placement`;
- `Model`;
- `ProductURL`;
- `StandardCode`;
- `SnapPoints`;
- `EquipmentPower`;
- soporte de geometria proveniente de `Base` y de malla de alta resolucion en ciertos flujos.

Conclusion revisada: `Arch Equipment` es un candidato nativo a integrar o comparar, pero ElectricCR ya posee un `Part::FeaturePython` comun con 2D+3D y una ruta `App::Link` probada. La decision debe basarse en que aporta Equipment sin perder el contrato existente, no en reemplazarlo por principio.

### Limitacion a verificar

El Equipment nativo asigna por defecto un `IfcType` orientado a Furniture/Furnishing Element/Building Element Proxy segun la version IFC disponible. Para ElectricCR debe comprobarse en FreeCAD 1.1.3 si el `IfcType` puede y debe especializarse de forma segura a clases IFC electricas apropiadas para cada familia. No se fija aun esa taxonomia.

## 4. App::Link no se descarta

`App::Link` sigue siendo valioso para instanciar muchas veces un master sin duplicar geometria.

Por tanto, la decision no debe plantearse como `Equipment` versus `App::Link`, sino como posible combinacion de responsabilidades:

- `Equipment`: identidad BIM/semantica del elemento;
- `App::Link` o `Base`: reutilizacion de la geometria/master;
- `App::PropertyLink`: relaciones semanticas con otros objetos.

Debe probarse en FreeCAD real que esta combinacion preserve rendimiento, Placement, visibilidad, guardar/reabrir y edicion.

## 5. PropertyLink para relaciones

El contrato semantico del arbol ya establece que la jerarquia visual no es autoridad.

Para nuevos objetos, las relaciones fuertes deben tender a enlaces reales:

```text
Element
  Space   -> App::PropertyLink
  Circuit -> App::PropertyLink cuando exista objeto Circuit
  Panel   -> App::PropertyLink
  Control -> App::PropertyLink o relacion equivalente
  Host    -> App::PropertyLink cuando corresponda
```

Los identificadores de texto actuales (`CircuitoID`, `ControlID`, `Recinto`, etc.) deben conservarse durante la transicion como compatibilidad y datos visibles, pero no ser la unica fuente de verdad.

## 6. Una identidad, dos representaciones

Regla del proyecto:

> 2D y 3D deben ser representaciones de la misma identidad, no dos objetos funcionales independientes.

Se deben comparar cuatro patrones.

### Alternativa A - evolucion del nucleo directo `TomaUnoProxy`

El objeto colocado sigue siendo un `Part::FeaturePython` del nucleo existente, con simbolo 2D y modelo 3D en una sola Shape y un solo Placement.

Ventajas:

- ya cumple la regla de una identidad con 2D+3D;
- altura 3D independiente del simbolo de planta;
- menor migracion conceptual;
- propiedades y registro existentes;
- facil de extender con enlaces semanticos.

Riesgos/preguntas:

- costo geometrico si hay cientos de elementos directos;
- semantica BIM/IFC no nativa;
- separar mejor nucleo de GUI/FreeCAD y evitar crecimiento monolitico.

### Alternativa B - evolucion de la ruta `App::Link` actual

El objeto colocado sigue siendo un `App::Link` con master compuesto 2D+3D, pero la **instancia** recibe el contrato semantico estable.

Ventajas:

- es el flujo real de luminarias de La Cruz;
- geometria compartida y eficiente;
- masters inmutables ya implementados;
- menor riesgo de migracion.

Riesgos/preguntas:

- definir claramente propiedades del master versus instancia;
- IFC/BIM de la instancia;
- asegurar que relaciones y documentacion no dependan del LinkedObject.

### Alternativa C - integracion hibrida con Arch Equipment

El nucleo ElectricCR conserva la identidad/compatibilidad y se evalua incorporar o adaptar capacidades de Equipment donde aporten BIM/IFC, Base o propiedades nativas.

Ventajas:

- semantica BIM nativa;
- propiedades de equipo ya disponibles;
- camino mas natural hacia IFC.

Riesgos/preguntas:

- eficiencia cuando hay cientos de instancias;
- comportamiento si Base es un Link u otro objeto compartido;
- estrategia 2D/3D.

### Alternativa D - Arch Equipment como sustituto de identidad

Un Equipment reemplazaria la identidad colocada actual y deberia reproducir sin perdida el contrato 2D+3D, los masters, la altura semantica y las herramientas existentes.

Ventajas:

- separa semantica de representacion;
- encaja con flujo plano 2D -> comprobacion 3D;
- permite cambiar familia/modelo sin cambiar identidad.

Riesgos/preguntas:

- requiere adaptador/view provider o reglas de visibilidad;
- debe evitar que el usuario perciba dos objetos funcionales distintos;
- debe evaluarse TechDraw/DXF.

### Alternativa E - segundo objeto propio ElectricCR

Debe descartarse por defecto mientras `objeto_toma_uno.py` pueda evolucionar. Solo seria justificable si una limitacion demostrada exige otro tipo y existe migracion reversible.

No es la opcion preferida por defecto.

## 7. Contrato base minimo propuesto

Separar propiedades comunes de extensiones por familia.

### Identidad

- `ElementUID`: identificador estable e independiente de Label/Name.
- `ElementClass`: clase logica comun (`LIGHT`, `OUTLET`, `SWITCH`, `DETECTOR`, etc.).
- `Family` / `TypeCode`: referencia estable a familia/tipo.

### Contexto espacial

- `Space`: enlace al recinto fisico canonico.
- `Level`: preferentemente derivado de Space; enlace explicito solo si hace falta.
- `Host`: muro, cielo, piso u otro soporte cuando aplique.

### Sistema electrico

- `System`: iluminacion, potencia, datos, deteccion, CCTV, etc.
- `Circuit`: enlace futuro al objeto Circuit cuando exista.
- `Panel`: enlace futuro al objeto Panel cuando aplique.
- `Control`: relacion con apagador/control cuando aplique.

### Representacion

- `Representation2D`.
- `Representation3D`.
- `Documentation2D` o mecanismo equivalente para salida documental.

### Datos de equipo

Reutilizar propiedades nativas de Equipment cuando sean adecuadas, por ejemplo `Model`, `StandardCode`, `ProductURL`, `SnapPoints`, `EquipmentPower`.

No duplicar propiedades nativas con prefijos ElectricCR salvo que exista una razon de compatibilidad.

## 8. Extensiones por familia

No todo pertenece al nucleo comun.

Ejemplos:

- luminaria: flujo luminoso, potencia, montaje, fotometria, emergencia;
- tomacorriente: polos, tension, amperaje, NEMA/tipo, uso especial;
- apagador: polos/vias, control asociado, altura de montaje;
- detector: tipo de deteccion, zona, cobertura;
- camara: FOV, resolucion, red/alimentacion;
- desconector: corriente, polos, SCCR cuando corresponda.

Estas propiedades deben vivir en extensiones/familias, no inflar el objeto base.

## 9. Relacion con el arbol

El arbol es una proyeccion.

Ejemplo de iluminacion:

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
                  L2
```

Los enlaces autoritativos serian conceptualmente:

```text
L1.Space   = Space_Oficina
L1.Circuit = Circuit_IL01
L1.Control = S1
```

El nodo `Oficina` de la rama electrica no sustituye a `Space_Oficina`.

La reconstruccion futura debe:

- crear/reusar contenedores por clave semantica;
- mover solo la presentacion/arbol de los elementos cuando sea seguro;
- no cambiar sus enlaces semanticos por el hecho de moverlos;
- no duplicar nodos al repetir;
- detectar relaciones incompletas/ambiguas y reportarlas.

## 10. Migracion legacy

La migracion futura debe ser incremental.

Orden propuesto:

1. inventariar objeto actual;
2. resolver Space con RoomResolver;
3. leer `CircuitoID`, `ControlID`, grupo y propiedades existentes;
4. proponer enlaces equivalentes en `dry_run`;
5. clasificar `MATCH`, `AMBIGUOUS`, `NO_MATCH`;
6. escribir solo casos seguros dentro de transaccion;
7. mantener textos legacy;
8. reconstruir arbol solo despues de que las relaciones esten consolidadas.

Nunca sustituir un `App::Link` funcional solo para cumplir el nuevo esquema sin demostrar una ventaja y una migracion reversible.

## 11. Recomendacion provisional revisada

La hipotesis prioritaria pasa a ser:

> **`objeto_toma_uno.py` evoluciona como nucleo electromecanico comun de ElectricCR. La ruta directa y la ruta `App::Link` se mantienen como estrategias de representacion/instancia; `App::PropertyLink` incorpora relaciones semanticas; `Arch Equipment` se integra solamente si una prueba demuestra valor BIM/IFC o funcional que el nucleo actual no cubre.**

Esto preserva el trabajo ya funcional y evita crear una tercera arquitectura.

La refactorizacion futura deberia separar responsabilidades, conceptualmente:

```text
contrato neutral de dispositivo
        |
adaptador/servicio ElectricCR
        |
        +-- TomaUnoProxy directo
        |
        +-- App::Link + master
        |
        `-- adaptacion Arch Equipment, si resulta conveniente
```

Antes de programar deben definirse:

- propiedades comunes que deben vivir en la instancia;
- datos exclusivamente del master/representacion;
- enlaces `Space`, `Circuit`, `Panel`, `Control`, `System`, `Host`;
- identificador persistente del elemento;
- compatibilidad de `Tipo`, `KeyRegistro`, `AlturaRel`, `ModoVisual` y `OrientacionPared`;
- estrategia IFC sin forzar clases incorrectas;
- salida documental 2D;
- migracion legacy `dry_run`.


## 12. Primer prototipo recomendado cuando vuelva Codex

Usar **una sola luminaria** como familia piloto, porque ya existe RoomResolver integrado en el calculo, una estructura de arbol conocida y luminarias reales `App::Link`.

El prototipo no debe migrar el proyecto. Debe comparar, en documento temporal:

1. luminaria directa creada por el nucleo vigente;
2. luminaria `App::Link` vigente con master inmutable;
3. la misma instancia enriquecida con enlaces semanticos temporales (`Space`, `Circuit`, `Control`) sin tocar el master;
4. una variante `Arch Equipment` o adaptada a Equipment solo para medir que aporta y que rompe;
5. representacion 2D y 3D de una sola identidad;
6. reconstruccion de una rama minima del arbol desde relaciones;
7. save/reopen, Undo/Redo, rendimiento y exportacion 2D basica.

El criterio no es elegir la solucion mas nueva, sino conservar la funcionalidad actual con la menor complejidad y obtener semantica estable.

## 13. Evidencia real de La Cruz Version 2.1

El arbol exportado confirma que el flujo actual ya separa biblioteca e instancias:

```text
electrico
  _lib                       (oculto)
    Luminarias_Link_Masters  (oculto)
      Master Link Luminaria ...
  Luminaria_Link
    S.S. Familiar Mujeres_Luminaria_001   App::Link
    S.S. Familiar Hombres_Luminaria_002   App::Link
    Sala de Lactancia_Luminaria_003       App::Link
    ...
```

Esto refuerza dos decisiones de compatibilidad:

1. la biblioteca `_lib` y los masters ocultos son una arquitectura valida que debe conservarse durante el prototipo;
2. no conviene reemplazar masivamente las instancias `App::Link`; primero debe demostrarse si un Equipment puede envolver/referenciar el mismo master sin perder las ventajas actuales.

La futura reconstruccion del arbol debe distinguir claramente:

- biblioteca tecnica de masters;
- identidad/instancia colocada;
- contenedores de presentacion por circuito/recinto/control.

Los masters no deben aparecer mezclados con los elementos reales del proyecto.

## 14. Auditoria del codigo vigente `objeto_toma_uno.py`

La lectura directa del archivo vigente confirma:

### Propiedades del objeto directo

- `ModoVisual`: `Ambos`, `Solo2D`, `Solo3D`;
- `Categoria`: `Pared`, `Cielo`, `Piso`;
- `Tipo`: `Toma`, `Apagador`, `Luminaria`, `Sensor`, `Rociador`, `Altavoz`, `Camara`;
- `Giro`;
- `OffsetX`;
- `OffsetY`;
- `AlturaRel`;
- `OrientacionPared`: `Vertical`, `Horizontal`, `Auto`;
- `KeyRegistro`;
- `RecursoProto2D`;
- `RecursoProto3D`.

### Composicion geometrica

`_build_shape()` no altera el Placement. El 2D se coloca en Z local 0 y el 3D recibe `AlturaRel`. En modo horizontal solo el 3D recibe pitch de 90 grados sobre Y local. Ambos se combinan con `Part.makeCompound`.

Este comportamiento satisface una regla central del proyecto: modificar la altura 3D no debe elevar el simbolo 2D en planta.

### Masters y Links

La clave del master combina:

`KeyRegistro + Tipo + ModoVisual + OrientacionPared + AlturaRel`

`_get_or_create_master_toma()` reutiliza un `Part::FeaturePython` existente o crea uno nuevo y lo coloca bajo:

`electrico/_lib/_lib_devices`

`crear_toma_link()` crea una instancia `App::Link`, conserva `Placement` editable, asigna `LinkedObject` al master y copia a la instancia metadatos basicos (`Tipo`, `KeyRegistro`, `ModoVisual`, `AlturaRel`, `OrientacionPared`).

El servicio `set_installation_elevation()` confirma una regla correcta: para Links no se muta el master compartido; se obtiene/crea otro master compatible y se reasigna el `LinkedObject`, conservando Placement.

### Huecos respecto al contrato nuevo

El nucleo actual todavia no define uniformemente en la instancia:

- `ElementUID`;
- `Space`;
- `Circuit`;
- `Panel`;
- `Control`;
- `System`;
- `Level`;
- `Host`.

Tampoco separa aun un nucleo neutral de la dependencia FreeCAD/GUI, y la semantica BIM/IFC no esta formalizada.

Estos son los huecos a resolver. **No hace falta reinventar el manejo 2D/3D, la libreria de masters ni la altura semantica.**

## 15. Matriz de decision provisional

La comparacion actual queda asi:

| Criterio | `TomaUnoProxy` directo | `App::Link` vigente | `Arch Equipment` | Hibrido ElectricCR + Equipment |
|---|---|---|---|---|
| Evidencia funcional actual | alta | alta, incluyendo La Cruz | nativa pero no probada en ElectricCR | no probada |
| Una identidad 2D+3D | si, Shape compuesta | si, mediante master compuesto | por demostrar para simbolo 2D + modelo 3D | posible |
| Reutilizacion de geometria | baja/media | alta | media/por medir | alta potencial |
| Placement independiente por instancia | si | si | si | si |
| Altura 3D sin elevar simbolo 2D | ya resuelto | ya resuelto por master compatible | por implementar/probar | debe conservarse |
| Propiedades semanticas por instancia | facil | posible y ya existen metadatos basicos | nativo/extensible | posible |
| Compatibilidad con masters actuales | directa | total | no demostrada | posible mediante adaptador |
| Migracion de luminarias existentes | media | minima | alta | media |
| IFC | no nativo: requiere adaptacion | `App::Link` requiere pruebas en exportacion IFC | fuerte como objeto Arch/BIM con `IfcType` | potencialmente fuerte |
| Riesgo de regresion | medio | bajo para flujo actual | alto | medio |

### Decision provisional de trabajo

Para **dispositivos repetitivos colocados**, especialmente luminarias, la identidad operativa preferida para el primer prototipo sera la **instancia `App::Link` vigente**, enriquecida en la instancia con el contrato semantico minimo.

`TomaUnoProxy` se conserva como:

- nucleo geometrico/compatibilidad;
- creador de objetos directos cuando corresponda;
- base de los masters;
- referencia del comportamiento 2D/3D que no se puede perder.

`Arch Equipment` no se descarta, pero en el primer prototipo se usa como comparador nativo de BIM/IFC. No se autoriza aun una sustitucion de Links por Equipment.

La documentacion actual de FreeCAD advierte que las nuevas estructuras `App::Link` no estan completamente soportadas por el exportador IFC y requieren prueba. Por eso la necesidad de IFC se tratara como una prueba especifica, no como motivo suficiente para cambiar la identidad operativa.

## 16. Separacion de responsabilidades: registro, master e instancia

### Registro de tipos `registry_electric.json`

Debe seguir representando la **definicion de familia/tipo**, no una instancia colocada.

Datos apropiados en registro:

- clave de tipo (`KeyRegistro`);
- clase IFC objetivo cuando corresponda;
- categoria de montaje;
- recurso `symbol2D`;
- recurso `model3D`;
- altura/modo/orientacion por defecto;
- datos de catalogo y electricos comunes al tipo, por ejemplo potencia, lumenes, CCT, CRI, tension y dimensiones;
- version de la definicion.

La auditoria confirma que el registro vigente ya contiene ejemplos como `IfcOutlet`, `IfcCommunicationsOutlet`, `IfcSwitchingDevice` e `IfcLightFixture`.

### Master oculto

El master es una **representacion reutilizable e inmutable**, no un elemento del proyecto.

Puede contener o derivar:

- `KeyRegistro`;
- `Tipo`;
- `ModoVisual`;
- `AlturaRel` cuando la altura cambia la geometria del master;
- `OrientacionPared` cuando cambia la geometria;
- Shape 2D/3D resultante;
- recursos/procedencia de representacion.

No debe recibir:

- `ElementUID` de una instancia;
- `Space`;
- `Circuit`;
- `Panel`;
- `Control`;
- `System` de una instancia;
- `Host` de una instancia.

Debe permanecer oculto en `_lib` y excluido de la proyeccion del arbol de elementos reales.

### Instancia colocada

La instancia es la **identidad del elemento fisico real** en el proyecto.

Debe conservar:

- `Placement` y `Label`;
- `LinkedObject` cuando sea `App::Link`;
- espejo compatible de `Tipo`, `KeyRegistro`, `ModoVisual`, `AlturaRel` y `OrientacionPared` porque herramientas actuales ya los usan;
- identificador persistente de instancia;
- relaciones semanticas del proyecto;
- posibles overrides de instancia, sin mutar el master compartido.

## 17. Contrato semantico minimo recomendado para la instancia

Para el primer prototipo no se deben agregar todas las relaciones imaginables. El minimo recomendado es:

### Propiedades nuevas necesarias

- `ElementUID`: `App::PropertyString`, UUID estable de la instancia.
- `Space`: `App::PropertyLink` al `Arch/BIM Space` canonico cuando exista.
- `Circuit`: `App::PropertyLink` al objeto/grupo de circuito cuando exista una identidad de circuito utilizable.

### Relaciones que conservan autoridad existente durante la primera migracion

- `CircuitoID` y propiedades equivalentes: compatibilidad textual visible.
- control de luminarias: primero respetar los `PropertyLinkList` ya existentes en el objeto Control y los `ControlID`/`ApagadorID` legacy; no duplicar automaticamente una relacion bidireccional hasta definir cardinalidad y sincronizacion.
- `Recinto`/`AreaID`: compatibilidad legacy; `Space` tiene prioridad cuando existe.

### Datos que deben derivarse antes de duplicarse

- `Level`: derivar de `Space` siempre que sea posible.
- `Panel`: derivar de `Circuit` cuando el circuito tenga relacion con su tablero.
- `System`: derivar de Circuit/tipo/registro cuando exista una regla univoca; solo almacenar enlace propio si aparece un objeto System real y aporta valor.
- datos de familia/modelo/potencia: derivar de `KeyRegistro`/registro salvo override de instancia justificado.

### Relaciones opcionales posteriores

- `Host`: util para pared/cielo/piso, pero no bloquea el prototipo de luminaria.
- `Control`: enlace directo futuro si la auditoria demuestra que mejora el contrato sin competir con los LinkList del Control.

Este esquema reduce el riesgo de desincronizacion. La regla es: **enlazar la autoridad, derivar lo derivable y conservar los textos legacy durante la transicion**.

## 18. Arquitectura de codigo objetivo sin romper compatibilidad

`objeto_toma_uno.py` funciona, pero actualmente mezcla registro, FreeCAD, geometria, GUI opcional, masters y servicios de altura.

La evolucion preferida es gradual:

```text
device_core.py
  - contratos/records JSON-compatible
  - claves de tipo/master
  - normalizacion semantica
  - plan de proyeccion del arbol
  - sin FreeCAD / sin GUI
        |
freecad_device_adapter.py
  - leer/escribir propiedades FreeCAD
  - reconocer TomaUno directo / App::Link
  - PropertyLinks
  - masters y relink
        |
objeto_toma_uno.py
  - fachada de compatibilidad
  - mantiene crear_toma_uno / crear_toma_link
  - conserva comportamiento actual mientras se delega gradualmente
```

No es obligatorio usar exactamente esos nombres. La regla importante es **no romper imports/macros existentes y no sustituir de una vez el modulo funcional**.

## 19. Proyeccion idempotente del arbol

La reconstruccion futura de iluminacion debe ser un servicio separado de la identidad del dispositivo.

### Entrada autoritativa por luminaria

Orden recomendado:

1. reconocer instancia ElectricCR y excluir masters;
2. obtener `Circuit` link valido; fallback a `CircuitoID`/propiedad estable;
3. obtener `Space` link valido; fallback a `RoomResolver`;
4. obtener Control desde relacion fuerte existente (`PropertyLinkList` del Control o enlace explicito futuro); fallback a `ControlID`;
5. obtener nombres/Labels solo para presentacion.

`AMBIGUOUS` o `NOT_FOUND` de RoomResolver no deben provocar movimiento silencioso.

### Nodos de proyeccion

Los grupos creados por el reconstruidor deben identificarse internamente por claves estables, no por el texto visible. Conceptualmente cada nodo debe tener:

- rol de nodo (`SYSTEM`, `CIRCUIT`, `ROOM`, `CONTROL`, `DEVICES`);
- clave estable;
- Label humano;
- marca de que es un nodo de proyeccion ElectricCR;
- `PropertyLink` a la fuente semantica cuando exista, por ejemplo Space o Control.

Los nombres internos deben evitar tildes/caracteres problematicos.

### Reglas de aplicacion

- `dry_run` por defecto;
- crear/reusar nodos por clave;
- mover/quitar al elemento **solo de otros nodos de proyeccion ElectricCR** cuando la nueva ruta sea segura;
- no retirar pertenencias manuales o externas que no sean propiedad del reconstruidor;
- no tocar `_lib` ni masters;
- no mover el `Arch Space` real;
- repetir el proceso debe producir `0` cambios cuando las relaciones no cambiaron;
- reportar `CREATE_NODE`, `REUSE_NODE`, `MOVE`, `KEEP`, `AMBIGUOUS`, `NOT_FOUND` y conflictos equivalentes.

### Ruta visual de iluminacion

```text
electrico
  Iluminacion
    Circuitos
      <Circuito>
        Recintos
          <Recinto>
            Apagadores
              <Control/Apagador>
                Luminarias
                  <instancias reales>
```

Si falta Control no se debe inventar un apagador. El elemento debe quedar sin mover o en un contenedor diagnostico claramente identificado, segun se defina en el prototipo.

## 20. Criterio de entrada a la siguiente tarea Codex

El diseno ya permite definir un prototipo pequeno y reversible. Antes de programar, la siguiente tarea Codex debe limitarse a **una luminaria temporal** y comprobar:

1. instancia `App::Link` creada con el mecanismo vigente;
2. `ElementUID` persistente;
3. `Space` enlazado a un Space nativo sin escribir propiedades ElectricCR en el Space;
4. `Circuit` enlazado si existe un objeto/grupo de circuito de prueba y `CircuitoID` conservado;
5. Control obtenido por el mecanismo existente, sin forzar aun un nuevo enlace bidireccional;
6. `LinkedObject`, master, Placement, Label, 2D y 3D sin cambios por agregar semantica;
7. cambio de `AlturaRel` mediante relink mantiene UID y relaciones;
8. plan `dry_run` del arbol y aplicacion sobre documento temporal;
9. segunda reconstruccion idempotente con cero duplicados/cambios;
10. guardar/cerrar/reabrir conserva identidad, links y arbol;
11. comparacion separada con `Arch Equipment` para IFC, sin sustituir la instancia vigente;
12. prueba 2D documental/exportable basica.

Si esta prueba aprueba, la siguiente familia natural es tomacorrientes; despues apagadores/Control.

## 21. Resultado del prototipo real en FreeCAD 1.1.3

El prototipo se ejecuto el 2026-09-01 y confirma la alternativa B para la fase
actual: la instancia `App::Link` existente puede recibir `ElementUID` y `Space`
sin cambiar su master, Placement o representacion. En esta fase no se agrego un
`Circuit` nuevo; `CircuitoID` y los LinkList de Control fueron suficientes y se
mantuvieron como autoridad vigente.

Hallazgos confirmados:

- RoomResolver debe recibir el punto global de la instancia; desenvolver el
  `App::Link` llevaria al Placement del master y resolveria un recinto erroneo;
- `AMBIGUOUS` y `NOT_FOUND` conservan `Space=None`;
- el relink por altura conserva UID, Space y Placement;
- simbolo 2D y modelo 3D siguen en la misma identidad y la salida DXF basica
  acepta el Link;
- `EsPrototipo` permite que los masters sigan ocultos despues de execute,
  recompute y reapertura;
- `Arch Equipment` aporta `GlobalId`, `IfcProperties` e `IfcType=Light Fixture`,
  pero su ruta Base/Shape duplica o controla geometria en vez de compartir el
  master con la ligereza del Link.

### Ajuste confirmado para la proyeccion

Un objeto agregado a otro `App::DocumentObjectGroup` pierde su pertenencia
visual anterior. Por ello el reconstruidor no coloca la instancia fisica en la
rama: crea/reusa una referencia indice `App::Link` de proyeccion, enlazada por
UID a la instancia real. Ese indice es reproducible, no contiene `ElementUID` o
`Space` propios y no representa otra identidad electromecanica.

La segunda ejecucion sin cambios materializo cero modificaciones. El Space
permanecio en Building/Level y los masters en `_lib`. Este resultado valida el
nucleo puro + adaptador FreeCAD como patron, pero no autoriza una migracion
masiva ni la siguiente familia.
