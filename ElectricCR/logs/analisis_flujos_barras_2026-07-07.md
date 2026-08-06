# Analisis de flujos por barra - ElectricCR

- Registro actual: `tool_usage.json`, actualizado `2026-07-07T08:30:12`.
- Corte de comparacion: `tool_usage-DESKTOP-5586S7P.json`, actualizado `2026-03-28T10:54:20`.
- Limitacion: los logs actuales guardan conteos y ultimo uso por herramienta, no una secuencia completa de eventos. Por eso este analisis infiere fases por crecimiento y ultimo uso, pero no puede probar co-uso minuto a minuto.
- Mejora aplicada: a partir de ahora ElectricCR tambien escribe `tool_events.jsonl`, con una linea por evento. Ese archivo si permitira medir cambios de flujo, co-uso de barras, herramientas consecutivas y duracion aproximada entre acciones.

## Crecimiento por barra desde el corte anterior

| Barra / grupo | Total actual | Crecio desde corte | Herramientas | Ultimo uso |
|---|---:|---:|---:|---|
| Draft heredado | 2722 | 619 | 39 | 2026-06-22 14:41 |
| Conectar | 946 | 210 | 30 | 2026-04-22 15:41 |
| Configuracion del proyecto | 261 | 177 | 21 | 2026-07-01 13:22 |
| Areas | 171 | 145 | 10 | 2026-06-22 16:10 |
| Iluminación | 278 | 132 | 15 | 2026-07-01 12:25 |
| ElectricCR | 62 | 62 | 1 | 2026-06-12 10:11 |
| Objetos | 70 | 22 | 7 | 2026-06-23 11:56 |
| Raiz | 65 | 19 | 6 | 2026-06-09 10:55 |
| Tomacorrientes | 126 | 16 | 9 | 2026-06-22 10:46 |
| ElectricCR sistema | 33 | 11 | 4 | 2026-07-07 08:29 |
| Cajas | 185 | 7 | 7 | 2026-04-22 12:05 |
| Tableros | 2 | 2 | 1 | 2026-07-07 08:30 |
| Organizacion del proyecto | 16 | 1 | 3 | 2026-06-22 15:17 |
| Exportar | 14 | 0 | 1 | 2026-03-10 10:35 |
| Acometida | 3 | 0 | 1 | 2026-03-10 10:25 |

## Barras de fase

Estas barras parecen activarse cuando se trabaja un frente especifico y luego pierden importancia al cambiar de frente.

| Barra | Total | Crecio | Ultimo uso | Herramientas dominantes |
|---|---:|---:|---|---|
| Conectar | 946 | 210 | 2026-04-22 15:41 | [ACTIVA] Conectar Alimentadores a Tablero (182), [LEGACY] Conectar Cajas y Alimentadores a Tablero (v1) (137), [ACTIVA] Ajustar Alimentador o Ramal Manual (100) |
| ElectricCR | 62 | 62 | 2026-06-12 10:11 | Insertar_Tablero (62) |
| Raiz | 65 | 19 | 2026-06-09 10:55 | Crear apagadores en sketch (34), Insertar_Dispositivo (20), Gestionar_Registro_Electrico (6) |
| Tomacorrientes | 126 | 16 | 2026-06-22 10:46 | Contar tomacorrientes y exportar (33), Etiqueta de circuito (32), RotarTomacorriente (19) |
| Cajas | 185 | 7 | 2026-04-22 12:05 | Colocar Cajas Octogonales Mejor Ubicacion... (45), Insertar Cajas Octogonales Encima... (45), Colocar Cajas Octogonales sobre Dispositivos (40) |
| Tableros | 2 | 2 | 2026-07-07 08:30 | Electrical_Schedule_Base (2) |
| Organizacion del proyecto | 16 | 1 | 2026-06-22 15:17 | Ordenar grupos (10), Multirenombrar (5), AbrirDirectorioElectricCR (1) |
| Exportar | 14 | 0 | 2026-03-10 10:35 | Exportar DXF/DWG (plano de trabajo) (14) |
| Acometida | 3 | 0 | 2026-03-10 10:25 | Registrar acometida y ruta (3) |

## Barras transversales o de soporte

Estas no parecen depender tanto de un solo frente; sirven como soporte frecuente entre tareas.

| Barra | Total | Crecio | Ultimo uso | Herramientas dominantes |
|---|---:|---:|---|---|
| Configuracion del proyecto | 261 | 177 | 2026-07-01 13:22 | Gestionar visibilidad ElectricCR (51), Calculo de circuitos por tablero (31), Unifilar interactivo tableros (26) |
| Areas | 171 | 145 | 2026-06-22 16:10 | RectFromBoundaryLines (100), Areas por click (22), AsignarNombreEstandar (20) |
| Iluminación | 278 | 132 | 2026-07-01 12:25 | Asistente CSV 2 Pasos (52), Colocar Luminarias Link (51), Importar Luminarias CSV (28) |
| Objetos | 70 | 22 | 2026-06-23 11:56 | Alinear (34), RenombrarDiálogo (15), Copiar Formato Electrico (13) |

## Lectura especifica

- **Iluminacion** funciona como barra de fase: tiene uso fuerte y reciente en el frente de luminarias, pero no deberia dominar cuando se pasa a tomas.
- **Tomacorrientes** tambien es una barra de fase: util mientras se trabaja tomas, secundaria fuera de ese flujo.
- **Cajas** es fase/especializada, vinculada a luminarias y ubicacion de cajas octogonales.
- **Conectar** mezcla dos cosas: flujo real de conexion y ruido de implementacion en alimentadores. Debe estar visible, pero no todos sus comandos merecen el mismo peso.
- **Areas** debe tratarse como importante aunque no sea la barra mas grande: `RectFromBoundaryLines` concentra 100 usos que parecen operativos.
- **Objetos** encaja mejor como barra transversal: `Alinear`, `RenombrarDialogo`, cambios de altura/rotacion y utilidades de seleccion aparecen como apoyo entre flujos.
- **Draft heredado** es el soporte transversal mas fuerte: Mover, Linea, Rectangulo, Grupo y Snaps son usados mas que muchas macros.
- **BIM/Arch heredado** no tiene uso registrado; no hay evidencia para mantenerlo visible por defecto.

## Recomendacion de interfaz

Mantener visible por defecto:

- `Objetos` como barra transversal.
- `Areas`, por `RectFromBoundaryLines`.
- `Conectar`, pero idealmente depurada o separada entre comandos activos y legacy/pruebas.
- Una barra Draft compacta o acceso rapido a Mover, Linea, Rectangulo, Add/Select Group y Snaps principales.

Mostrar segun el frente activo o dejar en panel:

- `Iluminacion` cuando el frente sea luminarias.
- `Tomacorrientes` cuando el frente sea tomas.
- `Cajas` cuando se este coordinando luminarias/cajas.
- `Tableros` cuando se trabaje tableros.
