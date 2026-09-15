## Actualizacion 2026-09-09 22:09 -0600 America/Costa_Rica - banco de pruebas canonico del dispositivo comun

Se materializo la Demo ElectricCR A1 v0.1 como instrumento permanente de regresion. Sigue la arquitectura preferida del proyecto: especificacion pura JSON-compatible -> adaptador FreeCAD -> auditor -> comando/boton -> `.FCMacro` pequeno.

La demo no crea una nueva clase de dispositivo: llama a la fabrica A1 vigente, al adaptador semantico y al PLAN existente. Su objetivo es someter el mismo nucleo a un escenario conocido con dos Spaces BIM y varias familias antes de ampliar Circuit, Control o IFC.

Estado: implementacion Drive + 7/7 pruebas puras; FreeCAD 1.1.3 real pendiente.

---

## Diseno 2026-09-09 22:09 -0600 America/Costa_Rica - frontera A1 / IFC

A1 se conserva como nucleo operativo del elemento electromecanico. NativeIFC/IfcOpenShell se estudia como infraestructura de interoperabilidad y no como segunda autoridad persistente.

Regla de arquitectura:

```text
fuente de verdad de diseno:  A1 Owner
identidad ElectricCR:         ElementUID
autoridad espacial:           Owner.Placement
geometria fisica:             LinkedObject/master A1
documentacion planta:         PLAN owned
intercambio BIM:              adaptador IFC transitorio
```

El adaptador debe poder recibir un archivo IFC ya inicializado por FreeCAD, crear o localizar el producto electrico correspondiente y mantener una tabla temporal `Owner.Name -> IfcEntity`. Esto permite reutilizar los `IfcSpace` del mismo archivo para containment sin introducir un `Space` duplicado.

No convertir/agregar automaticamente Owners A1 productivos mediante `NativeIFC.aggregate()`, porque la ruta puede sustituir el objeto FreeCAD original. Cualquier experimento de conversion debe hacerse solo en documento desechable.

Mapeo inicial de identidad recomendado para probar:
- `ElementUID` -> `GlobalId` determinista;
- `KeyRegistro`/familia -> clase, `PredefinedType` y futuro `IfcTypeProduct`;
- `Owner.Placement` -> `ObjectPlacement`;
- master fisico -> `Representation`;
- `Space` -> containment en el `IfcSpace` correspondiente;
- propiedades electricas -> Psets estandar cuando exista equivalencia.

El master A1 actual no es todavia equivalente semantico de un IFC Type porque su firma incluye parametros de ocurrencia. No optimizar por `IfcRepresentationMap` hasta separar y probar claramente definicion de familia y ocurrencia.

PLAN no se exporta como segundo `IfcOutlet`/`IfcSwitchingDevice`/`IfcLightFixture`. Una futura representacion `IfcAnnotation` en contexto Plan es opcional y documental.

Instrumento de prueba recomendado: Demo ElectricCR autocontenida y reproducible, siguiendo el patron de la Demo Casa de 2 Plantas. Debe crear el escenario desde cero y servir simultaneamente como ejemplo de usuario y prueba de regresion. No se implementa hasta autorizacion expresa.

---

## Decision de diseno 2026-09-05 - feedback documental y arbol hospedado

La seleccion A1 se separa asi:

```text
identidad/seleccion logica = Device/Owner App::Link
representacion documental  = PLAN Part::Feature
feedback persistente PLAN  = overlay GUI-only descartable
```

En FreeCAD 1.1.3 la preseleccion nativa completa es solo hover. Para feedback persistente se reutiliza `draftguitools.gui_trackers.ghostTracker`; PLAN no se agrega a `Gui.Selection` ni adquiere autoridad propia. PLAN puede permanecer visible en viewport y oculto en el arbol (`ShowInTree=false`).

### Host y proyeccion visual

La relacion `Device.Host -> Wall` sigue siendo autoridad semantica A1 y **no se convierte a hidden por ahora**. La razon es funcional: BIM/Arch usa el backlink del host no solo para `claimChildren()` del arbol, sino tambien para descubrir hijos movibles mediante `getMovableChildren()`.

Por tanto, la multiparentalidad visual debe resolverse sin romper esa relacion hasta que una prueba demuestre una alternativa equivalente. `ClaimHosted=False` es una opcion nativa de presentacion, pero global; la referencia indice/proyeccion electrica es la alternativa localizada ya contemplada en el contrato del arbol.

Regla provisional:
- no usar `PropertyLinkHidden Host` solo para limpiar el arbol;
- no alterar globalmente `ClaimHosted` desde ElectricCR sin decision explicita;
- no duplicar la identidad fisica;
- si se usa referencia de proyeccion, debe ser documental/indice, no autoridad funcional, y seleccionar/operar siempre sobre Owner.

---

## Diseno 2026-09-05 20:22 - feedback PLAN completo y enlace Owner oculto al dependency checking

### Feedback visual sin segunda seleccion

La evidencia real de Upala muestra que el pick nativo de un PLAN `Part::Feature` identifica
un subelemento concreto (`Edge`, `Vertex`) y resalta solamente esa linea/punto. Para A1 eso
no representa correctamente la identidad visual del dispositivo.

El contrato se mantiene:

```text
Gui.Selection = Owner exclusivamente
feedback visual = PLAN completo
```

Primera solucion nativa adoptada en prueba:

```python
Gui.Selection.setPreselection(plan, "")
```

El subname vacio pide preseleccion del DocumentObject completo. `plan_selection.py` normaliza
la preseleccion de cualquier subelemento PLAN a ese estado y, despues de redirigir un clic a
Owner, vuelve a aplicar la preseleccion completa porque una operacion de seleccion puede
limpiar la preseleccion previa.

Esta tecnica sigue siendo provisional hasta prueba real de persistencia/UX. Si el highlight
completo desaparece de forma inaceptable al mover el cursor, el siguiente nivel sera un
overlay/ViewProvider minimo, sin introducir PLAN en la seleccion logica.

