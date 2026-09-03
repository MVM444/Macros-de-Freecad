# Contrato semantico del arbol ElectricCR

Estado: fase 2A cerrada y prototipo de luminaria validado
Fecha: 2026-09-01
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
| elemento -> recinto | cadenas `Recinto`, `AreaNombre`, `AreaID`, `ORG_Area` y contexto de grupos | en calculo de iluminacion, `CRBIMCore.RoomResolver`; en organizadores legacy, propiedad explicita antes que geometria/arbol | definir `App::PropertyLink Space` para objetos electromecanicos futuros y adaptador no destructivo para legacy |
| elemento -> circuito | `CircuitoID`, `Circuito`, `ECR_CircuitoIluminacion` | identificador estable de texto; las herramientas de asignacion ya lo escriben antes de organizar | evaluar `App::PropertyLink Circuit` sin retirar `CircuitoID` de compatibilidad |
| circuito -> tablero | `Tablero` de tipo cadena en grupos de circuito | texto legacy | evaluar `App::PropertyLink Panel` y conservar codigo visible |
| luminaria -> apagador/control | `ControlID`, `ApagadorID`, `ECR_ControlID`; el objeto Control usa `PropertyLinkList Luminarias` y `PropertyLinkList Apagadores` | los LinkList del Control son la relacion mas fuerte existente | definir cardinalidad y enlace directo reversible solo en una fase de objeto electromecanico |
| elemento -> sistema/disciplina | `Tipo`, `TipoLogico`, `Categoria`, `KeyRegistro` y clasificador | clasificacion por propiedades | normalizar contrato comun sin cambiar masters ni LinkedObject |
| elemento -> Level | no uniforme; RoomResolver devuelve el Level del Space | contexto del Space resuelto para calculo | decidir enlace o derivacion por Space en fase posterior |

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

Esta fase no reconstruye el arbol de proyectos reales, no agrega enlaces a dispositivos existentes y no redefine luminarias, tomacorrientes ni apagadores. El rediseño del objeto electromecanico y la reconstruccion idempotente del arbol son una fase posterior separada.

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
