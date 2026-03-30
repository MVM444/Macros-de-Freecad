# Archivo: FLUJO_DE_TRABAJO.md
**Proposito:** Definir el flujo operativo recomendado para usar MEPWorkbenchCR en FreeCAD.  
**Fecha y hora de version:** 2026-03-30 08:15 (editable)  
**Nota:** Proyecto en etapa inicial, orientado a FreeCAD.

# Flujo de Trabajo HVAC

## Flujo base dentro de FreeCAD

1. Dibujar o seleccionar poligonos de recintos (regular o irregular) en el modelo.
2. Crear/actualizar recintos HVAC desde poligono(s) o desde grupo `Areas/Áreas/Recintos`.
3. Definir altura y propiedades del recinto.
4. Crear o editar el proyecto HVAC.
5. Definir variables climaticas del proyecto.
6. Ejecutar calculo de carga del recinto.
7. Insertar evaporadora dentro del recinto.
8. Insertar condensadora en ubicacion tecnica adecuada.
9. Asignar evaporadoras a la condensadora (comando `Asignar a Condensadora`).
10. Crear rutas HVAC entre puertos.
11. Mostrar etiqueta HVAC del recinto.
12. Ejecutar `Validar HVAC` para revisar cobertura y consistencia del sistema.

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

### Etapa 3: Calculo

- Ejecutar calculo rapido para dimensionamiento preliminar.
- Ejecutar calculo preciso cuando se requiera ajuste fino.
- Registrar carga final por recinto para seleccion de equipos.

### Etapa 4: Equipos

- Insertar evaporadora en posicion realista de instalacion.
- Asignar capacidad de evaporadora y validar cobertura.
- Insertar condensadora en zona tecnica independiente del recinto.
- Asociar evaporadoras a condensadora con `Asignar a Condensadora` y revisar balance total.

### Etapa 5: Rutas y conexiones

- Crear rutas por tipo de servicio: refrigerante, electrica y condensados.
- Asegurar conexion entre puertos validos.
- Verificar longitud y nivel de ruta segun criterio del proyecto.

### Etapa 6: Etiquetado y revision

- Activar etiqueta HVAC sobre el recinto.
- Revisar nombre de recinto, carga BTU/h, equipo y porcentaje de cobertura.
- Corregir capacidad, rutas o clima si la cobertura no cumple objetivo.

## Observaciones de uso practico

- Trabajar primero en un documento limpio para validar flujo MVP.
- Confirmar asociaciones de objetos despues de recargas del Workbench.
- No cerrar seleccion tecnica con base solo en calculo rapido cuando existan cargas internas relevantes.
- Priorizar consistencia de puertos y rutas antes de generar planos o reportes.