### PLAN.Owner como PropertyLinkHidden

Para una representacion documental owned, `PLAN.Owner` no debe provocar el dialogo
`The following referencing objects might break` al borrar el dispositivo. FreeCAD 1.1.3
define `App::PropertyLinkHidden` para enlaces excluidos del dependency checking, y Draft Layer
usa la familia `*Link*Hidden` precisamente para evitar ese aviso en relaciones de pertenencia.

Contrato provisional implementado:

```text
PLAN.Owner : App::PropertyLinkHidden
PLAN.Placement <- expression through Owner
Delete Owner -> lifecycle elimina PLAN
```

Los PLAN A1 legacy con `App::PropertyLink` se migran solo cuando pasan por
`sync_plan_representation()`, dentro de la transaccion existente. La migracion:

1. conserva Owner y expresiones;
2. limpia temporalmente expresiones que dereferencian Owner;
3. reemplaza la propiedad dinamica por `App::PropertyLinkHidden`;
4. restaura Owner/expresiones;
5. vuelve a verificar el binding canonico de Placement.

No se cambia `RepresentationSchemaVersion`, porque el esquema espacial/documental sigue siendo
el mismo; cambia solo la semantica de dependency checking del enlace owned.

Criterio de cierre real: movimiento, giro, recompute, Delete sin aviso, lifecycle, Undo/Redo,
save/reopen y cero PLAN huerfanos en FreeCAD 1.1.3.

---

## Diseno 2026-09-05 - contrato visual A1 integrado con ModoVisual historico

A1 no introduce un segundo sistema de visibilidad. El contrato historico ElectricCR:

```text
ModoVisual = Ambos | Solo2D | Solo3D
```

se conserva como interfaz de alto nivel y se traduce a las representaciones separadas:

```text
ModoVisual   MostrarModelo3D   MostrarSimboloPlano
Ambos        true              true
Solo2D       false             true
Solo3D       true              false
```

`Owner.ViewObject.Visibility` representa la visibilidad fisica 3D.
`PLAN.ViewObject.Visibility` representa la visibilidad documental de planta.

`MostrarModelo3D` y `MostrarSimboloPlano` pueden seguir controlandose directamente. Si su
combinacion corresponde a un modo canonico, `ModoVisual` se refleja para mantener
compatibilidad con herramientas historicas.

Cambiar visibilidad:
- no modifica `Device.Placement`;
- no modifica la expresion PLAN<-Owner;
- no regenera Shape 3D;
- no regenera Shape PLAN;
- no afecta DXF salvo naturalmente si el exportador decide respetar Visibility.

El gestor existente `Gestionar_Visibilidad_ElectricCR.FCMacro` debe ser reutilizado como
interfaz principal. El nucleo A1 se adapta a el, no al contrario.

---

## Diseno 2026-09-05 16:10 - refresco interactivo sin segunda autoridad

La expresion PLAN<-Owner garantiza coherencia al recomputar, pero el dragger nativo de
`ViewProviderLink` actualiza `Owner.Placement` mas rapido que el ciclo normal de recompute.
El resultado de campo fue una separacion visual temporal que desaparece con F5.

No se cambia la autoridad espacial ni se asigna PLAN manualmente. Se agrega un adaptador App-only:

```text
slotChangedObject(Owner, Placement)
        -> resolver PLAN
        -> PLAN.recompute()
```

Esto reutiliza `DocumentObject.recompute()`/`recomputeFeature()` para recomputar unicamente la
representacion documental. No usar `doc.recompute()` en cada movimiento del mouse.

Reglas de seguridad:

- no ejecutar durante `Document.isPerformingTransaction()`;
- no actuar sobre objetos en eliminacion;
- no regenerar Shape PLAN;
- no modificar `Owner.Placement`;
- no crear dependencia bidireccional;
- si el refresco dirigido degrada rendimiento o causa reentrancia, retirarlo y buscar un
  mecanismo de ViewProvider/escena grafica para preview, manteniendo la expresion como estado persistente.

### Undo/Redo del ciclo de vida

El observer de borrado nunca debe mutar objetos durante Undo/Redo/rollback. FreeCAD expone
`Document.isPerformingTransaction()` especificamente para esa fase. La transaccion original ya contiene
los objetos creados/eliminados y debe ser reproducida por FreeCAD sin intervencion del observer.

### Transformar versus Snap Special

- `Transformar`: usa el dragger de `ViewProviderLink`; no consume Draft Snap Special.
- `Draft Move`: pide punto base/destino y si consume los modos Draft Snap.
- `Snap Special`: permite que Draft capture `PLAN.SnapPoints=[(0,0,0)]`; no mueve nada por si mismo.

---

## Diseno 2026-09-05 15:43 - seleccion visual, visibilidad y dependencia de borrado

### Seleccion logica versus feedback visual

La validacion real demuestra que la redireccion PLAN -> Owner es correcta, pero FreeCAD
resalta solamente la geometria visible del Owner. Por tanto:

```text
seleccion logica = Owner exclusivamente
feedback visual  = debe poder incluir PLAN sin agregarlo a Selection
```

No mantener Owner y PLAN simultaneamente en `Gui.Selection`, porque herramientas
genericas podrian procesar ambos como objetos editables.

Primera alternativa nativa: `Gui.Selection.setPreselection()` para PLAN mientras Owner
permanece seleccionado. Es solo candidata porque la preseleccion es transitoria. Si no es
estable, el siguiente nivel es un overlay visual de ViewProvider/Coin limitado a PLAN.

### Visibilidad independiente

La prueba real confirma que ocultar el `App::Link` Owner oculta la representacion fisica
3D y no el PLAN documental. Esto es correcto y se convierte en parte del contrato:

