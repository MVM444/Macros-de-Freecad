# TAREA ACTUAL - Facil Arquitectura - Puerta doble BIM

Fecha: 2026-08-12 16:52 -06:00
FreeCAD objetivo: 1.1.3 Windows
Workbench: Facil Arquitectura
Version final: 0.11.1 | build 2026.08.12.2
Estado: APROBADA TECNICAMENTE / VERIFICADO_MCP / VERIFICADO_VISUAL

## Resultado final 2026-08-12

Los trece criterios de aceptacion fueron verificados. Pasaron 139/139 pruebas
unitarias y los smokes MCP de puerta libre, puerta alojada, hueco nuevo y
preexistente, materiales, apertura, movimiento con host, persistencia, eliminacion,
ruta real del comando y dos hot restarts. El FCStd original de La Cruz conservo
tamano, mtime y SHA-256. La prueba manual corta de Marco permanece como validacion
de usuario, no como fallo tecnico pendiente.

## Objetivo

Corregir la herramienta `FA Insertar puerta doble BIM` para que la puerta doble de acceso funcione como una puerta BIM normal de FreeCAD:

- insercion libre;
- insercion alojada correctamente en un muro seleccionado;
- hueco real en el muro;
- `IfcType = Door`;
- movimiento con el muro anfitrion;
- materiales y transparencias sin errores;
- conservar la organizacion actual de barras de Facil Arquitectura.

No agregar funciones nuevas hasta resolver los fallos actuales.

## Estado actual confirmado

La reorganizacion del Workbench carga correctamente estas cinco barras:

- `FA Proyecto BIM`
- `FA Estructura BIM`
- `FA Aberturas BIM`
- `FA Recintos y cielos`
- `FA Plataforma`

El comando `FA_InsertDoubleDoorBIM` esta registrado. El hot restart completa correctamente y no duplica las barras. No modificar esta organizacion salvo que una prueba demuestre un problema real.

## Fallos observados en FreeCAD

Registro real:

```text
pyException: Traceback (most recent call last):
  File "...\\Mod\\BIM\\ArchWindow.py", line 886, in updateData
    self.colorize(obj)
  File "...\\Mod\\BIM\\ArchWindow.py", line 985, in colorize
    sapp_mat.Transparency = 1.0 - color[3]
                                  ~~~~~^^^
<class 'IndexError'>: tuple index out of range
```

El error ocurre tres veces durante la insercion.

Luego aparece:

```text
[FACILARQ] FA Insertar puerta doble BIM: La puerta doble no intersecta realmente el muro seleccionado.
```

Prueba realizada con:

- documento: `La Cruz Version 2.1`;
- FreeCAD: 1.1.3;
- fecha: 2026-08-12;
- comando: `FA_InsertDoubleDoorBIM`.

## Archivos principales a revisar

Revisar primero estos archivos completos:

1. `FacilArquitecturaWB/core/double_door_bim.py`
2. `FacilArquitecturaWB/commands/cmd_insert_double_door_bim.py`
3. `FacilArquitecturaWB/ui/dialog_double_door_bim.py`
4. `FacilArquitecturaWB/InitGui.py`
5. `FacilArquitecturaWB/DOCUMENTACION_WORKBENCH.md`
6. `FacilArquitecturaWB/tests/freecad_double_door_bim_smoke.py`
7. `FacilArquitecturaWB/tests/freecad_double_door_toolbar_smoke.py`
8. `Scripts Varios/FacilArquitectura_BIM/Puriscal/RESULTADO_CODEX.md`

Tambien localizar el codigo exacto donde se crean o asignan los materiales de marco de aluminio, vidrio y panel inferior. Leer `AGENTS.md` si existe en la raiz del proyecto.

## Regla 1 - No tocar lo que ya funciona

No modificar innecesariamente:

- loaders globales;
- `ElectricCRLoader`;
- `GameEngineExportLoader`;
- `MEPWorkbenchCRLoader`;
- estructura de las cinco barras ya creada;
- comandos ajenos a la puerta;
- documento `La Cruz Version 2.1`.

No guardar cambios sobre el FCStd original durante pruebas automaticas.

## Parte A - Corregir materiales y transparencia

### Problema

`ArchWindow.py` intenta acceder al cuarto componente del color mediante `color[3]`, pero uno o mas materiales entregan solamente RGB.

### Tarea

Revisar como `double_door_bim.py` crea y asigna los materiales. Asegurar que todos los componentes usados por `ArchWindow` tengan datos compatibles con FreeCAD 1.1.3.

Verificar especialmente:

- aluminio;
- vidrio;
- panel inferior.

No resolver el problema aplicando un unico `ShapeColor` a toda la puerta si eso elimina la diferenciacion de componentes.

La puerta debe conservar:

- marco aluminio gris satinado;
- vidrio claramente distinguible y transparente;
- panel inferior opaco.

### Validacion

No debe volver a aparecer:

```text
IndexError: tuple index out of range
```

ni ninguna excepcion en `ArchWindow.colorize()`.

## Parte B - Corregir insercion BIM en muro

### Problema

El comando termina con:

```text
La puerta doble no intersecta realmente el muro seleccionado.
```

No asumir que `door.Shape` debe intersectar el muro como criterio de alojamiento. La geometria visible de la puerta y el volumen de abertura del muro son conceptos distintos.

### Tarea

Revisar la logica de:

- seleccion del host;
- punto de insercion;
- `Placement`;
- `Normal`;
- `Hosts`;
- `Host`, si el objeto lo expone;
- `MoveWithHost`;
- `HoleWire`;
- `HoleDepth`;
- `Subvolume` o volumen de abertura disponible en ArchWindow;
- recomputacion del host.

