# Reporte de macros mas usadas - ElectricCR

- Fuente: `ElectricCR/logs/tool_usage.json`
- Ultima actualizacion del registro: `2026-07-07T08:30:12`
- Macros unicas normalizadas: **112**
- Ejecuciones de macros registradas: **2199**
- Nota: se normalizaron rutas por `Macros-de-Freecad/...` para unir usos del mismo archivo desde distintos perfiles de Windows.
- Criterio importante: este ranking es un conteo bruto. Algunas macros tienen muchos usos por ciclos de desarrollo, pruebas y ajuste fino; eso no siempre equivale a importancia operativa diaria.

## Lectura operativa corregida

El conteo alto de `[ACTIVA] Conectar Alimentadores a Tablero` y `[LEGACY] Conectar Cajas y Alimentadores a Tablero (v1)` debe leerse con cautela: esas macros acumularon muchas ejecuciones porque costaron mucho de implementar y depurar.

En cambio, `RectFromBoundaryLines` con 100 usos es una señal fuerte de uso real: es una macro importante del flujo de trabajo, no solo ruido de desarrollo.

Prioridades operativas inferidas:

- **Areas / RectFromBoundaryLines**: mantener visible; alto uso real y reciente.
- **Conectar**: mantener el grupo visible, pero no sobredimensionar la importancia de alimentadores solo por conteo bruto.
- **Iluminacion** y **Cajas**: mantener visibles por uso acumulado y trabajo recurrente.
- **Configuracion del proyecto**: alto uso, pero probablemente conviene evaluarlo por comandos especificos antes de darle una barra completa.
- **Tableros**: uso bajo historico; visible solo cuando se este trabajando tableros.

## Resumen por grupo

| Grupo | Ejecuciones | % macros | Macros usadas | Ultimo uso |
|---|---:|---:|---:|---|
| Conectar | 946 | 43.0% | 30 | 2026-04-22 15:41 |
| Iluminación | 278 | 12.6% | 15 | 2026-07-01 12:25 |
| Configuracion del proyecto | 261 | 11.9% | 21 | 2026-07-01 13:22 |
| Cajas | 185 | 8.4% | 7 | 2026-04-22 12:05 |
| Areas | 171 | 7.8% | 10 | 2026-06-22 16:10 |
| Tomacorrientes | 126 | 5.7% | 9 | 2026-06-22 10:46 |
| Objetos | 70 | 3.2% | 7 | 2026-06-23 11:56 |
| Raiz | 65 | 3.0% | 6 | 2026-06-09 10:55 |
| ElectricCR | 62 | 2.8% | 1 | 2026-06-12 10:11 |
| Organizacion del proyecto | 16 | 0.7% | 3 | 2026-06-22 15:17 |
| Exportar | 14 | 0.6% | 1 | 2026-03-10 10:35 |
| Acometida | 3 | 0.1% | 1 | 2026-03-10 10:25 |
| Tableros | 2 | 0.1% | 1 | 2026-07-07 08:30 |

## Top 25 macros por conteo bruto