```text
Owner.ViewObject.Visibility = false
PLAN.ViewObject.Visibility  = true
-> modo de trabajo planta 2D
```

La independencia de visibilidad no implica independencia espacial ni semantica.

### Borrado y PropertyLinkHidden

`plan_lifecycle.py` ya consigue eliminar Owner + PLAN, pero `Std_Delete` muestra un aviso
porque `PLAN.Owner` participa en el grafo normal de dependencias.

FreeCAD define `App::PropertyLinkHidden` como un `PropertyLink` oculto al chequeo de
dependencias. Es el candidato nativo para una relacion documental owned que no deba
provocar el dialogo de borrado.

Riesgo principal: al ocultar la arista al dependency checking puede cambiar la forma en
que FreeCAD decide recomputes. Como `PLAN.Placement` usa una expresion que atraviesa
`.Owner`, no se debe adoptar sin prueba real de propagacion.

Criterio de adopcion:

```text
PropertyLinkHidden
  + expresion dinamica intacta
  + Delete sin aviso
  + lifecycle cascade
  + Undo/Redo
  + save/reopen
  = REUTILIZAR

si rompe propagacion/recompute
  = DESCARTAR para Owner
```

No sustituir `ViewProviderLink`, no crear un Delete paralelo y no ocultar la dependencia
solo para silenciar la GUI si ello debilita el modelo parametrico.

### Snap Special

`Draft Snap Special` es el consumidor nativo de `SnapPoints`. Para PLAN:

```text
SnapPoints = [(0,0,0)]
```

representa el punto base/registration point comun. Su activacion manual sirve para la
prueba, pero la UX final puede encapsularla si se demuestra que el usuario no debe
gestionar modos de snap para una operacion ElectricCR habitual.

---

## Diseno 2026-09-05 - punto de insercion/snap comun A1

### Contrato

Todo PLAN A1 debe exponer un punto de insercion local canonico:

```text
SnapPoints = [Vector(0,0,0)]
```

Ese punto representa:
- origen local del simbolo;
- punto de insercion;
- referencia preferente para Draft Move;
- snap comun aunque la geometria STEP no tenga vertex en el origen;
- la misma posicion XY autoritativa del Device, proyectada al plano documental.

No es una segunda coordenada. FreeCAD Draft transforma `SnapPoints` mediante el
`Placement` del objeto. Como `PLAN.Placement` deriva de `Owner.Placement`, el snap
mundial permanece coherente automaticamente.

### Motivo para usar SnapPoints

Se prefiere `SnapPoints` a agregar un `Part::Vertex` visible a cada Shape porque:
- es una capacidad nativa consumida por Draft Snap Special;
- no altera Shape ni DXF;
- funciona igual para simbolos con endpoint, circulo centrado o sin geometria
  capturable en el centro;
- evita modificar los STEP fuente solo para UX;
- permite mantener una sola autoridad espacial.

Los puntos geometricos ya presentes en los STEP se conservan. Endpoint/Center
siguen funcionando y Snap Special agrega una referencia uniforme.

### Integracion de interfaz

`Draft compacto` debe conservar `Draft_Move` y exponer `Draft_Snap_Special`.
No crear un comando ElectricCR de movimiento mientras el flujo nativo resuelva el
caso real.

### Auditoria inicial

- `toma_normal.step`: endpoint en origen.
- `switch_simple.step`: punto geometrico explicito en origen.
- `etiqueta_circuito.step`: endpoint en origen.
- `Luminaria_LED_Redonda_1000lm_2D.step`: centro circular en origen.
- `Luminaria 60x60.step`: sin vertex/curva de snap en origen.
- `Sensor de Humo.step`: centros geometricos en origen, sin punto explicito
  equivalente al apagador.

`SnapPoints` hace que estas diferencias de construccion interna no cambien la UX.

---

## Diseno 2026-09-05 - ciclo de vida de representaciones documentales A1

La regla "una identidad" tambien aplica al borrado.

Contrato:

```text
Device / Owner
   |
   +-- Shape fisica
   `-- PLAN DocumentationOnly

Delete Device
   -> desaparece Device
   -> desaparecen sus representaciones owned/documentales
```

Un PLAN con `Owner=null` despues de borrar el dispositivo es un estado invalido y debe
considerarse un huerfano, no una representacion independiente recuperable.

### Por que no se adopta PropertyLinkChild como solucion suficiente

`PropertyLinkChild` expresa un enlace de alcance Child/claimed-child, pero la evidencia
nativa revisada no permite tratarlo como garantia de borrado en cascada. Ademas,
reorganizar el arbol o el ViewProvider solo para conseguir borrado introduciria un
cambio arquitectonico mayor.

### Mecanismo actual

Se conserva:

```text
PLAN.Owner : App::PropertyLink
Owner.DocumentationRepresentationName : String
PLAN.Placement <- expresion Owner.Placement
```

y se agrega un adaptador de ciclo de vida App-only:

```text
App DocumentObserver
    slotDeletedObject(Owner A1)
        -> identificar PLAN
        -> eliminar PLAN en la misma transaccion cuando sea posible
```

El adaptador vive en `electriccr/features/plan_lifecycle.py`, no depende de
`FreeCADGui`, no sincroniza Placement y no sustituye `ViewProviderLink`.

La instalacion se realiza al inicializar ElectricCR y permanece activa aunque luego se
cambie de Workbench, porque el ciclo de vida es parte del contrato del documento.

Antes de considerarlo definitivo debe probarse en FreeCAD 1.1.3:

- Delete normal;
- Undo/Redo en un solo paso;
- documentos multiples;
- save/reopen;
- ausencia de efectos sobre LegacyCompound;
- ausencia de eliminacion cruzada entre documentos.

---

## Investigacion 2026-09-05 - patron nativo de manipulacion confirmado

La UX 2D de A1 no debe inventar un sistema de grips paralelo. La investigacion del codigo oficial de FreeCAD confirma que la infraestructura nativa ya contiene los conceptos necesarios.

### ViewProviderDragger

`Gui::ViewProviderDragger` es la base para ViewProviders que modifican `Placement`.

El mecanismo relevante es:

```text
Object.Placement
      |
      +-- TransformOrigin
      |
      `-- dragger
```

