# ElectricCR - Decisiones tecnicas

**Proposito:** Registrar decisiones de arquitectura que deben mantenerse entre tareas y agentes.

**Version:** 2026-08-06 12:41, America/Costa_Rica.

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

- Utilizar `Height` como altura de montaje.
- Respetar `BaseLevel` y la logica existente de maestros y sincronizacion.
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

La solucion no se limita a sensores. Debe diseñarse como servicio general para:

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