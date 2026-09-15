## Ajuste 2026-09-05 - multiparentalidad de hosted objects pendiente de proyeccion

La auditoria real de Upala confirma que una misma instancia A1 puede aparecer bajo `Wall` y bajo un grupo electrico porque BIM/Arch proyecta los objetos hospedados cuando `ClaimHosted=True`. Esto es una **multiparentalidad visual**, no duplicacion de identidad.

No se adopta `PropertyLinkHidden` para `Device.Host` como mera correccion de arbol: FreeCAD tambien usa `Wall.InList + Device.Host` para movimiento con host. El contrato conserva `Device.Host -> Wall` normal mientras se compara una solucion de proyeccion que preserve comportamiento.

Candidatos:

```text
A) ClaimHosted=False
   + nativo, sin cambiar relaciones
   + conserva movimiento con host
   - preferencia BIM global

B) referencia indice/proyeccion electrica
   + localizada por disciplina
   + no cambia Host ni arquitectura
   - requiere lifecycle/seleccion de la referencia

C) Host hidden + movimiento A1 propio
   + localizado
   - sustituye comportamiento BIM existente; no preferido
```

PLAN es diferente: es auxiliar documental y puede ocultarse del arbol con `ShowInTree=false` sin perder relacion semantica ni movimiento del dispositivo.

La regla autoritativa sigue siendo: relaciones semanticas = verdad; TreeParents/InList visibles no deben confundirse con identidad.

---

# Contrato semantico del arbol ElectricCR

Estado: fase 2A cerrada / A1 fisico-documental verificado opt-in / sin migracion productiva
Fecha: 2026-09-03
FreeCAD verificado: 1.1.3

## Regla autoritativa

Las relaciones semanticas son la verdad. El arbol del modelo es una vista reproducible de esas relaciones.

Un `Arch/BIM Space` permanece en la jerarquia arquitectonica. La rama electrica puede contener un nodo visual con el nombre del recinto, pero ese nodo no es una segunda identidad arquitectonica y no sustituye al Space.

## Proyeccion visual de iluminacion

La forma historica se conserva como objetivo visual:

```text
electrico/Iluminacion/Circuitos/<Circuito>/Recintos/<Recinto>/Apagadores/<Apagador>/Luminarias
```

No todos los sistemas deben adoptar esta misma forma. Por ejemplo, deteccion puede proyectarse por zonas.

## Auditoria de relaciones existentes

| Relacion | Evidencia actual | Autoridad actual | Pendiente posterior |
|---|---|---|---|
| elemento -> recinto | legacy: `Recinto`, `AreaNombre`, `AreaID`, `ORG_Area`; A1: `App::PropertyLink Space` verificado | A1: `Space` explicito; si falta, `CRBIMCore.RoomResolver`; legacy conserva sus textos durante transicion | integrar A1 de forma opt-in en herramientas reales y crear adaptador no destructivo para legacy |
| elemento -> host | A1: `App::PropertyLink Host` verificado con muro BIM temporal; legacy usa propiedades como `MuroReferencia`/`ECR_SourceWall` | `Host` del dispositivo A1 | normalizar adaptadores por familia sin perder las propiedades legacy |
| apagador -> puerta origen | legacy ya dispone de `PuertaOrigen`/`ElementoOrigen`; A1 requiere relacion de familia con Door BIM real | `PuertaOrigen` cuando la regla de colocacion dependa de la puerta | evitar que Sketch/auxiliares se conviertan en autoridad semantica |
| elemento -> circuito | `CircuitoID`, `Circuito`, `ECR_CircuitoIluminacion` | identificador estable de texto; las herramientas de asignacion ya lo escriben antes de organizar | evaluar `App::PropertyLink Circuit` sin retirar `CircuitoID` de compatibilidad |
| circuito -> tablero | `Tablero` de tipo cadena en grupos de circuito | texto legacy | evaluar `App::PropertyLink Panel` y conservar codigo visible |
| luminaria -> apagador/control | `ControlID`, `ApagadorID`, `ECR_ControlID`; el objeto Control usa `PropertyLinkList Luminarias` y `PropertyLinkList Apagadores` | los LinkList del Control son la relacion mas fuerte existente | definir cardinalidad y enlace directo reversible sin competir con los LinkList existentes |
| elemento -> sistema/disciplina | `Tipo`, `TipoLogico`, `Categoria`, `KeyRegistro` y clasificador | clasificacion por propiedades | normalizar contrato comun sin cambiar masters ni LinkedObject |
| elemento -> Level | RoomResolver puede devolver el Level del Space | derivado de `Space` por defecto | agregar enlace explicito solo si un caso real demuestra que la derivacion no basta |

## Precedencia para consumidores nuevos

1. Relacion nativa o `App::PropertyLink` explicita y valida.
2. Identificador semantico estable de compatibilidad (`CircuitoID`, `ControlID`, etc.).
3. `RoomResolver` para la identidad fisica del recinto.
4. Propiedades de texto legacy.
5. Posicion en el arbol solo como adaptador heredado diagnosticable.

No se debe elegir un recinto ambiguo por menor area ni por cercania. `AMBIGUOUS` y `NOT_FOUND` deben conservarse como estados explicitos.

## Alcance implementado en fase 2A

