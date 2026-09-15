# ElectricCR - Diseno del adaptador IFC para A1

**Proposito:** definir la frontera entre el elemento electrico A1 y la interoperabilidad IFC sin crear una segunda autoridad de datos.

**Estado:** adaptador IFC aun exploratorio; Demo ElectricCR A1 v0.1 implementada como banco de pruebas previo.

**FreeCAD objetivo:** 1.1.3.

**Version:** 0.2.0.

**Fecha y hora:** 2026-09-09 22:09 -0600 America/Costa_Rica.

## 1. Punto de partida

A1 esta aprobado para continuar y conserva una unica identidad funcional en `Device/Owner = App::Link`, `Placement` autoritativo, master fisico compartido y representacion PLAN documental. El experimento NativeIFC real ya demostro en FreeCAD 1.1.3 que las clases electricas basicas, atributos IFC, Placement y Psets pueden persistir, pero no demostro equivalencia con `App::Link + master`.

## 2. Decision provisional

No sustituir A1 ni mantener un espejo NativeIFC vivo por cada elemento durante la edicion normal. Reutilizar NativeIFC/IfcOpenShell como infraestructura de interoperabilidad mediante un adaptador explicito.

```text
A1 Owner
  |-- ElementUID
  |-- Placement
  |-- LinkedObject/master fisico
  |-- Space / Host / relaciones
  `-- PLAN documental
          |
          v
    Adaptador IFC
          |-- GlobalId
          |-- IfcClass / PredefinedType
          |-- ObjectPlacement
          |-- Representation
          |-- Psets
          |-- Type
          `-- Spatial containment / Systems
```

## 3. Autoridad de datos

Durante el flujo ElectricCR normal:

- identidad operativa: `ElementUID`;
- posicion/orientacion: `Owner.Placement`;
- geometria fisica: master enlazado por `LinkedObject`;
- recinto: `Owner.Space`;
- documentacion: PLAN;
- IFC: proyeccion derivada, no segunda fuente editable.

## 4. Identidad IFC

Primera estrategia a probar: generar `IfcGlobalId` de forma determinista a partir del UUID `ElementUID`. El objetivo es conservar una correspondencia 1:1 estable entre el elemento ElectricCR y su producto IFC sin almacenar dos identificadores independientes cuando no sea necesario.

## 5. Clase y esquema

La clase debe resolverse en una capa dependiente del esquema. Ejemplos iniciales:

- tomacorriente: `IfcOutlet`;
- apagador: `IfcSwitchingDevice`;
- luminaria: `IfcLightFixture`;
- sensor de humo: candidato `IfcSensor`;
- tablero IFC4: `IfcElectricDistributionBoard`;
- tablero IFC4X3: `IfcDistributionBoard`.

El `registry_electric.json` es la fuente natural de familia, pero requiere depuracion semantica antes de convertirse en tabla IFC definitiva. No modificarlo por esta fase.

## 6. Geometria

Primera version del adaptador: reutilizar directamente la Shape fisica A1 y el exportador geometrico existente de FreeCAD/NativeIFC. No reconstruir la geometria ni separar de inmediato mapas de representacion.

El master A1 actual no se considera automaticamente un `IfcTypeProduct`, porque su firma incorpora propiedades de ocurrencia como altura y orientacion. La optimizacion mediante `IfcRepresentationMap` queda para una fase posterior, despues de separar familia/tipo de ocurrencia y medir rendimiento.

## 7. Placement

`Owner.Placement` es la unica autoridad. El adaptador debe producir `IfcObjectPlacement` desde esa propiedad. No mantener un Placement NativeIFC editable en paralelo durante la edicion ElectricCR.

## 8. Psets

Preferir Psets estandar IFC cuando exista equivalencia. Crear propiedades ElectricCR especificas solo para informacion sin correspondencia adecuada. Las cantidades/Qto deben tratarse aparte porque el soporte NativeIFC revisado conserva limites/TODO.

## 9. Space y containment

El exportador debe trabajar sobre el mismo `ifcopenshell.file` que contiene la arquitectura. Se mantiene una tabla temporal de entidades creadas y se resuelve `Owner.Space` contra el `IfcSpace` exacto de ese mismo archivo. No buscar por etiqueta si existe identidad directa y no duplicar el recinto.

## 10. PLAN

PLAN no es otro producto electrico IFC. En la primera version se excluye del producto fisico. Una fase posterior puede estudiar `IfcAnnotation` en contexto `Plan` si se necesita intercambio documental 2D, manteniendo siempre `Owner` como identidad electrica.

## 11. Conversion NativeIFC directa

No usar `NativeIFC.aggregate()` sobre elementos productivos como ruta de integracion. La implementacion nativa puede crear un objeto IFC nuevo y eliminar el objeto FreeCAD original dependiendo de `KeepAggregated`. Cualquier experimento de conversion se limita a documentos desechables.

## 12. Macro/demo de pruebas propuesta

Se propone una herramienta de pruebas equivalente en filosofia a la **Demo Casa de 2 Plantas**: debe crear su propio escenario desde cero, ser reproducible y servir tanto para demostracion como para regresion.

Escenario minimo propuesto:

```text
Proyecto demo ElectricCR
  Nivel / Space A: Oficina
  Nivel / Space B: Bodega o pasillo

  2 tomacorrientes A1
  2 apagadores A1
  2 luminarias A1
  1 sensor de humo A1
  1 tablero de prueba

  relaciones simples:
    Space
    circuito de iluminacion
    circuito de tomas
    control apagador -> luminaria
```

La demo debe poder auditar, como minimo:

- `ElementUID` unico y persistente;
- correspondencia Owner/PLAN 1:1;
- `Placement` y movimientos;
- save/reopen y Undo/Redo;
- Space/containment;
- clases y PredefinedType IFC esperados;
- GlobalId estable;
- Psets previstos;
- exportacion IFC y reapertura;
- ausencia de sustitucion, borrado o mutacion de Owners A1;
- salida 2D PLAN comprensible.

La macro debe ser pequena y actuar como orquestador. La logica de creacion/auditoria/exportacion debe vivir en modulos reutilizables, no dentro de un `.FCMacro` monolitico.

## 13. Estado y siguiente decision

Investigacion/documentacion: COMPLETADA para esta fase.

Implementacion de adaptador IFC: NO AUTORIZADA.

Implementacion de Demo/Macro de pruebas: **AUTORIZADA E IMPLEMENTADA EN DRIVE v0.1; PRUEBA REAL FREECAD 1.1.3 PENDIENTE**.

Marco autorizo la demo y se decidio limitar v0.1 a A1 + Space/Host. El exportador IFC permanece fuera hasta que el banco de pruebas apruebe en FreeCAD real.