FreeCAD calcula la ubicacion del manipulador a partir de:

```text
ObjectPlacement * TransformOrigin
```

y al terminar una operacion escribe el nuevo valor en la propiedad `Placement` del objeto.

Para ElectricCR, el contrato preferido queda:

```text
TransformOrigin = identidad local / (0,0,0)
Device.Placement = unica autoridad espacial
```

Por tanto, el origen local del simbolo y el origen del manipulador pueden ser el mismo concepto, sin introducir una propiedad espacial paralela.

### ViewProviderLink

`Gui::ViewProviderLink`, usado por `App::Link`, ya implementa infraestructura especifica de transformacion:

- modo de edicion `Transform`;
- `DraggerContext`;
- `initDraggingPlacement()`;
- `currentDraggingPlacement()`;
- `updateDraggingPlacement()`;
- `setEditViewer()`;
- dragger Coin propio.

Ademas, el nucleo GUI de FreeCAD contiene `ViewProviderDragger.forwardToLink()`, que reenvia una edicion al primer `App::Link` encontrado en una cadena de subobjetos. Ese patron demuestra que **editar una representacion pero transformar la instancia Link** es un comportamiento nativo de FreeCAD.

El PLAN A1 no forma hoy parte de esa cadena de subobjetos, por lo que no se asume que la redireccion funcione automaticamente. Sin embargo, el patron de diseno debe imitar esa filosofia antes de crear infraestructura nueva.

### Draft Move y Snap

`Draft Move` ya proporciona la UX CAD clasica:

```text
seleccionar objeto
-> punto base
-> punto destino
-> mover
```

y funciona con objetos 2D y muchos objetos 3D. Draft Snap permite capturar puntos geometricos exactos.

Por eso, `(0,0,0)` del simbolo debe ser el punto de insercion/snap preferente y no una coordenada separada.

### Orden de preferencia definitivo

```text
1. ViewProviderLink Transform nativo
2. TransformOrigin en el origen local
3. Draft Move + Draft Snap
4. redireccion PLAN -> Owner con mecanismo minimo de seleccion
5. SelectionObserver solo si hace falta
6. dragger propio ElectricCR solo como ultimo recurso
```

Esta decision reduce el riesgo de inventar una UX paralela a FreeCAD y alinea ElectricCR con patrones CAD clasicos de bloque/instancia, grip/base point y transformacion de una unica identidad.

---

## Estudio previo 2026-09-05 - interaccion 2D como interfaz del dispositivo

### Nuevo requisito funcional

La sincronizacion espacial A1 resuelta por expresion cubre correctamente el
sentido `Device.Placement -> PLAN.Placement`, pero no cubre por si sola la
edicion desde la representacion 2D.

El requisito de producto se amplia:

```text
                 misma identidad
                      Device
                        |
                 Placement unico
                 /             \
                /               \
        representacion 3D    representacion PLAN
              visible              visible
              o no                 o no
                ^                   ^
                |                   |
          mover desde 3D      mover desde 2D
                \                   /
                 \                 /
                  -> Device.Placement
```

Reglas:

- el usuario debe poder trabajar con el modelo 3D oculto y operar ElectricCR
  practicamente como un plano 2D normal;
- hacer clic sobre PLAN debe seleccionar la identidad principal `Owner`, no el
  auxiliar documental;
- PLAN puede seguir existiendo como `Part::Feature DocumentationOnly`, pero no
  debe presentarse como una segunda identidad de trabajo;
- mover desde 2D debe escribir en `Owner.Placement`; la expresion vigente vuelve
  a colocar PLAN y el 3D sigue al mismo Owner;
- no crear una expresion bidireccional PLAN <-> Owner ni dos Placement
  autoritativos;
- la seleccion y el movimiento 2D son una capa de interaccion, no un segundo
  modelo de datos.

### Arbol y seleccion

El PLAN documental debe tender a:

```text
PLAN.ViewObject.ShowInTree = false
```

para evitar que al hacer clic en el simbolo aparezca un objeto auxiliar como si
fuera el elemento funcional.

La seleccion deseada es:

```text
clic sobre Shape PLAN
        -> resolver PLAN.Owner
        -> seleccionar Owner
        -> propiedades/arbol/comandos operan sobre Owner
```

No se debe cambiar `PLAN.Owner` ni eliminar el PLAN del documento, porque sigue
siendo la representacion documental consumible por DXF.

La investigacion de FreeCAD confirma que `ViewProvider` dispone de manejo de
seleccion y que los objetos de vista tienen `Selectable` y `ShowInTree`.
Sin embargo, el PLAN actual conserva el ViewProvider nativo de `Part::Feature`.
Por tanto, las alternativas a probar en FreeCAD 1.1.3 son:

1. mediador de seleccion `Gui.Selection` limitado a ElectricCR, que al detectar
   un objeto `DocumentationOnly/PLAN` reemplace la seleccion por `Owner`;
2. solo si lo anterior no es robusto, evaluar un ViewProvider/proxy especifico
   para PLAN;
3. no sustituir el ViewProvider nativo del `App::Link` principal.

Un mediador de seleccion, si se usa, debe ser estrictamente acotado:

- registrarse una sola vez;
- actuar solo sobre PLAN ElectricCR con Owner valido;
- usar guardia contra recursion al cambiar la seleccion;
- no modificar geometria ni propiedades de documento al seleccionar;
- retirarse/desactivarse al desactivar el Workbench cuando corresponda;
- probar con varios documentos abiertos.