| # | Macro | Grupo | Usos | % macros | Ultimo uso | Archivo |
|---:|---|---|---:|---:|---|---|
| 1 | [ACTIVA] Conectar Alimentadores a Tablero | Conectar | 182 | 8.3% | 2026-03-28 15:00 | `Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro` |
| 2 | [LEGACY] Conectar Cajas y Alimentadores a Tablero (v1) | Conectar | 137 | 6.2% | 2026-03-26 14:44 | `Conectar/Conectar_Cajas_a_Tablero_Auto.FCMacro` |
| 3 | [ACTIVA] Ajustar Alimentador o Ramal Manual | Conectar | 100 | 4.5% | 2026-03-26 13:26 | `Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro` |
| 4 | RectFromBoundaryLines | Areas | 100 | 4.5% | 2026-06-22 16:10 | `Areas/RectFromBoundaryLines.FCMacro` |
| 5 | Conectar_Circuitos_Luminarias_Auto | Conectar | 97 | 4.4% | 2026-03-30 10:35 | `Conectar/Conectar_Circuitos_Luminarias_Auto.FCMacro` |
| 6 | Panel Conexiones Endpoints (Beta) | Conectar | 85 | 3.9% | 2026-04-22 12:35 | `Conectar/Panel_Conexiones_Endpoints.FCMacro` |
| 7 | Insertar_Tablero | ElectricCR | 62 | 2.8% | 2026-06-12 10:11 | `ElectricCR/Insertar_Tablero.FCMacro` |
| 8 | [ACTIVA] Conectar Circuitos Ramales | Conectar | 57 | 2.6% | 2026-03-28 16:15 | `Conectar/Conectar_Circuitos_Ramales_Auto.FCMacro` |
| 9 | Asistente CSV 2 Pasos | Iluminación | 52 | 2.4% | 2026-04-22 15:51 | `Iluminación/AsisCSV2Pasos.FCMacro` |
| 10 | Colocar Luminarias Link | Iluminación | 51 | 2.3% | 2026-07-01 12:25 | `Iluminación/ColocarLuminarias_Link.FCMacro` |
| 11 | Gestionar visibilidad ElectricCR | Configuracion del proyecto | 51 | 2.3% | 2026-07-01 12:44 | `Configuracion del proyecto/Gestionar_Visibilidad_ElectricCR.FCMacro` |
| 12 | Colocar Cajas Octogonales Mejor Ubicacion... | Cajas | 45 | 2.0% | 2026-03-26 16:18 | `Cajas/Colocar_Cajas_Octogonales_Mejor_Ubicacion.FCMacro` |
| 13 | Insertar Cajas Octogonales Encima... | Cajas | 45 | 2.0% | 2026-04-22 12:05 | `Cajas/Insertar_Cajas_Octogonales_Encima.FCMacro` |
| 14 | Colocar Cajas Octogonales sobre Dispositivos | Cajas | 40 | 1.8% | 2026-03-26 19:09 | `Cajas/Colocar_Cajas_Octogonales_Sobre_Dispositivos.FCMacro` |
| 15 | Colocar Cajas Octogonales entre Luminarias | Cajas | 36 | 1.6% | 2026-04-01 14:34 | `Cajas/Colocar_Cajas_Octogonales_Entre_Luminarias.FCMacro` |
| 16 | Alinear | Objetos | 34 | 1.5% | 2026-06-15 14:21 | `Objetos/Alinear.FCMacro` |
| 17 | Crear apagadores en sketch | Raiz | 34 | 1.5% | 2026-03-25 13:43 | `ColocarApagadores_Sketch.FCMacro` |
| 18 | Contar tomacorrientes y exportar | Tomacorrientes | 33 | 1.5% | 2026-04-18 10:56 | `Tomacorrientes/contar_tomacorrientes_y_exportar.FCMacro` |
| 19 | Etiqueta de circuito | Tomacorrientes | 32 | 1.5% | 2026-02-23 11:56 | `Tomacorrientes/Insertar_Etiqueta_Circuito.FCMacro` |
| 20 | Calculo de circuitos por tablero | Configuracion del proyecto | 31 | 1.4% | 2026-04-23 11:00 | `Configuracion del proyecto/Calculo_Circuitos_PanelSchedule.FCMacro` |
| 21 | Conectar_objetos_en_C | Conectar | 31 | 1.4% | 2026-04-14 15:46 | `Conectar/Conectar_objetos_en_C.FCMacro` |
| 22 | [ACTIVA] Sustituir Conexion EMT por Linea | Conectar | 29 | 1.3% | 2026-04-15 16:24 | `Conectar/Sustituir_Conexion_EMT_por_Linea.FCMacro` |
| 23 | Importar Luminarias CSV | Iluminación | 28 | 1.3% | 2026-03-25 18:06 | `Iluminación/Importar_Luminarias_CSV_ElectricCR.FCMacro` |
| 24 | Unifilar interactivo tableros | Configuracion del proyecto | 26 | 1.2% | 2026-04-20 14:17 | `Configuracion del proyecto/UnifilarInteractivoTableros.FCMacro` |
| 25 | Conectar Luminarias a Octogonal Existente | Conectar | 25 | 1.1% | 2026-04-15 17:43 | `Conectar/Conectar_Luminarias_a_Octogonal_Existente.FCMacro` |

## Macros usadas recientemente

| Macro | Grupo | Usos | Ultimo uso |
|---|---|---:|---|
| Electrical_Schedule_Base | Tableros | 2 | 2026-07-07 08:30 |
| Exportar DXF/DWG (plano de trabajo) | Configuracion del proyecto | 15 | 2026-07-01 13:22 |
| Gestionar visibilidad ElectricCR | Configuracion del proyecto | 51 | 2026-07-01 12:44 |
| Colocar Luminarias Link | Iluminación | 51 | 2026-07-01 12:25 |
| Actualizar Iluminacion Completa | Iluminación | 17 | 2026-07-01 12:23 |
| Guia Iluminacion | Iluminación | 10 | 2026-07-01 12:16 |
| cambiar_altura_y_rotacion_objetos | Objetos | 5 | 2026-06-23 11:56 |
| RenombrarDiálogo | Objetos | 15 | 2026-06-23 11:56 |
| RectFromBoundaryLines | Areas | 100 | 2026-06-22 16:10 |
| cuenta_cuántos_objetos_están_seleccionados | Objetos | 1 | 2026-06-22 15:41 |
| AsignarNombreEstandar | Areas | 20 | 2026-06-22 15:17 |
| AbrirDirectorioElectricCR | Organizacion del proyecto | 1 | 2026-06-22 15:17 |
| Areas por click | Areas | 22 | 2026-06-22 14:52 |
| InsertarTomacorrientesenPoligonos_objeto_toma | Tomacorrientes | 14 | 2026-06-22 10:46 |
| Alinear | Objetos | 34 | 2026-06-15 14:21 |

