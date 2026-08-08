# ElectricCR - Tarea actual

**Fecha:** 2026-08-06 14:58, America/Costa_Rica.

**Estado:** Tarea preparada para trabajo futuro. No iniciar modificaciones de codigo sin autorizacion expresa.

## Nombre provisional

Distribucion automatica y verificacion geometrica de detectores de humo.

## Objetivo

Analizar, disenar e implementar posteriormente una herramienta para FreeCAD 1.1.1 que proponga la ubicacion de detectores de humo dentro de recintos cerrados, utilizando la geometria real del recinto y verificaciones de separacion y cobertura.

La herramienta debe integrarse con ElectricCR y aprovechar los objetos de sensor existentes, sin crear un sistema paralelo innecesario.

## Idea de funcionamiento

Para cada recinto seleccionado:

1. Obtener el contorno interior valido del recinto.
2. Calcular el area util.
3. Estimar una cantidad inicial de detectores.
4. Generar una distribucion inicial uniforme.
5. Verificar separacion entre detectores.
6. Verificar la distancia desde los puntos del recinto hasta el detector mas cercano.
7. Verificar la cobertura de las franjas cercanas a paredes y divisiones.
8. Detectar o solicitar informacion sobre obstaculos que puedan afectar el movimiento del humo.
9. Agregar, eliminar o reubicar detectores hasta obtener una propuesta geometrica aceptable.
10. Crear los objetos ElectricCR y producir un informe de verificaciones y advertencias.

## Criterios preliminares de diseno

Los siguientes valores son parametros iniciales para investigar y validar antes de programar. No deben tratarse como una sustitucion de la NFPA 72, de los criterios del Cuerpo de Bomberos de Costa Rica ni de las instrucciones del fabricante:

- Espaciamiento nominal inicial entre detectores: 9.1 m.
- Distancia maxima aproximada desde cualquier punto del recinto hasta el detector mas cercano: 6.4 m, equivalente aproximadamente a 0.7 veces el espaciamiento nominal.
- Distancia maxima preliminar entre una pared y la primera fila de detectores: 4.55 m, equivalente a la mitad del espaciamiento nominal.
- Estimacion inicial por area: aproximadamente un detector por cada 80 m2.
- En recintos irregulares o cuando se adopte un criterio conservador, evaluar una estimacion inicial cercana a un detector por cada 60 m2.

La cantidad calculada por area es solamente una estimacion inicial. El resultado final debe depender de la verificacion geometrica completa.

## Condiciones que deben verificarse antes de usar los parametros

Codex debe confirmar mediante fuentes actuales y confiables para que condiciones resultan aplicables los valores anteriores, incluyendo como minimo:

- Techo liso y horizontal.
- Altura del techo.
- Recintos con cielos inclinados.
- Vigas, nervaduras o cambios de nivel.
- Divisiones que lleguen total o parcialmente al cielo.
- Ductos, bandejas, equipos y otros obstaculos.
- Corrientes de aire, difusores de aire acondicionado y ventilacion.
- Tipo y tecnologia del detector.
- Requisitos del fabricante.
- Reglas o criterios aplicables del Cuerpo de Bomberos de Costa Rica.
- Edicion de NFPA 72 que corresponda al proyecto.

La herramienta debe identificar situaciones que no puedan resolverse con una reticula simple y marcarlas para revision manual.

## Trabajo previo obligatorio

Antes de modificar codigo:

1. Leer `AGENTS.md`, `ESTADO_PROYECTO.md`, `DECISIONES_TECNICAS.md` y este archivo.
2. Buscar en Internet si ya existe una macro, Workbench, complemento o programa de FreeCAD que distribuya detectores, rociadores, luminarias u otros objetos mediante cobertura geometrica.
3. Revisar herramientas de FreeCAD relacionadas con Path, Draft, Arch, BIM, Sketcher, Part, Area, Voronoi, triangulacion, mallas de puntos y optimizacion de posiciones.
4. Revisar el repositorio completo para localizar funciones reutilizables de:
   - deteccion de recintos;
   - lectura de contornos cerrados;
   - creacion de sensores ElectricCR;
   - manejo de niveles y `AlturaRel`;
   - grupos, transacciones y mensajes de consola.