La decision anterior de descartar un observador GUI se referia a la
**sincronizacion espacial**, donde la expresion nativa era suficiente. No se
extiende automaticamente a esta nueva necesidad de UX de seleccion.

Existe un reporte de regresion de `Gui.Selection` en FreeCAD 1.2dev con varios
documentos, mientras 1.1.1 se reporta como comportamiento correcto. ElectricCR
usa 1.1.3, por lo que la seleccion redirigida debe verificarse expresamente en
1.1.3 con dos o mas documentos abiertos antes de adoptarla.

### Movimiento desde 2D

Primera opcion: reutilizar `Draft Move`.

FreeCAD permite mover objetos 2D y 3D seleccionados indicando un punto base y un
punto destino. Si el clic sobre PLAN selecciona realmente al Owner, el flujo
esperado es:

```text
3D oculto
PLAN visible
clic PLAN -> Owner seleccionado
Draft Move
punto base = origen/insercion del simbolo
punto destino = nueva posicion
        -> Owner.Placement cambia
        -> PLAN sigue por expresion
        -> al mostrar 3D aparece en la nueva posicion
```

Debe probarse que `Draft Move` acepte correctamente el Owner seleccionado aunque
su representacion 3D este oculta. Si no, se podra crear un adaptador/comando
ElectricCR minimo que reutilice la captura de puntos/snaps de Draft pero escriba
explicitamente en `Owner.Placement`.

No crear inicialmente un dragger Coin propio si la herramienta nativa resuelve
el flujo.

### Contrato del punto de insercion 2D

Todos los prototipos 2D ElectricCR deben tener como punto de insercion local:

```text
(0, 0, 0)
```

Ese origen debe coincidir con:

- `Device.Placement.Base` en coordenadas globales despues de transformar;
- punto base preferente para mover;
- referencia de snap/insercion;
- punto de alineamiento entre representacion PLAN y modelo fisico.

Para los simbolos donde ya existe un punto dibujado en el origen, debe
conservarse y usarse. Antes de modificar recursos, auditar todos los prototipos
2D para comprobar que contienen una entidad/vertice utilizable en `(0,0,0)`.

`Arch Equipment.SnapPoints` confirma que FreeCAD dispone del concepto de puntos
de snap personalizados, pero esa propiedad no resuelve por si sola seleccion ni
movimiento y no debe introducirse como una segunda arquitectura. Puede servir de
referencia o alternativa si un prototipo no expone un vertice utilizable.

No insertar automaticamente geometria visible adicional en todos los PLAN antes
de comprobar el efecto en DXF y en los simbolos existentes.

### Criterio UX futuro

A1 no se considera terminado desde la perspectiva de edicion 2D hasta aprobar:

```text
clic PLAN -> Owner seleccionado
PLAN no aparece como identidad auxiliar en el arbol
3D oculto + PLAN visible -> trabajo 2D posible
Draft Move desde origen 0,0,0 -> Owner se mueve
PLAN sigue al Owner
mostrar 3D -> 3D coincide con PLAN
mover 3D -> PLAN sigue
Undo/Redo -> ambas representaciones coherentes
save/reopen -> comportamiento persiste
varios documentos abiertos -> seleccion no se cruza
```

Hasta cerrar esta UX, mantener A1 opt-in y no iniciar migracion legacy.

---

## Mecanismo definitivo 2026-09-05 - Placement PLAN derivado por expresion

La alternativa nativa fue probada y seleccionada. PLAN conserva el TypeId
`Part::Feature`; no requiere proxy ni observador GUI. Su propiedad `Owner`
continua como `App::PropertyLink` y gobierna una expresion persistente:

```text
PLAN.Placement = placement(
  vector(Owner.Placement.Base.x;
         Owner.Placement.Base.y;
         Owner.DocumentationPlaneZ);
  Owner.Placement.Rotation
)
```

Consecuencias del contrato:

- `Device.Placement` es la unica autoridad para X/Y/orientacion;
- PLAN no ofrece una segunda posicion espacial editable;
- `DocumentationPlaneZ` reemplaza solamente Z en la transformacion derivada;
- `PlanSymbolScale` modifica solo la Shape 2D local;
- cambiar altura/relink de master no afecta Placement del Owner ni del PLAN;
- FreeCAD almacena la dependencia en `ExpressionEngine`, la recompone en
  recompute y la conserva en Undo/Redo y save/reopen;
- `Owner` aparece en `PLAN.OutList`, sin enlace inverso estructural que produzca
  ciclos.

`RepresentationSignature` pasa a esquema 2 y queda limitada a:

```text
(schema_version, KeyRegistro, Giro, OffsetX, OffsetY, PlanSymbolScale)
```

Placement, quaternion, UID y `DocumentationPlaneZ` ya no forman parte de la
firma. Por tanto, movimiento, giro o cambio de plano documental actualizan la
transformacion sin reconstruir la geometria del simbolo. La escala si cambia la
firma porque requiere regenerar la Shape 2D.

### Alternativas cerradas

| alternativa | decision |
|---|---|
| expresion nativa en `Part::Feature` | seleccionada; menor cambio y dependencia persistente |
| `Part::FeaturePython` | reserva no necesaria; agregaria proxy y ciclo de restauracion |
| observador global GUI/Qt | descartado; innecesario y dependiente de interfaz |

Los PLAN esquema 1 se actualizan idempotentemente cuando pasan por
`sync_plan_representation`. No se realiza barrido automatico ni migracion del
documento productivo.

---

## Actualizacion historica de diseno 2026-09-03 - una sola autoridad espacial

### Hallazgo de campo

La separacion `PhysicalDocumentationA1` resolvio correctamente la contaminacion
de la Shape fisica por el simbolo 2D, pero un uso real en Chomes revelo que la
representacion PLAN conserva actualmente un `Placement` independiente.

Caso observado:

```text
Device Placement X = 19263
PLAN Placement X   = 19004
PLAN.Owner          = Device
PLAN.ExpressionEngine = []
```

La diferencia de 259 mm demuestra que `Owner` expresa pertenencia pero no una
dependencia espacial dinamica.

### Contrato corregido

La arquitectura A1 debe distinguir entre independencia de representacion e
independencia espacial:

```text
                     Device / unica identidad
                              |
                       Placement autoritativo
                         /             \
                        /               \
             Physical representation   PLAN representation
             Shape 3D                   Shape 2D documental
                                        Z/scale/visibility documentales
```

Reglas:

- 2D y 3D permanecen geometricamente separados;
- `Device.Placement` es la unica autoridad para X/Y y orientacion;
- PLAN deriva X/Y y orientacion del Owner;
- `DocumentationPlaneZ` controla solamente la cota documental;
- `PlanSymbolScale` controla solamente la escala documental;
- un eventual offset documental debe ser una propiedad explicita, no un
  Placement libre que pueda divergir accidentalmente;
- cambiar altura fisica/relink no altera XY/orientacion de PLAN.

### Implicacion para `sync_plan_representation`

`sync_plan_representation` no puede ser el unico mecanismo que mantiene la
coherencia espacial si solo se llama durante creacion o sincronizaciones
explicitas. El documento debe contener una dependencia persistente suficiente
para que una edicion manual de Placement se propague despues de recompute.

Antes de implementar, comparar en FreeCAD 1.1.3:

1. dependencia nativa por expresiones manteniendo PLAN como `Part::Feature`;
2. PLAN `Part::FeaturePython` con `Owner` como entrada y proxy documental;
3. solo como ultimo recurso, sincronizacion imperativa mediante eventos.

Se prefiere una dependencia nativa almacenada en el documento y sin acoplamiento
innecesario a GUI/Qt.

### RepresentationSignature

La firma debe representar la configuracion de la representacion documental, no
ser la unica fuente de sincronizacion de Placement.

Auditar la inclusion actual de coordenadas/rotacion. Idealmente, mover un
objeto no reconstruye el simbolo si familia, variante, escala y esquema no han
cambiado; solo actualiza su transformacion derivada.

### Nuevo criterio A1

A1 no se considera completo mientras no apruebe movimiento y rotacion manual
del Owner con seguimiento automatico de PLAN, ademas de las pruebas ya
existentes de Shape, DXF, save/reopen, Undo/Redo e idempotencia.

---

# Diseno del objeto electromecanico comun - ElectricCR

Fecha: 2026-09-03 America/Costa_Rica
Estado: `A1 FISICO/DOCUMENTAL CON AUTORIDAD ESPACIAL IMPLEMENTADA Y PROBADA / OPT-IN`
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

La auditoria inicial encontro este contrato geometrico **legacy**:

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
- en `LegacyCompound`, el simbolo y el modelo se combinan en una sola `Shape`;
- en `PhysicalDocumentationA1`, implementado el 2026-09-03, la `Shape` conserva
  solamente el modelo fisico y PLAN se materializa aparte como documentacion de
  la misma identidad;
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

## 6. Una identidad, dos representaciones (estudio previo a A1)

Regla del proyecto:

> 2D y 3D deben ser representaciones de la misma identidad, no dos objetos funcionales independientes.

Se deben comparar cuatro patrones.

### Alternativa A - evolucion del nucleo directo `TomaUnoProxy`

El objeto colocado sigue siendo un `Part::FeaturePython` del nucleo existente.
La composicion en una sola Shape corresponde al comportamiento legacy y no
satisface el contrato A1 fisico/documental.

Ventajas:

- conserva una identidad, pero mezcla dos clases de representacion;
- altura 3D independiente del simbolo de planta;
- menor migracion conceptual;
- propiedades y registro existentes;
- facil de extender con enlaces semanticos.

Riesgos/preguntas:

- costo geometrico si hay cientos de elementos directos;
- semantica BIM/IFC no nativa;
- separar mejor nucleo de GUI/FreeCAD y evitar crecimiento monolitico.

### Alternativa B - evolucion de la ruta `App::Link` actual

El objeto colocado sigue siendo un `App::Link`. El master compuesto 2D+3D queda
clasificado como legacy; A1 exige un master fisico separado.

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


## 12. Primer prototipo recomendado (historico; ya ejecutado)

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

### Composicion geometrica diagnosticada y corregida

`_build_shape()` no altera el Placement. Antes de A1, el 2D se colocaba en Z
local 0, el 3D recibia `AlturaRel` y ambos se combinaban con
`Part.makeCompound`. Ese fue el diagnostico real; la documentacion por si sola
no demostraba separacion.

Ahora el comportamiento depende de un contrato explicito:

- `LegacyCompound`: conserva la composicion anterior para compatibilidad;
- `PhysicalDocumentationA1`: `Part.makeCompound` recibe exclusivamente una
  copia transformada de `model3D`; `symbol2D` se usa solamente para PLAN.

En A1, modificar la altura fisica no eleva PLAN porque son Shapes distintas.

### Masters y Links

La clave del master combina:

`KeyRegistro + Tipo + ModoVisual + OrientacionPared + AlturaRel`

`_get_or_create_master_toma()` reutiliza un `Part::FeaturePython` existente o crea uno nuevo y lo coloca bajo:

`electrico/_lib/_lib_devices`

`crear_toma_link()` crea una instancia `App::Link`, conserva `Placement` editable, asigna `LinkedObject` al master y copia a la instancia metadatos basicos (`Tipo`, `KeyRegistro`, `ModoVisual`, `AlturaRel`, `OrientacionPared`).

El servicio `set_installation_elevation()` confirma una regla correcta: para Links no se muta el master compartido; se obtiene/crea otro master compatible y se reasigna el `LinkedObject`, conservando Placement.

### Huecos respecto al contrato nuevo

