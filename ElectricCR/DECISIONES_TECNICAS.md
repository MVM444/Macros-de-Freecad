# ElectricCR - Decisiones tecnicas

**Proposito:** Registrar decisiones de arquitectura y proceso que deben mantenerse entre tareas y agentes.

**Version:** 2026-08-08 11:46, America/Costa_Rica.

## DT-001 - Separacion entre nivel base y altura de instalacion

Para objetos que contienen representacion 2D y modelo 3D se adopta la siguiente regla:

```text
Placement.Base.z = cota base del nivel o piso
AlturaRel         = altura de instalacion del componente 3D respecto al nivel
Simbolo 2D        = permanece en Z local igual a 0
Altura 3D final   = Placement.Base.z + AlturaRel
```

No debe utilizarse `Placement.Base.z` como sustituto de `AlturaRel` cuando el simbolo 2D debe permanecer visible en planta.

## DT-002 - Tratamiento segun tipo de objeto

### Objeto ElectricCR directo

Para `Part::FeaturePython` con propiedades ElectricCR:

- Modificar `AlturaRel`.
- Mantener `Placement.Base.z`.
- Ejecutar `touch()`.
- Ejecutar un unico `recompute()` controlado al final de la operacion.

### Instancia ElectricCR App::Link

Para un `App::Link` cuya geometria depende de un maestro:

- No limitarse a cambiar la propiedad informativa `AlturaRel` del enlace.
- Obtener o crear el maestro compatible con la nueva altura.
- Reasignar `LinkedObject` al maestro correcto.
- Actualizar los metadatos del enlace.
- Mantener `Placement`, XY, cota base, rotacion, etiqueta y pertenencia a grupos.

### Equipo MEPWorkbenchCR

- Utilizar la propiedad o API semantica de altura de montaje disponible.
- Respetar el nivel base y la logica existente de maestros y sincronizacion.
- Reutilizar funciones publicas o internas existentes solo despues de revisar su contrato y efectos.

### Objeto sencillo

Cuando el objeto no tenga propiedad semantica de altura ni representacion 2D asociada:

- Se permite modificar `Placement.Base.z`.

## DT-003 - Rotacion

La herramienta no debe reemplazar siempre toda la rotacion por un yaw Z.

Debe distinguir:

- Rotacion absoluta en planta.
- Delta de rotacion en planta.
- Orientacion tecnica propia del objeto, por ejemplo montaje vertical, horizontal o en cielo.

Cuando sea posible, la rotacion en planta debe componerse con la orientacion existente en vez de borrarla.

## DT-004 - Herramienta general

La solucion no se limita a sensores. Debe disenarse como servicio general para:

- Sensores de incendio.
- Luminarias.
- Rociadores.
- Altavoces.
- Camaras.
- Tomacorrientes.
- Apagadores.
- Equipos HVAC.
- Otros objetos futuros con simbolo 2D y modelo 3D.

El nucleo de deteccion y actualizacion debe separarse de la interfaz grafica para facilitar su reutilizacion en el futuro Workbench.

## DT-005 - Compatibilidad

- No migrar automaticamente todos los documentos al abrirlos.
- No modificar maestros compartidos si el cambio afectaria otras instancias con distinta altura deseada.
- Crear o reutilizar maestros por firma de propiedades.
- Conservar documentos antiguos y objetos directos.
- Registrar casos no reconocidos y omitirlos de manera segura.

## DT-006 - Transacciones y depuracion

- Agrupar los cambios en una transaccion de FreeCAD.
- Un fallo individual no debe dejar el documento en estado parcialmente incoherente.
- Mostrar en consola el tipo detectado y la estrategia aplicada para cada objeto.
- Informar claramente los objetos omitidos y la causa.

## DT-007 - Una solucion nueva no se considera automaticamente una mejora

ElectricCR adopta como decision permanente que la novedad del codigo no determina su calidad ni su integracion al Workbench.

Reglas:

- Antes de crear una macro o variante nueva debe revisarse si existe una solucion que pueda corregirse, ampliarse o reutilizarse.
- Una macro que ejecuta sin errores puede seguir siendo funcionalmente incorrecta, incompleta o desviada.
- Una prueba automatica exitosa demuestra solamente los casos cubiertos por esa prueba.
- Un numero alto de ejecuciones puede corresponder a desarrollo y depuracion, no necesariamente a uso operativo.
- Una version antigua no debe eliminarse solamente porque exista una version nueva.
- Los resultados negativos de desarrollos con IA deben documentarse expresamente.
- No continuar ampliando una solucion que se haya desviado del objetivo original sin registrar antes esa desviacion y revisar la tarea.

## DT-008 - Tres ejes para evaluar herramientas

Cada herramienta relevante debe evaluarse mediante tres ejes independientes:

1. Rol funcional.
2. Madurez.
3. Resultado comprobado.

El tercer eje utiliza las categorias:

- `COMPROBADA`
- `COMPROBADA-PARCIAL`
- `PROMETEDORA`
- `EXPERIMENTAL`
- `DESVIADA`
- `DUPLICADA`
- `INCOMPLETA`
- `FALLIDA`
- `ABANDONADA`
- `POR VERIFICAR`
- `NO APLICA`

Cuando no exista evidencia suficiente debe utilizarse `POR VERIFICAR`; no se debe inferir exito o fracaso.

Las herramientas nuevas deben comenzar normalmente como `PROMETEDORA`, `EXPERIMENTAL` o `POR VERIFICAR`, segun la evidencia disponible.

## DT-009 - Separacion entre prueba tecnica y validacion funcional

Se adopta el siguiente ciclo de vida:

```text
DEFINIDA
  -> IMPLEMENTADA
  -> PROBADA TECNICAMENTE
  -> VALIDADA FUNCIONALMENTE
  -> REVISADA POR GPT
  -> ACEPTADA
  -> INTEGRADA
```

Definiciones:

- `PROBADA TECNICAMENTE`: el codigo paso las pruebas previstas y no presenta los fallos tecnicos conocidos dentro de los casos ensayados.
- `VALIDADA FUNCIONALMENTE`: Marco comprobo que la herramienta resuelve el objetivo en el flujo real de FreeCAD.
- `REVISADA POR GPT`: se comparo el resultado con el contexto historico, las alternativas y la arquitectura del proyecto.
- `ACEPTADA`: existe decision explicita de conservar la solucion.
- `INTEGRADA`: la solucion forma parte del flujo definitivo, documentacion e inventario correspondientes.

Una tarea puede regresar a `DESARROLLO` desde cualquier etapa si se detectan errores, regresiones o desviaciones.

El detalle operativo completo se mantiene en `FLUJO_GPT_CODEX.md`.