5. Revisar especialmente:
   - `Deteccion/ColocarDetectores_NFPA.FCMacro`;
   - `ElectricCR/electriccr/features/objeto_toma_uno.py`;
   - registro de sensores y simbolos ElectricCR;
   - herramientas existentes que reconozcan habitaciones, caras o contornos.
6. Confirmar la causa, posibilidades y limitaciones.
7. Presentar un plan de implementacion antes de modificar archivos funcionales.

## Entradas propuestas

La primera version debe estudiar como minimo las siguientes entradas:

- Uno o varios recintos seleccionados.
- Contorno mediante cara plana, `Part::Face`, `Draft Wire`, `Sketcher::SketchObject` cerrado u objeto de recinto reconocido.
- Cota base del nivel.
- Altura del cielo o altura de instalacion.
- Tipo de detector ElectricCR que se desea colocar.
- Espaciamiento nominal configurable.
- Distancia maxima de cobertura configurable.
- Distancia maxima a paredes configurable.
- Modo automatico o modo de solo verificacion.
- Tolerancia geometrica.
- Opcion para conservar detectores existentes y verificar su distribucion.

No se debe asumir que todos los recintos son rectangulares.

## Requisitos geometricos

La herramienta debe considerar:

- Poligonos convexos y concavos.
- Recintos en forma de L, T u otras formas irregulares.
- Huecos interiores, columnas o zonas excluidas.
- Pasillos estrechos.
- Unidades internas de FreeCAD en milimetros.
- Contornos con pequenos errores dentro de una tolerancia controlada.
- Puntos que queden realmente dentro del recinto.
- Distancia al detector mas cercano para toda la superficie util.

No basta con calcular solamente el area ni con colocar circulos visuales alrededor de los detectores.

La verificacion de cobertura puede utilizar una malla de puntos adaptativa, triangulacion u otro metodo justificado. Codex debe explicar la precision, costo computacional y limitaciones del metodo seleccionado.

## Estrategia preliminar de distribucion

El algoritmo puede estudiar el siguiente flujo:

```text
INICIO

Para cada recinto valido:

1. Obtener poligono interior y area.

2. Calcular cantidad inicial:
      CantidadInicial = techo(Area / AreaReferencia)

3. Generar candidatos de ubicacion:
      - reticula rectangular;
      - reticula desplazada;
      - eje principal del recinto;
      - puntos derivados de triangulacion;
      - detectores existentes, cuando corresponda.

4. Eliminar candidatos fuera del recinto o dentro de zonas excluidas.

5. Evaluar cada propuesta:
      - separacion entre detectores;
      - cobertura de todos los puntos de control;
      - cobertura cercana a paredes;
      - cantidad de detectores;
      - simetria y facilidad constructiva.

6. Mientras existan puntos sin cobertura:
      agregar o reubicar detector cerca de la zona critica;
      recalcular cobertura.

7. Intentar eliminar detectores redundantes sin perder cobertura.

8. Marcar obstaculos o condiciones que requieren revision manual.

9. Presentar vista previa.

10. Con autorizacion del usuario, crear objetos ElectricCR.

FIN
```

El algoritmo definitivo no debe quedar fijado hasta revisar la arquitectura y realizar pruebas con recintos reales.

## Integracion con ElectricCR

Los detectores creados deben:

- Utilizar el objeto o funcion de sensor existente en ElectricCR.
- Mantener el simbolo 2D en la cota base del nivel.
- Utilizar `AlturaRel` para la altura fisica del modelo 3D.
- Evitar modificar `Placement.Base.z` como sustituto de la altura de instalacion.
- Conservar categoria, tipo, modo visual, propiedades y metadatos definidos por ElectricCR.
- Incorporarse al grupo indicado por el usuario o al grupo de deteccion correspondiente.
- Usar transacciones de FreeCAD para permitir undo y redo.
- Evitar duplicar detectores existentes sin advertencia.

Si se crean instancias `App::Link`, debe respetarse la arquitectura de maestros y la regla de reasignacion por altura registrada en `DECISIONES_TECNICAS.md`.

## Interfaz propuesta

La interfaz inicial debe mantenerse sencilla e incluir, como minimo:

- Seleccion de recinto o recintos.
- Tipo de detector.
- Altura de instalacion.
- Espaciamiento nominal.
- Distancia maxima de cobertura.
- Area de referencia inicial.
- Modo `Proponer detectores`.
- Modo `Verificar detectores existentes`.
- Boton de vista previa.
- Boton de crear o aplicar.
- Resumen de resultados y advertencias.

