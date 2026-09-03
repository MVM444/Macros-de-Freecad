# MEPWorkbenchCR - Sanitario Esparza

**Proposito:** Especificacion, trazabilidad y estado del nucleo sanitario para tanque septico, FAFA y drenaje.
**Version:** 0.5.0
**Fecha:** 2026-08-26
**FreeCAD objetivo:** 1.1.3
**Estado:** NUCLEO v0.5.0 IMPLEMENTADO / 22 PRUEBAS PREVIAS APROBADAS + NUCLEO ESPACIAL VERIFICADO AISLADAMENTE / VALIDACION FUNCIONAL FREECAD PENDIENTE

## Alcance

```text
Tanque septico -> FAFA -> caja de distribucion -> campo de infiltracion
```

La caja de distribucion no se modela aun como objeto definitivo. El adaptador FreeCAD actual es solo una previsualizacion experimental y usa `dry_run=True` por defecto.

## Modulos

- `MEP/sanitary/models.py`: contrato JSON-compatible de resultados y mensajes.
- `MEP/sanitary/septic.py`: volumen/TRH y validaciones del tanque rectangular; referencias comerciales preliminares.
- `MEP/sanitary/fafa.py`: TRH, porosidad, area requerida, velocidad ascensional y COV opcional; referencias comerciales preliminares.
- `MEP/sanitary/infiltration.py`: prueba de campo de 8 intervalos, T, Tabla 2 T->Vp, area, Fp, Pe, longitud y separaciones.
- `MEP/sanitary/system.py`: orquestador y `geometry_spec` neutral.
- `MEP/sanitary/layout.py`: acomodo preliminar de zanjas en un rectangulo disponible.
- `MEP/sanitary/freecad_adapter.py`: previsualizacion 3D experimental sin `FreeCADGui` ni Qt.
- `MEP/sanitary/freecad_objects.py`: proxies `Part::FeaturePython` experimentales para tanque, FAFA y zanja.
- `MEP/sanitary/documentation.py`: planta/seccion 2D neutral y salida SVG.
- `MEP/sanitary/case.py`: validacion de entradas antes del calculo.
- `MEP/sanitary/boundary.py`: contrato `Boundary2D` neutral, area, perimetro, centroide, bounding box, contencion e intersecciones.
- `MEP/sanitary/spatial.py`: validacion espacial de limite de propiedad, huella del edificio, area de tanques y area de drenaje.
- `MEP/sanitary/examples/esparza_input_template.json`: plantilla sin valores inventados.

## Tanque septico

Criterios codificados inicialmente:

- volumen util minimo 1.20 m3;
- profundidad liquida 1.00-2.80 m;
- borde libre minimo 0.30 m;
- ancho interior minimo 0.70 m;
- relacion largo/ancho 3:1 a 4:1;
- TRH minimo predeterminado 1 dia.
- diametro minimo de entrada/salida 0.10 m;
- diferencia minima de elevacion entrada-salida 0.075 m;
- sumergencia minima de entrada 0.15 m;
- sumergencia de salida >= max(H/3, 0.40 m);
- abertura de inspeccion minima 0.60 m;
- recubrimiento minimo de terreno 0.15 m.

El limite de 5.0 m3 se reporta como advertencia de aplicabilidad.

### Referencia comercial inicial

Se incorporo como referencia, no como seleccion automatica, el tanque Fibromuebles `TS-3000` (3.0 m3 nominal, huella aproximada documentada 3.30 x 1.15 m). La ficha debe volver a verificarse antes de compra o especificacion.

## FAFA

Dimensionamiento primario:

```text
V_hidraulico = Q * TRH
V_lecho = V_hidraulico / porosidad
Area = V_lecho / altura_medio
```

Preset configurable:

- TRH 8 h;
- intervalo tecnico de referencia 4-10 h;
- porosidad 0.70;
- carga organica de referencia 0.15-0.50 kg DBO/(m3.d).

Si no existe DBO post-tanque, se emite `FAFA_BOD_MISSING` y el calculo queda como preliminar.

### Referencia comercial inicial

Se incorporo `Fibromuebles FAFA-1600` como referencia comercial preliminar. El volumen nominal comercial no se considera automaticamente equivalente al volumen util de medio filtrante.

## Infiltracion v0.2

Se incorporo la Tabla 2 del Anexo 3 del Decreto 42075-S-MINAE:

- se admite captura directa de los 8 descensos de 30 minutos posteriores a una saturacion minima de 24 h;
- el calculo de T utiliza el octavo/ultimo intervalo;

- intervalo permitido: 2-24 min/cm;
- Vp desde 90.33 L/m2/dia para T=2 hasta 26.08 L/m2/dia para T=24;
- para valores T no enteros el metodo predeterminado selecciona conservadoramente la fila entera superior;
- se requieren al menos dos pruebas y se adopta como criterio de diseno la mas lenta (mayor min/cm).

Calcula:

```text
Ai = G / Vp
A'c = Ai * Fp
Lz = Ai / Pe
Ls = A'c / Lz
```

Valida:

- Fp >= 2.5;
- ancho W 0.30-0.90 m;
- profundidad D 0.30-0.90 m;
- fondo y tuberia de zanja a 0 %;
- nivel freatico >= 1.50 m bajo el fondo;
- pendiente del terreno <= 30 %;
- en terreno <=1 % separacion minima `max(W + 1.50, 1.80 m)`;
- en terreno >1 % y <=30 %, trazado siguiendo curvas de nivel y separacion minima 5 m;
- zanja individual <=60 m.