El prototipo A1 ya define en la instancia:

- `ElementUID`;
- `Space`;
- `Host`.

Permanecen fuera de este incremento:

- `Circuit`;
- `Panel`;
- `Control`;
- `System`;
- `Level`.

Tampoco separa aun un nucleo neutral de la dependencia FreeCAD/GUI, y la semantica BIM/IFC no esta formalizada.

Estos son los huecos a resolver. **No hace falta reinventar el manejo 2D/3D, la libreria de masters ni la altura semantica.**

## 15. Matriz de decision historica anterior a A1

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

## 17. Contrato semantico vigente para la instancia A1

La prueba A1 ya permite distinguir entre relaciones **confirmadas** y relaciones
**pendientes de consolidacion**.

### Propiedades comunes confirmadas en A1

- `ElementUID`: `App::PropertyString`, UUID estable de la instancia.
- `Space`: `App::PropertyLink` al `Arch/BIM Space` canonico cuando RoomResolver
  devuelve `RESOLVED`.
- `Host`: `App::PropertyLink` al soporte BIM real cuando la familia lo requiere.
- `Placement`: autoridad geometrica de la instancia.
- `LinkedObject`: master fisico A1 para la ruta `App::Link`.

### Relaciones de proyecto que siguen en consolidacion

- `Circuit`: futuro `App::PropertyLink` cuando exista una identidad de circuito
  suficientemente estable. Mientras tanto se conserva `CircuitoID` y equivalentes.
- `Control`: respetar primero los `PropertyLinkList` existentes del objeto
  Control y los identificadores legacy; definir cardinalidad antes de duplicar
  una relacion directa.
- `Panel`: derivar de Circuit cuando sea posible.
- `System`: derivar de Circuit/tipo/registro cuando la regla sea univoca; crear
  enlace propio solo si existe una entidad System real.

### Datos que deben derivarse antes de duplicarse

- `Level`: derivar de `Space` siempre que sea posible.
- datos de familia/modelo/potencia: derivar de `KeyRegistro`/registro salvo
  override de instancia justificado.

### Compatibilidad legacy

- `Recinto`, `AreaID`, `AreaNombre`, `AreaRecinto`: compatibilidad diagnostica;
  `Space` tiene prioridad cuando existe.
- `MuroReferencia`, `ECR_SourceWall`: compatibilidad de host; `Host` es la
  autoridad A1.
- `AlturaMontaje` puede coexistir durante la transicion, pero la API comun debe
  tener una unica autoridad de elevacion (`AlturaRel`/servicio semantico vigente).

### Extensiones por familia

No deben agregarse al nucleo comun propiedades que solo tienen sentido para una
familia. Ejemplo de apagador:

- `PuertaOrigen`: enlace a Door BIM real;
- `DistanciaJamba`;
- `SentidoApertura`;
- regla de ubicacion;
- relacion `Control` cuando se consolide.

`ElementoOrigen` puede mantenerse como alias legacy si una herramienta actual lo
requiere, pero no debe competir con una propiedad de familia mas especifica.

Regla: **enlazar la autoridad, derivar lo derivable y conservar los textos y
aliases legacy solo durante la transicion**.

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

## 20. Criterio del prototipo semantico (historico; ya superado)

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

## 22. Decision A1 verificada: PhysicalRepresentation + DocumentationRepresentation

El 2026-09-03 se cerro la siguiente decision para el prototipo opt-in:

```text
App::Link (identidad unica)
  |-- LinkedObject -> master PhysicalDocumentationA1
  |                    `-- Shape = model3D fisico
  |-- ElementUID
  |-- Space
  |-- Host
  `-- DocumentationRepresentationName
                       `--> Part::Feature PLAN
                              |-- DocumentationOnly = true
                              |-- RepresentationRole = PLAN
                              `-- Owner -> App::Link
```

El nombre de PLAN en el propietario y el `PropertyLink Owner` en PLAN evitan un
ciclo de dependencias de FreeCAD. PLAN no recibe UID, Space, Host, circuitos ni
otra semantica de identidad. Su ciclo de vida se controla con
`remove_device_with_documentation()` y `cleanup_orphan_documentation()`.

### Alternativas de presentacion evaluadas

| alternativa | resultado |
|---|---|
| A. sustituir el ViewProvider nativo del `App::Link` | descartada para A1; eleva el riesgo de romper la instancia enlazada |
| B. dibujar PLAN solo como escena Coin del ViewProvider | insuficiente; no proporciona un objeto semantico consumible por DXF |
| C. auxiliar PLAN controlado | seleccionada; separa Shape, visibilidad, escala, persistencia y exportacion |

El auxiliar documental no contradice la identidad unica: es una representacion
sin UID cuyo `Owner` es resoluble. La Shape fisica nunca consume `symbol2D`.

### Compatibilidad y masters

`crear_toma_link(..., separate_documentation=True)` activa A1. La omision del
argumento mantiene `LegacyCompound`, exclusivamente para no modificar llamadas
y documentos existentes. Los masters A1 llevan sufijo `_A1Physical`, por lo que
nunca reutilizan accidentalmente un master compuesto legacy. Un cambio de
altura conserva el contrato al relinkear.

### Evidencia minima aceptada

La prueba MCP de un tomacorriente y un apagador verifico en FreeCAD 1.1.3:

- Shapes fisicas con volumen y solidos, y Z correspondiente a 450/1350 mm;
- PLAN independientes en Z=0, sin volumen ni solidos;
- cambio de escala PLAN sin variar las metricas fisicas;
- UIDs unicos, Space nativo, Host muro, Placement estable;
- `App::Link`/master A1 despues de save/reopen;
- Undo/Redo de creacion, visibilidad y altura;
- DXF generado solo desde dos PLAN;
- segunda sincronizacion sin cambios y cero huerfanos.