- `Actualizar_Iluminacion_Completa.FCMacro` enumera recintos mediante `CRBIMCore`.
- Space tiene prioridad sobre Area superpuesta.
- Areas heredadas conservan `Rows`, `Columns` y las propiedades de calculo existentes.
- Spaces se leen sin agregarles propiedades de iluminacion.
- `DatosRecintos` conserva sus 12 columnas y la tabla legacy conserva su consumidor actual.
- No se crean luminarias para calcular y no se modifica Placement, Shape, master o `LinkedObject`.

## No migrado

Los proyectos reales no han sido migrados. La fase A1 ya creo y verifico en documento temporal un tomacorriente y un apagador nuevos con `ElementUID`, `Space`, `Host`, master fisico separado y PLAN documental, pero no modifica dispositivos existentes.

La reconstruccion del arbol en proyectos reales, la migracion de luminarias/tomacorrientes/apagadores legacy y la sustitucion del default productivo siguen fuera de alcance.

## Contrato confirmado por el prototipo de luminaria

En documento temporal FreeCAD 1.1.3 se confirmo:

- instancia fisica `App::Link`: autoridad de `ElementUID`, `Space`,
  `CircuitoID`, master y Placement;
- Control: autoridad por sus `PropertyLinkList Luminarias/Apagadores`;
- nodo Room de proyeccion: enlaza el Space mediante `ECR_SourceSpace`, pero no
  contiene ni duplica el Space;
- nodo Switch de proyeccion: enlaza el Control mediante `ECR_SourceControl`;
- hoja visual de Luminarias: contiene un `App::Link` indice marcado
  `ECR_ProjectionReference` y `ECR_SourceElementUID`, no una segunda identidad;
- grupos de proyeccion: `ECR_ProjectionRole` y `ECR_ProjectionKey` estables;
- segunda aplicacion: cero cambios materiales.

La referencia indice es necesaria para conservar la pertenencia manual de la
instancia, ya que `App::DocumentObjectGroup` no ofrece pertenencia visual
multiple para este flujo. El helper permanece `dry_run=True` por defecto y no
se ha ejecutado sobre modelos productivos.


## Contrato A1 fisico, documental y semantico

Verificado el 2026-09-03 en FreeCAD 1.1.3:

```text
App::Link dispositivo A1
  |-- ElementUID
  |-- Space -> Arch/BIM Space
  |-- Host  -> soporte BIM
  |-- Placement
  |-- LinkedObject -> master fisico A1
  |                    `-- Shape = solo 3D fisico
  `-- PLAN DocumentationOnly
       `-- Owner -> dispositivo A1
```

`PLAN` no es una segunda identidad del dispositivo. No recibe `ElementUID`,
`Space`, `Host`, `Circuit` ni otras relaciones funcionales. La modificacion de
su visibilidad o escala documental no puede modificar Volume, BoundBox o Solids
del modelo fisico.

El arbol puede mostrar el PLAN o referencias de indice cuando convenga, pero ni
PLAN ni esas referencias son autoridad funcional.

## Interfaz con Facil Arquitectura y CRBIMCore

La arquitectura transversal queda:

```text
Facil Arquitectura / BIM
  Space -----> Device.Space
  Wall  -----> Device.Host
  Door  -----> Switch.PuertaOrigen     # cuando aplique
  Level <----- derivado desde Space
          ^
          |
CRBIMCore.RoomResolver
```

Reglas:

1. FA conserva la autoria de Space, Wall, Door y Window.
2. ElectricCR consume esos objetos mediante enlaces; no crea duplicados para
   satisfacer su arbol.
3. Un Sketch de centros, poligono auxiliar o Area legacy puede participar en
   calculo/fallback, pero no sustituye a Space/Host/PuertaOrigen cuando existe
   una identidad BIM valida.
4. `AMBIGUOUS` y `NOT_FOUND` no escriben relaciones por aproximacion.
5. `Level` se deriva del Space antes de duplicarse como propiedad independiente.

## Proyeccion transversal del arbol

La jerarquia arquitectonica real permanece:

```text
Site
  `-- Building
       `-- Level
            |-- Wall / Door / Window
            `-- Space
```

Las disciplinas pueden construir vistas como:

```text
Electromecanico
  |-- Electricidad
  |-- HVAC
  `-- otros sistemas
```

o ramas por circuito/recinto/control, pero siempre mediante claves semanticas y
referencias reproducibles. Mover una referencia de proyeccion nunca modifica
`Space`, `Host`, `Circuit` o `Control` del dispositivo fuente.

## Estado de Upala como baseline legacy

El documento `1416 Levantamiento 250424 Compu D` se conserva como referencia
real sin migracion. La auditoria identifico 48 tomacorrientes y 11 apagadores
`App::Link` basados en masters `LegacyCompound`. Los apagadores ya tienen
relaciones utiles con puerta y muro, pero su recinto se apoya en propiedades y
auxiliares legacy. Estos objetos no deben reorganizarse ni convertirse hasta
que la integracion A1 opt-in en las herramientas reales haya sido probada.


## Ajuste 2026-09-05 21:50 America/Costa_Rica - PLAN no es nodo organizativo

Para A1, el PLAN es representacion documental auxiliar y no debe aparecer como hermano del dispositivo dentro de `Apagadores BIM` ni de otros grupos de usuario.

Regla:
```text
Apagadores BIM
└─ Device/Owner App::Link

PLAN Part::Feature
- propiedad del Owner
- oculto del arbol
- sin pertenencia a grupos de usuario
```

La multiparentalidad del Owner bajo `Wall` y `Apagadores BIM` sigue siendo un problema separado del PLAN y permanece sin modificar hasta definir la proyeccion electrica final.