## Lectura para la barra de herramientas

Grupos con mas uso acumulado:
- **Conectar**: 946 usos (43.0%).
- **Iluminación**: 278 usos (12.6%).
- **Configuracion del proyecto**: 261 usos (11.9%).
- **Cajas**: 185 usos (8.4%).
- **Areas**: 171 usos (7.8%).
- **Tomacorrientes**: 126 usos (5.7%).
- **Objetos**: 70 usos (3.2%).
- **Raiz**: 65 usos (3.0%).

Sugerencia practica: mantener barras visibles para los grupos con uso real alto o reciente, y dejar el resto en el panel de macros.

Recomendacion de barras visibles segun el registro:

- **Conectar**: visible, pero con cautela; parte del 43.0% viene de implementacion y pruebas de alimentadores.
- **Iluminacion**: alto uso y actividad reciente al 2026-07-01.
- **Cajas**: grupo especializado con uso alto.
- **Areas**: mantener visible; `RectFromBoundaryLines` tiene 100 usos que si representan importancia operativa.
- **Tomacorrientes**: uso medio; conviene mantenerlo si el trabajo diario lo requiere.
- **Configuracion del proyecto**: alto uso, pero mejor dejarlo en el panel salvo que se identifiquen 2-4 comandos realmente diarios.
- **Tableros**: bajo historico; visible durante trabajo de tableros o mover al panel si se quiere compactar mas.

## Herramientas heredadas Draft/BIM/Arch

El registro no muestra usos de comandos `BIM_` ni `Arch_`. Si se usaron, no quedaron registrados por este logger; con los datos actuales no hay evidencia para mantener una barra BIM heredada visible dentro de ElectricCR.

Si hay que rescatar herramientas heredadas, la señal fuerte esta en Draft:

| Herramienta | Usos | Ultimo uso |
|---|---:|---|
| Mover | 653 | 2026-06-12 11:28 |
| Select Group | 318 | 2026-05-05 10:50 |
| Linea | 224 | 2026-06-12 10:05 |
| Anadir a grupo | 204 | 2026-06-22 14:41 |
| Snap Endpoint | 138 | 2026-06-08 19:33 |
| Actualizacion | 100 | 2026-04-22 11:29 |
| Degradar | 98 | 2026-04-14 16:46 |
| Rectangulo | 85 | 2026-06-22 10:45 |
| Editar | 82 | 2026-03-28 14:04 |
| Snap Perpendicular | 81 | 2026-06-08 19:28 |

Decision recomendada: no heredar barras BIM completas. Si se necesita BIM, activar solo una mini barra BIM desde `show_bim_toolbar`. Para Draft, conviene una barra compacta de herramientas frecuentes o dejar Draft como workbench separado.

## Herramientas no macro mas usadas

Estas no son macros ElectricCR, pero explican parte del flujo de trabajo registrado.

| Herramienta | Usos | Ultimo uso |
|---|---:|---|
| Mover | 653 | 2026-06-12 11:28 |
| Select Group | 318 | 2026-05-05 10:50 |
| Línea | 224 | 2026-06-12 10:05 |
| Añadir a grupo | 204 | 2026-06-22 14:41 |
| Snap Endpoint | 138 | 2026-06-08 19:33 |
| Actualización | 100 | 2026-04-22 11:29 |
| Degradar | 98 | 2026-04-14 16:46 |
| Rectángulo | 85 | 2026-06-22 10:45 |
| Editar | 82 | 2026-03-28 14:04 |
| Snap Perpendicular | 81 | 2026-06-08 19:28 |
| Snap Midpoint | 74 | 2026-06-08 13:04 |
| Polilínea | 71 | 2026-03-25 22:01 |
| Punto | 60 | 2026-03-25 18:42 |
| Snap Lock | 58 | 2026-06-08 13:04 |
| Snap Ortho | 56 | 2026-06-08 19:27 |
