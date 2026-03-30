# Archivo: FLUJO_DE_TRABAJO.md
**Proposito:** Definir el flujo operativo recomendado para usar MEPWorkbenchCR en FreeCAD.  
**Fecha y hora de version:** 2026-03-30 19:40 (editable)  
**Nota:** MVP centrado en recintos, etiquetas y evaporadoras.

# Flujo de Trabajo HVAC

## Flujo principal dentro de FreeCAD (MVP)

1. Seleccionar poligonos de recintos o grupo `Areas/Areas/Recintos`.
2. Ejecutar `Crear o Actualizar Recintos HVAC`.
3. Ejecutar `Calcular HVAC`.
4. Ver etiquetas actualizadas automaticamente sobre cada recinto.
5. Insertar evaporadora concreta en el recinto.
6. Revisar cobertura en etiqueta (`EQ: capacidad (porcentaje)`).

## Flujo secundario de sistema (fase posterior)

7. Crear/ajustar Proyecto HVAC.
8. Insertar Condensadora.
9. Asignar Evaporadoras a Condensadora.
10. Crear Ruta HVAC.
11. Ejecutar Validar HVAC.

## Detalle por etapa

### Etapa 1: Recinto

- El recinto es la referencia central de calculo.
- El recinto debe originarse desde geometria real (poligono o cara), no desde objeto vacio.
- El area y altura deben revisarse antes de calcular.
- La propiedad de ocupacion y carga de equipos internos debe completarse.

### Etapa 2: Clima del proyecto

- Definir lugar, altitud, temperatura exterior, humedad y temperatura interior.
- Confirmar que la humedad por defecto conservadora sea la esperada para el escenario.
- Verificar que el factor climatico resultante sea tecnicamente coherente.

### Etapa 3: Calculo y resultado

- Calcular HVAC debe actualizar carga, cobertura y etiquetas en un solo paso.
- Ejecutar modo rapido para dimensionamiento preliminar.
- Ejecutar modo preciso cuando se requiera ajuste fino.
- Registrar carga final por recinto para seleccion de equipos.

### Etapa 4: Evaporadora

- Insertar evaporadora concreta (ejemplo: `Pared_12000`, `Cassette_24000`).
- Si hay recinto seleccionado, asignar evaporadora al recinto seleccionado.
- Si no hay seleccion, detectar recinto por posicion; si falla, asignar manualmente.
- Revisar cobertura directamente en etiqueta del recinto.

### Etapa 5: Sistema (segunda capa)

- Insertar condensadora y asociar evaporadoras cuando aplique.
- Crear rutas por tipo de servicio: refrigerante, electrica y condensados.
- Asegurar conexion entre puertos validos y validar sistema completo.

## Observaciones de uso practico

- Trabajar primero en un documento limpio para validar flujo MVP.
- Confirmar asociaciones de objetos despues de recargas del Workbench.
- No cerrar seleccion tecnica con base solo en calculo rapido cuando existan cargas internas relevantes.
- Priorizar consistencia de puertos y rutas antes de generar planos o reportes.
