# Archivo: REGLAS_HVAC.md
**Proposito:** Establecer reglas funcionales y de calculo HVAC para asegurar consistencia tecnica del proyecto.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Reglas HVAC

## Principios de sistema

- El calculo pertenece al recinto.
- El equipo responde al calculo del recinto.
- La condensadora valida el sistema completo.
- Las rutas conectan puertos y representan servicio tecnico.
- El sistema HVAC se considera valido cuando carga, capacidad y conexiones son coherentes.

## Variables climaticas del proyecto

- `Location`: referencia geografica del proyecto.
- `Altitude`: altitud del sitio en metros.
- `OutdoorTemp`: temperatura exterior de diseno.
- `Humidity`: humedad relativa del ambiente exterior.
- `IndoorTemp`: temperatura interior objetivo, default 22 C.
- `ClimateFactor`: factor de carga de referencia en BTU/h por m2.

## Reglas de factor automatico y manual

- El factor automatico se calcula desde variables climaticas del proyecto.
- La altitud debe reducir el factor climatico, no aumentarlo.
- El factor manual debe poder sobrescribir el automatico para casos de ingenieria especifica.
- Toda sobreescritura manual debe quedar identificada en propiedades del proyecto.

## Reglas de recintos y geometria base

- El recinto HVAC debe crearse desde geometria base real (poligono/cara), no desde objetos sin area.
- Se permite trabajar por seleccion directa o por grupo `Areas/Áreas/Recintos`.
- El area del recinto debe venir de la geometria del poligono cuando exista.
- Si la geometria no entrega area directa, se permite fallback por caja envolvente como ultima opcion.

## Reglas de calculo rapido

- Uso: estimacion preliminar y decisiones tempranas.
- Base: area del recinto por factor climatico.
- Ajustes minimos: ocupacion y cargas de equipos internos.
- Resultado principal: carga en BTU/h.
- Resultado secundario: conversion de referencia a W/m2 cuando se requiera reporte.

## Reglas de calculo preciso

- Uso: refinamiento previo a seleccion definitiva de equipos.
- Incluye: area, altura efectiva, ocupacion, carga de equipos y condicion climatica.
- Debe ser mas conservador que calculo rapido cuando existan dudas de carga interna.
- Debe mantener trazabilidad de los parametros usados.

## Reglas de cobertura

- Formula base: `cobertura = capacidad_equipo / carga_requerida * 100`.
- Cobertura menor a 100%: sistema insuficiente.
- Cobertura alrededor de 100%: objetivo de diseno.
- Cobertura muy superior: posible sobredimensionamiento y alerta tecnica.

## Reglas de evaporadoras

- Son equipos interiores 3D colocados por el usuario.
- Deben asociarse a un recinto de forma automatica o manual.
- Deben exponer puertos de servicio definidos.
- Su capacidad individual contribuye al calculo de cobertura del recinto.

## Reglas de condensadoras

- Son equipos 3D independientes del recinto.
- Deben aceptar una o varias evaporadoras asignadas.
- Deben consolidar capacidad conectada y compararla con demanda total.
- Deben reportar porcentaje de cobertura del conjunto conectado.

## Reglas de rutas HVAC

- Tipos de ruta: refrigerante, electrica, condensados.
- Las rutas se definen por conexion entre puertos compatibles.
- No se admiten rutas tecnicas sin origen y destino validos.
- Longitud y nivel deben ser propiedades auditables.
- Altura de rutas debe poder configurarse por proyecto.

## Reglas de etiquetas HVAC

- Deben mostrar: nombre del recinto, carga BTU/h, equipo seleccionado y cobertura.
- La etiqueta depende del recinto como entidad principal.
- Debe actualizarse al cambiar carga, equipo o cobertura.
- Debe ser legible en vista de trabajo y util para revision tecnica.