La vista previa debe diferenciar claramente:

- Detectores propuestos.
- Detectores existentes.
- Puntos o zonas sin cobertura.
- Casos que requieren revision manual.

## Salidas esperadas

- Objetos de detector ElectricCR correctamente ubicados.
- Conteo de detectores por recinto.
- Area del recinto.
- Parametros utilizados.
- Distancia maxima encontrada al detector mas cercano.
- Separacion maxima entre detectores vecinos relevantes.
- Lista de zonas sin cobertura.
- Lista de obstaculos o condiciones no evaluadas automaticamente.
- Mensajes detallados en la consola de FreeCAD.
- Posibilidad futura de generar una tabla o reporte de calculo.

## Mensajes de depuracion

Utilizar un prefijo consistente, por ejemplo:

```text
[ElectricCR.DetectorLayout]
```

Registrar como minimo:

- objeto o recinto procesado;
- tipo de geometria detectada;
- area calculada;
- parametros usados;
- cantidad inicial;
- iteraciones realizadas;
- detectores agregados, movidos o eliminados;
- distancia maxima de cobertura obtenida;
- advertencias;
- resultado final o motivo de omision.

## Seguridad y alcance normativo

- La herramienta sera una ayuda de diseno y verificacion, no una certificacion automatica de cumplimiento.
- No debe mostrar `Cumple NFPA 72` cuando existan condiciones no evaluadas.
- Debe distinguir entre `Verificacion geometrica satisfactoria` y `Revision normativa completa`.
- Debe permitir que el usuario revise y modifique manualmente la propuesta antes de crear los objetos definitivos.
- Los parametros normativos deben quedar configurables y documentados, no ocultos como constantes sin explicacion.

## Archivos que probablemente requeriran revision

- `Deteccion/ColocarDetectores_NFPA.FCMacro`
- `ElectricCR/electriccr/features/objeto_toma_uno.py`
- archivos del registro de sensores ElectricCR;
- utilidades existentes de geometria, seleccion, niveles y grupos;
- posibles modulos nuevos dentro de `ElectricCR/electriccr/` para separar:
  - geometria del recinto;
  - calculo de cobertura;
  - optimizacion de posiciones;
  - creacion de objetos;
  - interfaz grafica.

La ubicacion y nombre definitivo de cualquier archivo nuevo deben proponerse despues de revisar la estructura existente.

## Pruebas requeridas

Como minimo:

1. Recinto rectangular pequeno que requiera un detector.
2. Recinto rectangular largo que requiera varios detectores.
3. Recinto de area menor a 80 m2 cuya forma obligue a colocar mas de un detector.
4. Recinto en forma de L.
5. Pasillo estrecho.
6. Recinto con hueco interior o columna.
7. Varios recintos procesados en una sola operacion.
8. Verificacion de detectores existentes correctamente distribuidos.
9. Deteccion de una zona sin cobertura.
10. Cambio de parametros de espaciamiento y cobertura.
11. Creacion en nivel con `Placement.Base.z` distinto de cero.
12. Confirmacion de que el simbolo 2D permanece en la cota base.
13. Confirmacion de que el modelo 3D utiliza `AlturaRel`.
14. Undo y redo.
15. Guardar, cerrar y reabrir el documento.
16. Recinto invalido o contorno abierto, con omision segura y mensaje claro.

## Fuera de alcance inicial

Salvo que el analisis recomiende lo contrario, la primera version no debe intentar resolver automaticamente:

- modelado completo del flujo de humo;
- simulacion CFD;
- seleccion del tipo de detector segun riesgo;
- calculo de sensibilidad o tiempo de respuesta;
- certificacion normativa;
- cielos complejos con multiples niveles sin intervencion del usuario;
- reconocimiento automatico perfecto de todos los obstaculos 3D.

## Resultado esperado de la primera etapa

Sin programar todavia, Codex debe entregar:

1. Busqueda previa de soluciones existentes.
2. Revision de la arquitectura ElectricCR relacionada.
3. Identificacion de los tipos reales de contorno y sensor disponibles.
4. Confirmacion o correccion de los parametros preliminares.
5. Propuesta del algoritmo geometrico.
6. Propuesta de estructura de archivos.
7. Riesgos y limitaciones.
8. Plan de pruebas.

Solo despues de revisar y autorizar ese analisis se podra iniciar la implementacion.