La insercion alojada debe trabajar como una puerta BIM normal.

### Secuencia esperada

1. El usuario selecciona un muro.
2. El usuario define un punto aproximado de insercion.
3. El comando obtiene la posicion adecuada sobre el muro.
4. Calcula la orientacion del muro.
5. Calcula una normal perpendicular coherente.
6. Coloca la puerta sobre el plano correcto.
7. Asigna el muro como host.
8. Activa `MoveWithHost`.
9. Recalcula puerta y muro.
10. Confirma el hueco usando el mecanismo BIM de abertura, no solo la interseccion del `Shape` visible.

No hacer cortes booleanos manuales permanentes si el objeto Arch/BIM ya ofrece el mecanismo de host y abertura.

## Parte C - Prueba de puerta libre

Crear una puerta libre en un documento temporal y verificar:

- `IfcType = Door`;
- ancho = 2000 mm;
- alto = 2100 mm;
- dos hojas;
- materiales correctos;
- `Opening` disponible;
- ningun host asignado;
- ninguna excepcion.

## Parte D - Prueba de puerta alojada

Crear un documento temporal exclusivo para prueba.

Crear un muro BIM simple suficientemente grande, por ejemplo:

- longitud: 5000 mm;
- alto: 3000 mm;
- espesor: 150 mm o 200 mm.

Insertar una puerta doble BIM en el muro y verificar:

- puerta colocada sobre el muro;
- `IfcType = Door`;
- host asignado;
- `MoveWithHost = True`;
- hueco de aproximadamente 2000 x 2100 mm;
- marco visible;
- vidrio visible;
- panel inferior visible;
- muro realmente abierto;
- ningun error de materiales.

Mover el muro una distancia conocida y comprobar que la puerta lo acompana. Eliminar la puerta y recomputar para confirmar que el muro queda consistente.

## Parte E - Prueba de apertura

Con la puerta libre o alojada:

1. `Opening = 0`
2. `Opening = 25`
3. `Opening = 50`
4. `Opening = 100`
5. volver a `Opening = 0`

Verificar que:

- cada hoja gira sobre su lado correcto;
- marco de hoja, vidrios y panel inferior se mueven juntos;
- no quedan componentes flotando;
- no cambia el marco exterior.

Si una hoja abre en sentido incorrecto, corregir solamente su `Edge` / `Mode` o parametro equivalente.

## Parte F - Depuracion requerida

Agregar mensajes suficientes para la insercion alojada, por ejemplo:

```text
[FACILARQ] Host seleccionado: ...
[FACILARQ] Punto insercion: ...
[FACILARQ] Normal calculada: ...
[FACILARQ] Hosts asignados: ...
[FACILARQ] MoveWithHost: ...
[FACILARQ] Hole/Subvolume: ...
[FACILARQ] Interseccion hueco/muro: ...
[FACILARQ] Corte BIM confirmado
```

No inundar la Vista de reportes.

## Parte G - Pruebas automaticas

Mantener las pruebas existentes. La referencia actual reportada es:

`139 pruebas aprobadas`

No reducir esa cobertura.

Agregar o actualizar pruebas para cubrir:

1. materiales con transparencia compatible;
2. puerta libre;
3. puerta alojada;
4. hueco real;
5. `MoveWithHost`;
6. persistencia FCStd;
7. apertura de ambas hojas;
8. ausencia de duplicacion de toolbars tras hot restart.

Ejecutar las pruebas completas al finalizar.

## Criterio de aceptacion

La tarea solo se considera aprobada si:

1. No aparece `IndexError` en `ArchWindow.colorize`.
2. La puerta libre sigue funcionando.
3. La puerta alojada se inserta en un muro real.
4. El muro presenta un hueco real de la puerta.
5. La puerta conserva `IfcType = Door`.
6. El host queda asignado correctamente.
7. `MoveWithHost` funciona.
8. El vidrio conserva transparencia.
9. El aluminio y panel inferior se ven correctamente.
10. `Opening` funciona en ambas hojas.
11. Las cinco barras actuales siguen apareciendo una sola vez.
12. Las pruebas existentes siguen aprobando.
13. El FCStd original de La Cruz no se modifica durante pruebas automaticas.

## Versionado

No subir version/build al empezar. Primero corregir y probar. Solo si todos los criterios pasan, actualizar la version de Facil Arquitectura de forma coherente como revision de mantenimiento posterior a `0.11.0`, siguiendo el esquema ya usado por el proyecto.

## Resultado Codex

Actualizar:

`Scripts Varios/FacilArquitectura_BIM/Puriscal/RESULTADO_CODEX.md`

Debe incluir:

- fecha y hora;
- archivos leidos;
- archivos modificados;
- causa real del error de `color[3]`;
- causa real del fallo de alojamiento;
- solucion aplicada;
- pruebas ejecutadas;
- total de pruebas aprobadas;
- resultado de puerta libre;
- resultado de puerta alojada;
- resultado de `Opening`;
- estado de materiales;
- pendientes;
- instrucciones exactas para la siguiente prueba manual en FreeCAD 1.1.3.

## Prueba manual final para Marco

Despues de pasar las pruebas automaticas, indicar un procedimiento corto:

1. abrir Facil Arquitectura;
2. activar `FA Aberturas BIM`;
3. seleccionar un muro;
4. seleccionar punto de insercion;
5. ejecutar `FA Insertar puerta doble BIM`;
6. confirmar hueco real;
7. probar `Opening`;
8. copiar solo las lineas relevantes de la Vista de reportes si ocurre un error.

No continuar con nuevas funciones de puertas hasta aprobar esta tarea.
