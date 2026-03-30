# Archivo: SPEC_FREEZE_V0_1.md
**Proposito:** Congelar reglas funcionales y formulas oficiales del MVP HVAC para eliminar contradicciones antes de seguir desarrollo.  
**Fecha y hora de version:** 2026-03-30 09:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Especificacion Congelada v0.1 (HVAC MVP)

## 1) Alcance congelado

- Esta version cubre solo HVAC.
- El calculo base pertenece al recinto (`HVACSpace`).
- La evaporadora responde a la carga del recinto.
- La condensadora valida el sistema por suma de evaporadoras.
- Las rutas conectan puertos compatibles, no geometria suelta.
- La etiqueta depende del recinto y muestra carga y cobertura.

## 2) Variables climaticas oficiales

- `Location` (string): default `CR`.
- `Altitude` (m): default `0.0`.
- `OutdoorTemp` (C): default `30.0`.
- `IndoorTemp` (C): default `22.0`.
- `Humidity` (%): default `100.0` (caso conservador).
- `ClimateFactor` (BTU/h*m2): calculado automaticamente.
- `RegionalBonus` (BTU/h*m2): bono por microclima de la `Location`.
- `ClimateOffset` (BTU/h*m2): ajuste manual adicional para calibracion local.

Reglas:

- `Humidity` se limita entre `20` y `100`.
- `delta_t = max(2.0, OutdoorTemp - IndoorTemp)`.
- Mayor temperatura exterior aumenta factor.
- Mayor humedad aumenta factor.
- Mayor altitud reduce factor.

## 3) Formula oficial de ClimateFactor (v0.1)

Unidad principal: `BTU/h*m2`.

```text
altitude_penalty = min(140.0, Altitude * 0.035)
factor = 260.0 + (delta_t * 11.0) + (Humidity * 0.75) - altitude_penalty + RegionalBonus + ClimateOffset
ClimateFactor = max(220.0, factor)
```

Notas:

- Esta es una formula empirica de pre-dimensionamiento (no calculo termico completo).
- `RegionalBonus` depende de `Location` (calibracion regional CR).
- `ClimateOffset` permite ajuste manual directo en BTU/h*m2.

## 4) Regla oficial de carga por recinto

Objeto: `HVACSpace`.

### Modo Rapido

```text
AreaLoad = Area * ClimateFactor
PeopleLoad = Occupancy * 600
Total = AreaLoad + PeopleLoad + EquipmentLoad
CoolingLoadBTU = Total
```

### Modo Preciso (inicial)

```text
AreaLoad = Area * ClimateFactor
PeopleLoad = Occupancy * 650
Base = AreaLoad + PeopleLoad + EquipmentLoad
HeightFactor = clamp(Height / 2.6, 0.85, 1.40)
CoolingLoadBTU = Base * HeightFactor
```

Reglas:

- Si hay `BaseSpace`, el area se detecta automaticamente cuando es posible.
- `EquipmentLoad` es carga adicional manual (BTU/h).
- La altura es configurable por recinto y afecta solo modo `Preciso`.

## 5) Regla oficial de cobertura

### Cobertura de evaporadora respecto al recinto

```text
CoveragePct = CapacityBTU / CoolingLoadBTU * 100
```

Interpretacion:

- `< 90%`: insuficiente.
- `90% - 110%`: rango objetivo de pre-dimensionamiento.
- `> 110%`: sobredimensionado.

### Cobertura de condensadora respecto al sistema

```text
ConnectedLoadBTU = suma(CapacityBTU de evaporadoras conectadas)
CoveragePct = CondenserCapacityBTU / ConnectedLoadBTU * 100
```

Reglas:

- `CoveragePct < 100%` en condensadora indica deficit del sistema.
- `CoveragePct >= 100%` indica capacidad suficiente.

## 6) Contratos funcionales por objeto

### HVACProject

- Mantiene clima global y `ClimateFactor`.
- Recalcula al cambiar: `Altitude`, `OutdoorTemp`, `Humidity`, `IndoorTemp`.

### HVACSpace

- Propiedades clave: `Area`, `Height`, `Occupancy`, `EquipmentLoad`, `Mode`, `CoolingLoadBTU`.
- El recinto es la fuente de verdad de la carga.

### HVACEquipment (evaporadora)

- Propiedades clave: `Type`, `CapacityBTU`, `Space`, `Height`, `CoveragePct`, `AutoDetectSpace`.
- Detecta recinto por:
  1. Seleccion actual.
  2. Posicion dentro del `BaseSpace`.
  3. Recinto unico en documento.

### HVACCondenser

- Propiedades clave: `CapacityBTU`, `ConnectedUnits`, `ConnectedLoadBTU`, `CoveragePct`, `AutoCollect`.
- Si `ConnectedUnits` esta vacio y `AutoCollect=True`, toma todas las evaporadoras del documento.

### HVACPort

- Tipos oficiales: `Gas`, `Liquid`, `Electric`, `Drain`.
- Conexion valida solo si `Type == Type` y no es el mismo puerto.
- Relacion de conexion se guarda por nombre (`ConnectedToName`) para evitar ciclos DAG por links directos.

### HVACRoute

- Basado en `Draft Wire`.
- Propiedades clave: `RouteType`, `StartPort`, `EndPort`, `Length`, `Level`, `AutoFromPorts`, `RelatedEquipment`.
- `RouteType` se deriva de puerto:
  - `Electric` -> `Electric`
  - `Drain` -> `Drain`
  - otro -> `Refrigerant`

### HVACLabel

- Ligada al recinto (`Space`).
- Debe mostrar exactamente:
  1. Nombre recinto
  2. Carga BTU/h
  3. `EQ: capacidad (porcentaje)`

## 7) Reglas de estabilidad (anti-regresion)

- No crear `PropertyLink` bidireccionales entre objetos que generen ciclos DAG.
- Evitar escrituras redundantes en `onChanged` para no disparar recursiones.
- Todo `FeaturePython` con guardas de reentrada (`_busy`) en cambios.
- Los puertos deben permanecer invisibles por defecto (solo logica).

## 8) Reglas de UI y experiencia

- Comandos minimos activos en toolbar:
  - Crear Proyecto HVAC
  - Crear Recinto HVAC
  - Calcular HVAC
  - Validar HVAC
  - Insertar Evaporadora
  - Insertar Condensadora
  - Asignar a Condensadora
  - Crear Ruta HVAC
  - Mostrar/Ocultar Etiquetas
  - Reload Workbench
- Cada comando debe tener icono propio.
- El sistema debe soportar idioma `es` y `en` (base i18n inicial).

## 9) Fuera de alcance de v0.1

- Balance psicrometrico avanzado.
- Bibliotecas comerciales completas de fabricantes.
- Calculo hidraulico detallado de drenajes y tuberias.
- Coordinacion automatica multi-disciplina completa (MEP total).

## 10) Criterio de continuidad

- Este archivo es la referencia operativa para desarrollo inmediato.
- Si aparece conflicto entre conversacion historica y codigo nuevo:
  - prevalece esta especificacion hasta emitir `SPEC_FREEZE_V0_2`.