Esta decision no migra ni autoriza migrar los 48 tomacorrientes o 11 apagadores
de Upala, ni ningun otro objeto productivo.


## 23. Interfaz arquitectonica Facil Arquitectura / CRBIMCore -> ElectricCR

Decision transversal cerrada el 2026-09-03 a nivel de contrato:

```text
FA / BIM                                ElectricCR A1
---------                               -------------
Arch/BIM Space  ----------------------> Space
Wall / soporte BIM -------------------> Host
Door BIM -----------------------------> PuertaOrigen   # familia Switch
Building/Level <--- Space ------------> Level derivado
                ^
                |
        CRBIMCore.RoomResolver
```

### Responsabilidades

Facil Arquitectura:

- detecta y mantiene geometria arquitectonica;
- crea/actualiza Spaces nativos;
- conserva identidad mediante sus UID/ID arquitectonicos;
- mantiene Wall, Door y Window BIM.

CRBIMCore:

- resuelve la identidad espacial sin duplicarla;
- prioriza `NATIVE_SPACE` sobre `LEGACY_AREA`;
- devuelve `AMBIGUOUS`/`NOT_FOUND` sin escoger silenciosamente.

ElectricCR:

- consume `Space` y `Host` mediante enlaces;
- no agrega propiedades ElectricCR al Space;
- no mueve el Space para satisfacer su arbol;
- no convierte Sketches, poligonos o Areas auxiliares en la autoridad de una
  relacion que ya dispone de objeto BIM.

### Consecuencia para apagadores junto a puertas

La regla de colocacion puede usar geometria auxiliar para calcular posicion,
pero el contrato final debe ser conceptualmente:

```text
Apagador
  Host         -> Wall BIM
  PuertaOrigen -> Door BIM
  Space        -> Space BIM resuelto
  Placement    -> posicion calculada junto a la jamba
```

Un `Sketch_Centros_Puertas`, `Rectangle006` u otro auxiliar puede quedar como
trazabilidad legacy, pero no sustituye esas relaciones.

## 24. Matriz nucleo comun frente a extensiones de familia

| Dato | Nucleo comun | Extension de familia / derivado |
|---|---|---|
| ElementUID | SI | - |
| ElementClass | SI | - |
| Family / TypeCode | SI | - |
| Placement | SI | - |
| Space | SI | - |
| Host | SI cuando aplique | - |
| Level | NO por defecto | derivado de Space |
| Circuit | contrato comun futuro | relacion de proyecto |
| Panel | NO por defecto | derivado de Circuit |
| System | contrato comun cuando exista entidad | derivable de circuito/tipo |
| Control | contrato comun cuando aplique | cardinalidad depende de familia |
| PuertaOrigen | NO | Apagador/otros casos dependientes de puerta |
| DistanciaJamba | NO | Apagador |
| SentidoApertura | NO | Apagador/puerta |
| lumenes/fotometria | NO | Luminaria |
| NEMA/polos/amperaje | NO | Tomacorriente |
| FOV/resolucion | NO | Camara |

## 25. Integracion real A1 opt-in verificada

El 2026-09-03 las herramientas existentes de tomacorrientes sobre muros BIM y
apagadores junto a puertas BIM integraron `PhysicalDocumentationA1` mediante un
selector de ejecucion desmarcado y no persistente. No se creo otro generador:
ambas rutas conservan sus algoritmos geometricos y llaman al mismo
`objeto_toma_uno.crear_toma_link`.

Secuencia A1 real:

```text
algoritmo de colocacion existente
  -> crear_toma_link(separate_documentation=True)
  -> recompute fisico
  -> ensure_device_semantics(Host=Wall, Space=RoomResolver)
  -> sync_plan_representation
```

El apagador conserva ademas `PuertaOrigen`, `ElementoOrigen`,
`MuroReferencia`, `AreaRecinto`, reglas de jamba/cara y metadatos legacy. Si la
busqueda encuentra un apagador `LegacyCompound` durante una ejecucion A1, este
se preserva y no se actualiza/migra.

La prueba MCP sobre una copia temporal de Upala creo una sola toma A1 y un solo
apagador A1. Aprobaron Shape fisica, PLAN independiente, UID, Space, Host,
PuertaOrigen, Placement, altura/relink, save/reopen, Undo/Redo, DXF e
invariancia de Volume/BoundBox/Solids frente a sincronizacion PLAN.

La investigacion de `Apagador - Rectangle006` confirmo que `Rectangle006` era
`AreaRecinto`; la puerta real era `Window` y el muro `Wall`. El Label reflejaba
el recinto auxiliar. Su Placement historico difiere del punto de jamba actual,
pero el estado original ya no estaba disponible en el FCStd vigente y no se
aplico una correccion especulativa.

Drive conserva el inventario historico de 48 tomas y 11 apagadores legacy. El
FCStd vigente tenia cero dispositivos al ejecutar la prueba; esta discrepancia
queda documentada. El contrato y la prueba no autorizan migracion masiva ni un
cambio del default productivo.


## Decision de diseno 2026-09-05 21:50 America/Costa_Rica - feedback PLAN persistente

Se descarta `Draft ghostTracker` como mecanismo persistente de seleccion para PLAN en FreeCAD 1.1.3. La prueba real produjo ghosts graficos y Access violation.

Contrato vigente de seleccion:
```text
clic PLAN -> seleccion logica = Owner solamente
feedback persistente PLAN = pendiente; no usar overlay Coin persistente ni preseleccion forzada
```

El PLAN documental debe permanecer fuera del arbol de usuario:
- `ViewObject.ShowInTree=False`;
- no pertenecer a `DocumentObjectGroup` como hermano del Owner;
- `PLAN.Owner` y la expresion de Placement siguen siendo las relaciones internas autoritativas.

La limpieza de pertenencia a grupos se ejecuta dentro de `sync_plan_representation()` y no cambia identidad, Placement, visibilidad ni snaps.
