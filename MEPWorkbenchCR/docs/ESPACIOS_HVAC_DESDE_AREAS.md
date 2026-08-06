# Espacios HVAC desde rectangulos, poligonos y analisis de areas

Fecha: 2026-08-01

## Objetivo

El comando estable `MEP_HVAC_CreateSpace` permite crear espacios HVAC a partir de:

- rectangulos Draft cerrados;
- poligonos o wires cerrados en el plano XY;
- objetos generados por el analisis de areas de FacilArquitecturaWB;
- grupos seleccionados que contengan varias geometrías de area validas.

El comando procesa solamente la seleccion explicita. No busca ni transforma automaticamente otros grupos del documento.

## Modos de creacion

### Copia HVAC vinculada

Es el modo predeterminado y conservador.

- conserva el objeto fuente;
- mantiene `BaseSpace` como `PropertyLink` hacia la fuente;
- actualiza el mismo espacio si se ejecuta nuevamente sobre la misma fuente;
- conserva sin modificar el rectangulo o poligono original y su estado de visibilidad;
- sincroniza area y geometria cuando se vuelve a procesar la fuente.

El valor interno de `SourceMode` es `LinkedCopy`.

### Conversion completa

- copia la geometria al objeto `HVACSpace`;
- registra `SourceObjectName` y `SourceObjectLabel` para trazabilidad;
- elimina el objeto fuente;
- deja `BaseSpace` vacio porque el espacio conserva una geometria autonoma;
- mantiene calculo, etiquetas, deteccion de recinto y guardado/reapertura.

El valor interno de `SourceMode` es `Converted`.

La conversion se ejecuta dentro de una transaccion de FreeCAD y puede deshacerse. Si el objeto fuente tiene dependencias externas, el comando no lo elimina y muestra cuales objetos lo utilizan.

## Espacios superpuestos

La superposicion es valida por diseño. No se elimina un espacio porque este contenido total o parcialmente dentro de otro. Esto permite, por ejemplo:

- analizar un salon irregular completo;
- analizar simultaneamente una plataforma o zona interior;
- comparar escenarios de carga sin alterar el contorno general.

Cada espacio tiene `AllowOverlap=True`. La limpieza heredada elimina solamente wrappers duplicados de una misma fuente o enlaces HVAC anidados invalidos; no compara contencion geometrica.

Cuando un equipo se inserta dentro de varios espacios superpuestos, la deteccion automatica prioriza el espacio de menor area, por ser la region mas especifica. La asignacion puede cambiarse manualmente.

## Flujo de uso

1. Dibujar o seleccionar uno o varios rectangulos/poligonos cerrados, o seleccionar su grupo de analisis de areas.
2. Ejecutar `Crear Espacios HVAC desde Areas`.
3. Elegir `Crear copia HVAC vinculada` o `Convertir completamente a Espacio HVAC`.
4. Confirmar la eliminacion de fuentes si se eligio conversion.
5. Revisar los objetos resultantes en `HVAC Air and Ventilation/Espacios`.
6. Ejecutar `Calcular HVAC` y completar ocupacion, altura y cargas internas segun corresponda.

## API para macros

El flujo sin dialogo permanece disponible para automatizaciones:

```python
from MEPWorkbenchCR.MEP.hvac import hvac_space

spaces = hvac_space.create_spaces_from_objects(
    objetos_fuente,
    doc=FreeCAD.ActiveDocument,
    source_mode=hvac_space.SOURCE_MODE_COPY,
)
```

Para conversion, usar `SOURCE_MODE_CONVERT`. La API anterior `create_spaces_from_selection(doc)` se conserva y utiliza el modo de copia vinculada para mantener compatibilidad.

## Validacion implementada

La prueba `tests/test_hvac_space_copy_convert.py` comprueba:

- copia conservando fuentes;
- idempotencia al repetir el comando;
- dos espacios geometricamente superpuestos;
- prioridad del espacio menor en una interseccion;
- conversion con eliminacion del original;
- proteccion ante dependencias externas;
- persistencia despues de guardar, cerrar y reabrir un FCStd temporal;
- conservacion de area, posicion de etiqueta y deteccion espacial sin `BaseSpace`.
