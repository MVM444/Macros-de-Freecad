# Extracción HVAC desde un DWG/DXF importado

Fecha: 2026-07-31
Versión: 1.0

## Objetivo

Convertir los bloques y textos HVAC de una referencia CAD ya importada en un inventario trazable dentro de MEP Workbench CR, sin modificar ni reemplazar la geometría CAD de origen.

## Uso

1. Importe el DWG/DXF con **Facil Arquitectura > Importar referencia CAD** y confirme la unidad real.
2. Guarde el documento importado cuando corresponda.
3. Active **MEP Workbench CR**.
4. Ejecute **Extraer inventario HVAC desde CAD**.
5. Revise el grupo `HVAC - Inventario extraido de CAD` y la hoja `HVAC - Inventario CAD`.

También puede ejecutar la macro `MEPWorkbenchCR_Extraer_HVAC_CAD.FCMacro`.

## Datos extraídos

- Tipo de unidad: pared, cassette, piso-cielo o extractor de cielo.
- Modelo MEP normalizado, por ejemplo `Pared_12000` o `Cassette_36000`.
- Capacidad en BTU/h o caudal en CFM.
- Coordenadas y rotación del bloque original.
- Enlace al bloque y a la etiqueta técnica CAD de origen.
- Recinto candidato, alternativas, distancia, confianza y estado de revisión.
- Marca de objetos aislados fuera del conjunto principal de la planta.

Los objetos fuera de planta reciben identificadores `EV-X..` o `EX-X..`, separados de la numeración válida.

## Criterio de recintos

El texto más cercano no se convierte automáticamente en un `HVACSpace`. El extractor registra una asociación **Probable** o **Revisar**, porque el punto de inserción de una etiqueta no demuestra por sí solo que el equipo está dentro de ese recinto. Los pares de unidades de pared colocadas espalda con espalda siempre quedan para revisión.

Cuando existan espacios HVAC geométricos, la asociación definitiva debe confirmarse con la herramienta **Asignar Evaporadora a Recinto** o mediante contención espacial.

## Repetición segura

La extracción es idempotente: vuelve a usar los registros asociados a cada bloque CAD y actualiza la hoja. Solo elimina registros obsoletos que hayan sido generados por `MEP_HVAC_ExtractCAD`. Toda la operación usa una transacción de FreeCAD y puede deshacerse con `Ctrl+Z`.

El comando no guarda el archivo FCStd automáticamente.

## Adaptación a otros dibujos

Se prefieren bloques con nombres descriptivos (`Evaporadora Pared`, `Cassette`, `Piso-Cielo`, `Fan Ceiling` o `Extractor`). Los bloques anónimos del plano de Puriscal tienen reglas conocidas en `MEP/hvac/hvac_cad_extract.py`:

- `BLOCK__U160` → cassette.
- `BLOCK__U157` → piso-cielo.

Si otro proyecto usa nombres anónimos distintos, agréguelos a `ANONYMOUS_BLOCK_TYPE_HINTS` después de verificar visualmente su significado. No se debe inferir una asociación ambigua solo por el nombre de bloque.