El nucleo calcula tambien el numero minimo de zanjas requerido por el limite de 60 m y una longitud igualada preliminar. Cuando se aportan `available_length_m` y `available_width_m`, `layout.py` calcula un acomodo rectangular preliminar, centra los ramales y reporta `LAYOUT_DOES_NOT_FIT` si no caben. El emplazamiento en poligonos arbitrarios, con obstaculos y curvas de nivel reales sigue pendiente.

## Adaptador FreeCAD experimental

`freecad_adapter.py` consume `geometry_spec` y puede:

1. devolver un plan de operaciones con `dry_run=True` sin modificar FreeCAD;
2. crear una previsualizacion `Part::Feature` dentro de una transaccion si se ejecuta expresamente con `dry_run=False`.

La geometria del FAFA usa aspecto 2:1 solo como previsualizacion cuando aun no se han seleccionado dimensiones constructivas. Las zanjas se muestran paralelas y no sustituyen el futuro algoritmo de ajuste al poligono real.

No se ha ejecutado aun este adaptador en FreeCAD 1.1.3 real; por tanto no esta aceptado ni integrado al Workbench.

## Documentacion 2D neutral

`documentation.py` genera dos contratos JSON-compatible desde el mismo resultado de calculo:

- `build_plan_documentation()`: planta esquematica de tanque, FAFA y zanjas;
- `build_section_documentation()`: seccion con nivel liquido del tanque, medio filtrante, zanja y nivel freatico cuando se conoce;
- `render_svg()`: exportacion SVG simple, sin `FreeCADGui`, Qt ni TechDraw.

La salida es documental preliminar. La geometria final de FAFA y el emplazamiento en poligono real deben reemplazar los supuestos de preview antes de emitir un plano definitivo.

## Validacion previa del caso

`case.py` separa el estado de captura del estado de calculo. La plantilla real de Esparza puede conservar valores `null`; `validate_case_input()` devuelve los campos faltantes y `calculate_case()` responde `INPUT_INCOMPLETE` sin ejecutar formulas ni inventar valores. Las dimensiones rectangulares del area disponible son opcionales para calcular hidraulicamente, pero necesarias para solicitar el layout automatico rectangular.


## Referencias espaciales v0.5

Antes del dimensionamiento fisico se formalizan cuatro referencias de entrada:

```text
LimitePropiedad
HuellaEdificio
AreaTanques
AreaDrenaje
```

El nucleo no depende del tipo de objeto FreeCAD. Todos los adaptadores futuros deben convertir la geometria seleccionada a un `Boundary2D` cerrado con puntos XY. Las fuentes previstas son Draft Wire, Sketch, Part Wire, Part Face, Draft Rectangle, Draft Polygon y conjuntos de lineas seleccionadas que puedan ordenarse como un contorno cerrado.

`Boundary2D` calcula area, perimetro, centroide y bounding box, rechaza contornos de area cero y autointersecciones. `validate_spatial_references()` comprueba que edificio y areas propuestas permanezcan dentro de la propiedad, detecta interseccion de las areas propuestas con el edificio y reporta superposicion entre AreaTanques y AreaDrenaje.

La plantilla `esparza_input_template.json` conserva estas referencias en `null` hasta que se capturen en FreeCAD. Tambien registra como inventario confirmado: 2 S.S. para funcionarios, 1 S.S. para publico, 1 fregadero y 1 pileta de aseo. Este inventario servira como contraste sanitario y no sustituye el consumo real historico.

Prueba aislada del nuevo nucleo espacial: aprobada. Se agregaron cuatro casos a `tests/test_sanitary_core.py`; la suite completa debe volver a ejecutarse en el entorno sincronizado antes de elevar el conteo oficial de pruebas.

## Datos reales pendientes de Esparza

No se han localizado aun datos confiables para cerrar el diseno:

1. consumo/caudal de diseno;
2. dimensiones verificadas del tanque septico existente, si se reutiliza;
3. dos o mas pruebas de infiltracion del sitio;
4. nivel freatico;
5. poligono/area disponible para las zanjas;
6. DBO post-tanque, si se desea verificacion organica del FAFA con datos medidos.

No presentar dimensiones definitivas de Esparza hasta disponer de esos datos.

## Verificacion automatizada 2026-08-26

`tests/test_sanitary_core.py`:

```text
22 passed
```

Incluye tanque, criterios adicionales de entrada/salida, FAFA, Tabla 2, captura de 8 intervalos, limites 2-24 min/cm, seleccion conservadora de dos pruebas, pendiente del terreno, referencias comerciales, orquestador, `geometry_spec`, acomodo rectangular, `dry_run` del adaptador, creadores parametricos experimentales documentacion planta/seccion SVG y manejo seguro de plantillas incompletas.

`compileall` del paquete sanitario: aprobado.

## Siguiente etapa

1. capturar en FreeCAD 1.1.3 un LimitePropiedad, HuellaEdificio, AreaTanques y AreaDrenaje en un documento temporal y validar su conversion a `Boundary2D`;
2. validar `freecad_adapter.py` y `freecad_objects.py` en FreeCAD 1.1.3 real mediante MCP y documento temporal;
3. validar recomputacion, propiedades, Undo/Redo y guardado/reapertura de los `Part::FeaturePython`;
4. enlazar representacion documental en planta y seccion a la misma identidad semantica;
5. implementar caja de distribucion;
6. evolucionar el layout rectangular hacia poligono real, obstaculos y curvas de nivel;
7. ampliar catalogo comercial solo con fichas verificadas y fecha de consulta.

## Regla de seguridad

Los modelos comerciales son referencias y candidatos posteriores al calculo. El programa no debe seleccionar automaticamente una compra ni sustituir el tanque existente de Esparza sin datos y revision tecnica.
