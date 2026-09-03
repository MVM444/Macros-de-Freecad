# Memoria FreeCAD - luminaria semantica y arbol idempotente

Fecha: 2026-09-01
FreeCAD: 1.1.3 revision 20260725
Proyecto: ElectricCR

## Patron validado

Una instancia ElectricCR `App::Link` puede conservar master, Placement y
representacion 2D/3D mientras recibe `ElementUID` y un `PropertyLink Space`.
Para resolver el recinto de una instancia se debe usar su Placement global; no
se debe desenvolver primero el Link hacia el master, porque el master vive en
coordenadas de biblioteca.

RoomResolver solo escribe Space cuando devuelve `RESOLVED` hacia un Space
nativo. `AMBIGUOUS`, `NOT_FOUND` y Areas legacy no producen enlace.

## Arbol como proyeccion

Los `App::DocumentObjectGroup` remueven la pertenencia visual anterior al
agregar el mismo objeto a otra rama. Para preservar la ubicacion manual del
elemento, la rama reproducible usa un `App::Link` indice marcado como referencia
de proyeccion, enlazado a la instancia fisica por `LinkedObject` y
`ECR_SourceElementUID`.

Los contenedores se identifican por rol y clave estable; el Space y el Control
se enlazan desde los nodos visuales. `dry_run=True` es el valor por defecto. Una
segunda aplicacion sin cambios debe devolver cero modificaciones.

## Masters

`TomaUnoProxy.execute()` hacia visible el ViewProvider durante recompute. Los
masters se marcan `EsPrototipo=True` y el ViewProvider respeta esa marca para
mantenerlos ocultos despues de recompute y reapertura.

## Comparacion Equipment

`Arch.makeEquipment()` en 1.1.3 crea `Part::FeaturePython`, usa `Base`, ofrece
`GlobalId`/`IfcProperties` y acepta `IfcType=Light Fixture`; el default observado
fue `Furniture`. Para el prototipo requirio una copia/Base controlada, mientras
el Link comparte master. No existe evidencia para reemplazar masivamente la
identidad App::Link.

## Prueba

`ElectricCR/tests/freecad_semantic_luminaire_prototype_smoke.py` crea solo un
documento temporal, valida UID/Space, casos ambiguo/exterior, altura, arbol,
Undo/Redo, DXF, Equipment y guardar/reabrir, y elimina el FCStd temporal.
