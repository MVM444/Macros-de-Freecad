# Descripciones de macros ElectricCR preparadas por GPT

Generado: 2026-08-12T18:52:43+00:00
Entradas: 192

Este archivo complementa `ElectricCR/data/macros_catalog.json`. La descripcion objetiva de una herramienta debe permanecer separada del comentario manual del usuario.

Confianza:
- **alta**: codigo o contexto tecnico revisado directamente;
- **media**: descripcion existente, herencia de una version activa o inferencia funcional razonable;
- **baja**: funcion aproximada que requiere revision posterior.

## Areas

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Areas por click | `Areas/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | alta | `codigo_revisado_gpt` |
| AsignarNombreEstandar | `Areas/AsignarNombreEstandar.FCMacro` | Muestra nombres de recinto definidos en la hoja NombresEstandar y aplica el nombre elegido a los objetos seleccionados; permite editar la lista y marca nombres ya utilizados. | alta | `codigo_revisado_gpt` |
| CrearMurosEntreEspacios | `Areas/CrearMurosEntreEspacios.FCMacro` | Detecta separaciones pequenas entre pares de objetos seleccionados mediante sus BoundBox y dibuja lineas Draft centrales entre ellos; sirve como referencia para divisiones o muros, pero no crea muros BIM. | alta | `codigo_revisado_gpt` |
| Guia Areas | `Areas/Guia_Areas.FCMacro` | Abre la guia operativa de la barra Areas y presenta el flujo recomendado para crear, corregir y nombrar recintos, con accesos a herramientas relacionadas. | alta | `codigo_revisado_gpt` |
| Poligono desde lineas limite | `Areas/PoligonoFromBoundaryLines.FCMacro` | Construye un poligono Draft cerrado de area a partir de aristas o lineas limite seleccionadas, aplicando tolerancias de snap y cierre. | alta | `codigo_revisado_gpt` |
| Poligonos de recintos desde muros BIM | `Areas/PoligonosRecintosDesdeArchWalls.FCMacro` | Crea areas poligonales independientes de recintos a partir de las huellas de muros Arch/BIM, conservando metadatos para su uso por ElectricCR. | alta | `catalogo_y_contexto_revisado_gpt` |
| RectFromBoundaryLines | `Areas/RectFromBoundaryLines.FCMacro` | Crea un rectangulo Draft desde aristas o caras seleccionadas de muros BIM. | media | `catalogo_existente` |
| RectFromLines | `Areas/RectFromLines.FCMacro` | Crea un rectangulo en Draft a partir de dos aristas lineales seleccionadas. | media | `catalogo_existente` |
| RectFromSelection | `Areas/RectFromSelection.FCMacro` | Crea un rectangulo en Draft a partir de una seleccion mixta. | media | `catalogo_existente` |
| Sustituir áreas por rectángulos nuevos | `Areas/SustituirAreasPorRectangulosNuevos.FCMacro` | Reemplaza la geometria de areas anteriores por rectangulos nuevos creados con RectFromBoundaryLines, conservando nombre, enlaces y metadatos del recinto y recalculando el area. | alta | `codigo_revisado_gpt` |

## Cajas

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Colocar Cajas Octogonales Mejor Ubicacion... | `Cajas/Colocar_Cajas_Octogonales_Mejor_Ubicacion.FCMacro` | Coloca una caja EMT octogonal por contenedor funcional en una posicion XY optima para los objetos seleccionados; permite altura SNPT y conexion EMT solida o flexible opcional. | alta | `codigo_revisado_gpt` |
| Colocar Cajas Octogonales entre Luminarias | `Cajas/Colocar_Cajas_Octogonales_Entre_Luminarias.FCMacro` | Agrupa luminarias por circuito y recinto, forma pares o clusters y coloca cajas EMT octogonales entre ellas; ademas genera conexiones 3D desde cada caja hacia sus luminarias. | alta | `codigo_revisado_gpt` |
| Colocar Cajas Octogonales sobre Dispositivos | `Cajas/Colocar_Cajas_Octogonales_Sobre_Dispositivos.FCMacro` | Coloca una caja EMT octogonal sobre cada tomacorriente o apagador, evita duplicados y la organiza en el circuito o contenedor correspondiente. | alta | `codigo_revisado_gpt` |
| Conectar Tomas a Cajas Octogonales Sobre Muro... | `Cajas/Conectar_Tomas_a_Cajas_Octogonales_Sobre_Muro.FCMacro` | Conecta cajas o puntos de tomacorriente con cajas EMT octogonales ubicadas sobre el muro, generando el recorrido de conexion correspondiente. | media | `catalogo_existente_normalizado` |
| Insertar Caja Octogonal en Grupo... | `Cajas/Insertar_Caja_Octogonal_En_Grupo.FCMacro` | Inserta una caja EMT octogonal en el grupo funcional relacionado con la seleccion actual. | alta | `catalogo_existente_normalizado` |
| Insertar Cajas Octogonales Encima... | `Cajas/Insertar_Cajas_Octogonales_Encima.FCMacro` | Inserta cajas EMT octogonales encima de los objetos seleccionados a una altura SNPT configurable y, opcionalmente, crea conexion EMT solida o flexible hacia cada objeto. | alta | `codigo_revisado_gpt` |
| Insertar Cajas Octogonales... | `Cajas/Insertar_Cajas_Octogonales.FCMacro` | Inserta cajas EMT octogonales como App::Link reutilizando el modelo maestro moderno de ElectricCR y sus puertos de conexion. | alta | `catalogo_existente_normalizado` |

## Conectar

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Ajustar Ruta... | `Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro` | Permite editar manualmente la ruta de un alimentador o ramal existente sin regenerar toda la red de conexiones. | alta | `catalogo_existente_normalizado` |
| Ajustar Ruta... | `Conectar/Backups/ruta_critica_seleccion_20260810/Ajustar_Alimentador_o_Ramal_Manual.FCMacro` | Permite editar manualmente la ruta de un alimentador o ramal existente sin regenerar toda la red de conexiones. | media | `heredada_de_version_activa` |
| Conectar Alimentadores... | `Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro` | Genera alimentadores ElectricCR desde circuitos o cajas de origen hacia el tablero asignado, usando el motor general de ruteo de alimentadores. | alta | `catalogo_y_contexto_revisado_gpt` |
| Conectar Circuito / Backbone... | `Conectar/Conectar_Octogonales_por_Circuito.FCMacro` | Genera el backbone o recorrido principal de un circuito conectando sus cajas octogonales con el motor general de conexiones ElectricCR. | alta | `catalogo_y_contexto_revisado_gpt` |
| Conectar Circuitos TCOM a Cara Superior del Tablero... | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero.FCMacro` | Alimentadores de TCOM-01..TCOM-05 hacia la cara superior real del tablero TCOM. | media | `catalogo_existente` |
| Conectar Circuitos TP a Cara Superior del Tablero... | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro` | Conecta los circuitos TP existentes con la cara superior real del tablero TP. | media | `catalogo_existente` |
| Conectar Luminarias a Octogonal Existente | `Conectar/Conectar_Luminarias_a_Octogonal_Existente.FCMacro` | Conecta una caja EMT octogonal existente con una o varias luminarias u objetos compatibles mediante una conexion EMT flexible por cada elemento. | alta | `catalogo_existente_normalizado` |
| Conectar Octogonales 45 (Diagonal) | `Conectar/Conectar_Octogonales_45.FCMacro` | Conecta cajas octogonales seleccionadas mediante tramos diagonales a 45 grados, generando una ruta de conexion entre sus posiciones. | media | `inferencia_nombre_gpt` |
| Conectar Octogonales Ortogonal por Circuito TCOM... | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Octogonales_Ortogonal_por_Circuito_TCOM.FCMacro` | Backbone EMT ortogonal para TCOM-01..TCOM-05, separado de la red TP. | media | `catalogo_existente` |
| Conectar Octogonales Ortogonal por Circuito TP... | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro` | Genera el backbone EMT interno de los circuitos TP. | media | `catalogo_existente` |
| Conectar circuito de tomas en plano 2D... | `Conectar/Conectar_Circuito_Tomas_Plano_2D.FCMacro` | Dibuja la representacion grafica 2D de un circuito de tomacorrientes para plantas ElectricCR. | alta | `catalogo_existente_normalizado` |
| Conectar desconectores al tablero asignado y actualizar tablas | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Desconectores_HVAC_a_TP.FCMacro` | Conectar desconectores ElectricCR al tablero que ya tienen asignado. | media | `catalogo_existente` |
| Conectar tableros y desconectores por cara superior | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Tableros_Cara_Superior.FCMacro` | Conecta tableros y desconectores utilizando como punto de llegada la cara superior real de cada equipo. | media | `catalogo_contextual_gpt` |
| ConectarObjetosdeunGrupo | `Conectar/ConectarObjetosdeunGrupo.FCMacro` | Conecta consecutivamente los objetos conectables de un grupo, ordenados por su Label, mediante segmentos Draft Wire directos y guarda las conexiones en el grupo Conexiones correspondiente. | alta | `codigo_revisado_gpt` |
| ConectarObjetosÁrbol | `Conectar/ConectarObjetosÁrbol.FCMacro` | Conecta consecutivamente los objetos numerados de un grupo siguiendo el orden de sus Labels y crea rutas Draft ortogonales entre sus posiciones. | alta | `codigo_revisado_gpt` |
| ConectarObjetosÁrbol-WIRE | `Conectar/ConectarObjetosÁrbol-WIRE.FCMacro` | Variante de conexion por arbol que une consecutivamente objetos numerados de un grupo con Draft Wire ortogonales y los organiza en el grupo Conexiones. | alta | `codigo_revisado_gpt` |
| ConectarTomasOrdenados | `Conectar/ConectarTomasOrdenados.FCMacro` | Ordena los tomacorrientes de un grupo por su etiqueta y crea una unica ruta Draft Wire ortogonal continua que los conecta en ese orden. | alta | `codigo_revisado_gpt` |
| ConectarTomasSnake | `Conectar/ConectarTomasSnake.FCMacro` | Conecta tomacorrientes, vertices, bordes o caras seleccionados mediante una ruta Draft Wire ortogonal tipo snake, con radio de redondeo y soporte de orientacion respecto a pared. | alta | `codigo_revisado_gpt` |
| Conectar_objetos_en_C | `Conectar/Conectar_objetos_en_C.FCMacro` | Conecta objetos seleccionados mediante una ruta ortogonal con forma de C, agregando puntos intermedios para mantener la geometria del recorrido. | media | `inferencia_nombre_gpt` |
| Crear Conector Flexible (Spline) | `Conectar/crear_conector_flexible.FCMacro` | Crea una conexion flexible tipo spline entre referencias seleccionadas para representar tuberia o enlace flexible. | media | `catalogo_existente_normalizado` |
| Normalizar grupos Conexiones | `Conectar/Normalizar_Grupos_Conexiones.FCMacro` | Revisa y normaliza la ubicacion de objetos de conexion dentro de la jerarquia ElectricCR, consolidandolos en los grupos Conexiones correspondientes. | media | `inferencia_nombre_gpt` |
| Panel Conexiones Endpoints (Beta) | `Conectar/Panel_Conexiones_Endpoints.FCMacro` | Abre un panel beta para revisar y gestionar los extremos de conexiones ElectricCR, facilitando la inspeccion de origen, destino y puntos de enlace. | media | `inferencia_nombre_gpt` |
| Preparar red TCOM completa | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Preparar_Red_TCOM_Completa.FCMacro` | Crea alimentadores y ramales TCOM y colorea los tomas de computo. | media | `catalogo_existente` |
| Preparar red completa de iluminación | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Preparar_Red_Iluminacion_Completa.FCMacro` | Orquesta cajas, ramales y alimentadores para circuitos de iluminacion. | media | `catalogo_existente` |
| Preparar red completa de iluminación | `Conectar/Preparar_Red_Iluminacion_Completa.FCMacro` | Orquesta la preparacion completa de una red de iluminacion, incluyendo cajas, ramales y alimentadores de sus circuitos. | alta | `catalogo_existente_normalizado` |
| Ruta critica circuito por circuito | `Conectar/RutaCritica_CircuitoPorCircuito.FCMacro` | Genera o analiza la ruta critica de los circuitos de manera individual, procesando cada circuito por separado para obtener su recorrido principal. | media | `contexto_revisado_gpt` |
| Ruta critica solo seleccionados | `Conectar/Backups/ruta_critica_seleccion_20260810/RutaCritica_Seleccionados.FCMacro` | Calcula y dibuja una ruta critica usando solamente los objetos o subelementos seleccionados, permitiendo definir el recorrido a partir de la seleccion actual. | media | `heredada_de_version_activa` |
| Ruta critica solo seleccionados | `Conectar/RutaCritica_Seleccionados.FCMacro` | Calcula y dibuja una ruta critica usando solamente los objetos o subelementos seleccionados, permitiendo definir el recorrido a partir de la seleccion actual. | alta | `contexto_revisado_gpt` |
| [ACTIVA] Ajustar Alimentador o Ramal Manual | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Ajustar_Alimentador_o_Ramal_Manual.FCMacro` | Permite editar manualmente la ruta de un alimentador o ramal existente sin regenerar toda la red de conexiones. | media | `heredada_de_version_activa` |
| [ACTIVA] Conectar Alimentadores a Tablero | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Alimentadores_a_Tablero_Auto.FCMacro` | Genera alimentadores ElectricCR desde circuitos o cajas de origen hacia el tablero asignado, usando el motor general de ruteo de alimentadores. | media | `heredada_de_version_activa` |
| [ACTIVA] Conectar Circuitos Luminarias | `Conectar/Conectar_Circuitos_Luminarias_Auto.FCMacro` | Conecta automaticamente los circuitos de iluminacion utilizando la estructura y metadatos ElectricCR para generar sus recorridos y conexiones. | media | `contexto_revisado_gpt` |
| [ACTIVA] Conectar Circuitos Ramales | `Conectar/Conectar_Circuitos_Ramales_Auto.FCMacro` | Genera automaticamente conexiones de ramales para circuitos ElectricCR, enlazando las cargas o cajas correspondientes segun la informacion del circuito. | media | `contexto_revisado_gpt` |
| [ACTIVA] Conectar objetos en L | `Conectar/Conectar_objetos_en_L.FCMacro` | Conecta objetos seleccionados mediante una ruta ortogonal en forma de L, utilizando puntos intermedios segun su posicion. | media | `inferencia_nombre_gpt` |
| [ACTIVA] Proponer Rutas Guia (Auto) | `Conectar/Proponer_Rutas_Guia_Auto.FCMacro` | Propone automaticamente lineas o rutas guia para orientar el trazado de conexiones ElectricCR sin impedir el ruteo cuando no existe una guia. | media | `contexto_revisado_gpt` |
| [ACTIVA] Sustituir Conexion EMT por Linea | `Conectar/Sustituir_Conexion_EMT_por_Linea.FCMacro` | Sustituye una conexion EMT seleccionada por una representacion lineal mas simple, conservando el recorrido como referencia grafica. | media | `contexto_revisado_gpt` |
| [LEGACY] Conectar Cajas y Alimentadores a Tablero (v1) | `Conectar/Backups/consolidacion_conexiones_20260808/Conectar/Conectar_Cajas_a_Tablero_Auto.FCMacro` | Conecta automaticamente circuitos de tomacorrientes/apagadores hacia cajas octogonales y al tablero (u objeto ancla) seleccionado. | media | `catalogo_existente` |
| conectar_objetos_en_eSe | `Conectar/conectar_objetos_en_eSe.FCMacro` | Conecta objetos seleccionados mediante un recorrido ortogonal con forma de S, creando puntos intermedios para evitar un enlace directo. | media | `inferencia_nombre_gpt` |
| conectar_objetos_por_bordes | `Conectar/conectar_objetos_por_bordes.FCMacro` | Conecta objetos o subelementos seleccionados tomando como referencia sus bordes para construir la ruta de conexion. | media | `inferencia_nombre_gpt` |
| conectar_objetos_por_bordes_WIRE | `Conectar/conectar_objetos_por_bordes_WIRE.FCMacro` | Variante que conecta objetos o subelementos por sus bordes y materializa el recorrido como Draft Wire. | media | `inferencia_nombre_gpt` |
| conectar_puntos_seleccionados | `Conectar/conectar_puntos_seleccionados.FCMacro` | Crea una conexion entre puntos o vertices seleccionados, usando la seleccion de subelementos como extremos del recorrido. | media | `inferencia_nombre_gpt` |
| crear_conector | `Conectar/crear_conector.FCMacro` | Crea un objeto de conexion entre elementos seleccionados para representar un enlace electrico dentro del modelo. | baja | `inferencia_nombre_gpt` |
| medir_distancia_y_dibujar_ruta | `Conectar/medir_distancia_y_dibujar_ruta.FCMacro` | Mide la distancia entre referencias seleccionadas y dibuja una ruta de conexion asociada al recorrido medido. | media | `inferencia_nombre_gpt` |
| medir_distancia_y_dibujar_ruta_independiente | `Conectar/medir_distancia_y_dibujar_ruta_independiente.FCMacro` | Variante independiente que mide la distancia entre referencias y dibuja una ruta sin depender de la organizacion electrica principal del documento. | media | `inferencia_nombre_gpt` |

## Conectar Legacy

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Conectar Circuitos TCOM a Cara Superior del Tablero (Legacy) | `Conectar/Conectar_Circuitos_TCOM_a_Cara_Superior_Tablero.FCMacro` | Wrapper compatible TCOM del motor general ElectricCR. | media | `catalogo_existente` |
| Conectar Circuitos TP a Cara Superior del Tablero (Legacy) | `Conectar/Conectar_Circuitos_TP_a_Cara_Superior_Tablero.FCMacro` | Wrapper compatible TP del motor general ElectricCR. | media | `catalogo_existente` |
| Conectar Octogonales por Circuito TCOM (Legacy) | `Conectar/Conectar_Octogonales_Ortogonal_por_Circuito_TCOM.FCMacro` | Wrapper TCOM del backbone general ElectricCR. Revision: 2026-08-08. | media | `catalogo_existente` |
| Conectar Octogonales por Circuito TP (Legacy) | `Conectar/Conectar_Octogonales_Ortogonal_por_Circuito_TP.FCMacro` | Wrapper TP del backbone general ElectricCR. Revision: 2026-08-08. | media | `catalogo_existente` |
| Conectar desconectores asignados (Legacy) | `Conectar/Conectar_Desconectores_HVAC_a_TP.FCMacro` | Wrapper historico para desconectores HVAC y otros servicios. | media | `catalogo_existente` |
| Conectar tableros y equipos por cara superior (Legacy) | `Conectar/Conectar_Tableros_Cara_Superior.FCMacro` | Wrapper tablero/equipo -> tablero aguas arriba. | media | `catalogo_existente` |
| Preparar red TCOM completa (Legacy) | `Conectar/Preparar_Red_TCOM_Completa.FCMacro` | Orquestador TCOM basado en los motores generales ElectricCR. | media | `catalogo_existente` |
| [LEGACY] Conectar Cajas y Alimentadores a Tablero (v1) | `Conectar/Conectar_Cajas_a_Tablero_Auto.FCMacro` | Conecta automaticamente circuitos de tomacorrientes/apagadores hacia cajas octogonales y al tablero (u objeto ancla) seleccionado. | media | `catalogo_existente` |

## Configuracion del proyecto

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Asignar tableros y circuitos (pestanas) | `Configuracion del proyecto/Asignar_Tableros_y_Circuitos.FCMacro` | Permite asignar circuitos y cargas a cada tablero mediante pestanas y definir el origen de tableros, desconectores e interruptores; genera las hojas Asignacion_Red y Red_Origenes. | alta | `codigo_revisado_gpt` |
| Calculo de circuitos por tablero | `Configuracion del proyecto/Calculo_Circuitos_PanelSchedule.FCMacro` | Calcula y organiza la informacion de circuitos por tablero para producir o actualizar el panel schedule electrico con los datos disponibles del proyecto. | media | `contexto_revisado_gpt` |
| Compactar proyecto ElectricCR | `Configuracion del proyecto/Compactar_Proyecto_ElectricCR.FCMacro` | Reduce peso y tiempo de recompute del FCStd: puede desactivar AutoUpdate en Shape2DView ocultas, convertir Draft Clones a App::Link y deduplicar FeaturePython legacy repetidos por hash de Shape. | alta | `codigo_revisado_gpt` |
| Crear arbol proyecto electrico | `Configuracion del proyecto/Crear_Arbol_Proyecto_Electrico.FCMacro` | Crea de forma idempotente la estructura estandar de grupos para un proyecto ElectricCR, evitando duplicar grupos al volver a ejecutarla. | alta | `catalogo_existente_normalizado` |
| Gestionar visibilidad ElectricCR | `Configuracion del proyecto/Gestionar_Visibilidad_ElectricCR.FCMacro` | Panel de visibilidad por categorias para proyectos ElectricCR; permite mostrar, ocultar o aislar sistemas y controlar el modo visual 2D/3D de dispositivos. | alta | `codigo_revisado_gpt` |
| Gestionar_Registro_Electrico | `Configuracion del proyecto/Gestionar_Registro_Electrico.FCMacro` | Abre la herramienta de gestion del registro electrico utilizado por ElectricCR para consultar o mantener tipos y datos de componentes. | media | `inferencia_nombre_gpt` |
| Mover Seleccion a Circuito... | `Configuracion del proyecto/Mover_Seleccion_a_Circuito.FCMacro` | Mueve los objetos seleccionados al grupo de un circuito ElectricCR elegido, facilitando la organizacion manual del arbol electrico. | alta | `inferencia_nombre_gpt` |
| Mover Seleccion a Grupo... | `Configuracion del proyecto/Mover_Seleccion_a_Grupo.FCMacro` | Mueve los objetos seleccionados a un grupo del documento elegido por el usuario, sin recrear la geometria. | alta | `inferencia_nombre_gpt` |
| Multirenombrar | `Configuracion del proyecto/Multirenombrar_ElectricCR.FCMacro` | Permite renombrar en lote varios objetos ElectricCR mediante una interfaz de edicion de nombres y criterios comunes. | media | `inferencia_nombre_gpt` |
| Ordenar arbol electrico (auto) | `Configuracion del proyecto/Ordenar_Arbol_Electrico_Auto.FCMacro` | Ordena automaticamente el arbol de grupos del documento aplicando la prioridad y jerarquia electrica definida por ElectricCR. | alta | `catalogo_existente_normalizado` |
| Ordenar grupos | `Configuracion del proyecto/Ordenar_Grupos_ElectricCR.FCMacro` | Reordena los grupos ElectricCR del documento para mantener una estructura de arbol consistente y mas legible. | media | `inferencia_nombre_gpt` |
| Organizar documento electrico | `Configuracion del proyecto/Organizar_Documento_Electrico.FCMacro` | Reorganiza objetos electricos en una jerarquia canonica de ElectricCR, por ejemplo luminarias por circuito, recinto y apagador y sensores por zona, moviendo los objetos reales a sus grupos correspondientes. | alta | `codigo_revisado_gpt` |
| Registrar acometida y ruta | `Configuracion del proyecto/Backups/legibilidad_acometida_20260810/Registrar_Acometida_y_Ruta.FCMacro` | Registra datos de acometida, calcula corriente nominal y de diseno, breaker y conductor recomendados, crea o actualiza la ruta entre medidor y tablero principal y guarda historial en la hoja Acometida. | media | `heredada_de_version_activa` |
| Registrar acometida y ruta | `Configuracion del proyecto/Registrar_Acometida_y_Ruta.FCMacro` | Registra datos de acometida, calcula corriente nominal y de diseno, breaker y conductor recomendados, crea o actualiza la ruta entre medidor y tablero principal y guarda historial en la hoja Acometida. | alta | `codigo_revisado_gpt` |

## Deteccion

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Sensores de humo en poligonos (NFPA) | `Deteccion/ColocarDetectores_Poligonos_NFPA.FCMacro` | Distribuye detectores de humo sobre recintos poligonales aplicando criterios de separacion y cobertura del flujo NFPA de ElectricCR. | alta | `catalogo_y_contexto_revisado_gpt` |
| Sensores de humo en rectangulos (NFPA) | `Deteccion/ColocarDetectores_NFPA.FCMacro` | Distribuye detectores de humo sobre areas rectangulares aplicando criterios de separacion y cobertura definidos para el flujo NFPA de ElectricCR. | alta | `contexto_revisado_gpt` |

## GameEngineExport

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| AplicarEmissiveColor | `GameEngineExport/AplicarEmissiveColor.FCMacro` | Aplica propiedades de color emisivo a objetos o materiales seleccionados para que las superficies luminosas se exporten con apariencia de emision en motores 3D. | media | `inferencia_nombre_gpt` |
| CombinarLucesEdificio | `GameEngineExport/CombinarLucesEdificio.FCMacro` | Combina la informacion de luces del edificio en una estructura o archivo comun para su posterior exportacion al flujo GameEngineExport. | media | `inferencia_nombre_gpt` |
| Combinarconarchivoluces | `GameEngineExport/Combinarconarchivoluces.FCMacro` | Combina la exportacion del modelo con un archivo de luces existente para integrar geometria e iluminacion en el flujo hacia el motor 3D. | baja | `inferencia_nombre_gpt` |
| ExportarLucesX3D | `GameEngineExport/ExportarLucesX3D.FCMacro` | Exporta las luces del documento a una representacion X3D para utilizarlas junto con el modelo en un motor grafico o visor compatible. | media | `inferencia_nombre_gpt` |
| GameEngineExport | `GameEngineExport/GameEngineExport.FCMacro` | Prepara y exporta elementos del documento FreeCAD para su uso en un motor grafico, integrando geometria y datos auxiliares del flujo GameEngineExport. | media | `inferencia_contextual_gpt` |
| GameEngineExport Copy 4 | `GameEngineExport/GameEngineExport Copy 4.FCMacro` | Copia historica de la macro GameEngineExport utilizada para preparar y exportar contenido de FreeCAD hacia un motor grafico. | media | `heredada_de_version_activa` |
| GameEngineExport copy | `GameEngineExport/GameEngineExport copy.FCMacro` | Copia historica de GameEngineExport para preparar y exportar contenido de FreeCAD hacia un motor grafico. | media | `heredada_de_version_activa` |
| GameEngineExport copy 2 | `GameEngineExport/GameEngineExport copy 2.FCMacro` | Copia historica de GameEngineExport para preparar y exportar contenido de FreeCAD hacia un motor grafico. | media | `heredada_de_version_activa` |
| GameEngineExport copy 3 | `GameEngineExport/GameEngineExport copy 3.FCMacro` | Copia historica de la macro GameEngineExport utilizada para preparar y exportar contenido de FreeCAD hacia un motor grafico. | media | `heredada_de_version_activa` |
| export_selection_via_gui_x3d | `GameEngineExport/export_selection_via_gui_x3d.FCMacro` | Exporta la seleccion actual mediante el flujo GUI de FreeCAD al formato X3D. | alta | `inferencia_nombre_gpt` |

## GameEngineExportWB

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| AgregarPuertasVentanasBIM_QuickExample | `GameEngineExportWB/macros/AgregarPuertasVentanasBIM_QuickExample.FCMacro` | Agregar puertas y ventanas BIM al Quick Example de GameEngineExportWB. | media | `catalogo_existente` |
| AgregarTechoBIM_QuickExample | `GameEngineExportWB/macros/AgregarTechoBIM_QuickExample.FCMacro` | Agregar techo sencillo al ultimo Quick Example de GameEngineExportWB. | media | `catalogo_existente` |
| CrearPuertasBIMDesdeSketch | `GameEngineExportWB/macros/CrearPuertasBIMDesdeSketch.FCMacro` | Crear puertas BIM desde el sketch seleccionado. | media | `catalogo_existente` |
| CrearVentanasBIMDesdeSketch | `GameEngineExportWB/macros/CrearVentanasBIMDesdeSketch.FCMacro` | Crear ventanas BIM desde el sketch seleccionado. | media | `catalogo_existente` |

## Iluminación

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Actualizar Iluminacion Completa | `Iluminación/Actualizar_Iluminacion_Completa.FCMacro` | Actualiza el calculo integral de iluminacion por recinto: clasifica el uso del espacio, calcula cantidad minima de luminarias y filas/columnas, conserva ajustes manuales cuando corresponde y sincroniza DatosRecintos, tabla legacy y etiquetas. | alta | `codigo_revisado_gpt` |
| Asignar Tipo de Luminaria a Areas | `Iluminación/Asignar_Tipo_Luminaria_Areas.FCMacro` | Asigna a las areas seleccionadas un tipo de luminaria del registro ElectricCR y guarda clave, lumenes, potencia, CCT y altura de montaje para calculos y colocacion automatica. | alta | `codigo_revisado_gpt` |
| Asignar luminarias a apagadores | `Iluminación/Asignar_Luminarias_Apagadores.FCMacro` | Asigna luminarias a uno o dos apagadores y registra la relacion de control, incluyendo la indicacion grafica del tipo en planta. | alta | `catalogo_existente_normalizado` |
| Asignar luminarias a circuitos | `Iluminación/Asignar_Luminarias_Circuitos.FCMacro` | Asigna luminarias a circuitos ElectricCR sin moverlas ni duplicarlas en el arbol del documento. | alta | `catalogo_existente_normalizado` |
| Asistente CSV eléctrico | `Iluminación/AsisCSV2Pasos.FCMacro` | Asistente en dos pasos para trabajar con datos electricos en CSV dentro del flujo de iluminacion, guiando la preparacion e intercambio de la informacion. | baja | `inferencia_nombre_gpt` |
| Colocar Luminarias Link | `Iluminación/Backups/altura_link_20260810/ColocarLuminarias_Link.FCMacro` | Coloca luminarias como App::Link dentro de areas rectangulares segun la rejilla Rows/Columns y el tipo registrado; distribuye las instancias por celdas y evita usar clones. | media | `heredada_de_version_activa` |
| Colocar Luminarias Link | `Iluminación/ColocarLuminarias_Link.FCMacro` | Coloca luminarias como App::Link dentro de areas rectangulares segun la rejilla Rows/Columns y el tipo registrado; distribuye las instancias por celdas y evita usar clones. | alta | `codigo_revisado_gpt` |
| Colocar Luminarias Objeto | `Iluminación/ColocarLuminarias_Objeto.FCMacro` | Coloca objetos de luminaria dentro de areas rectangulares segun su rejilla de filas y columnas, utilizando el tipo y parametros de iluminacion asignados. | media | `contexto_revisado_gpt` |
| Colocar apagadores junto a puertas BIM | `Iluminación/ColocarApagadoresEnPuertas.FCMacro` | Coloca apagadores junto a puertas BIM o aberturas sin hoja, usando la geometria de acceso como referencia. | alta | `catalogo_existente_normalizado` |
| Crear apagadores en sketch | `Iluminación/ColocarApagadores_Sketch.FCMacro` | Crea o coloca apagadores usando geometria de Sketch como referencia para su posicion en el proyecto. | media | `inferencia_nombre_gpt` |
| Guia Iluminacion | `Iluminación/Guia_Iluminacion.FCMacro` | Muestra la guia operativa de la barra Iluminacion y el flujo recomendado para calcular, colocar, asignar y organizar luminarias y apagadores. | media | `contexto_revisado_gpt` |
| Hoja Iluminacion | `Iluminación/Hoja_Iluminación.FCMacro` | Crea o actualiza la hoja de calculo de iluminacion del proyecto con la informacion de recintos, luminarias y parametros usados por ElectricCR. | media | `contexto_revisado_gpt` |
| Luminaria Link Sketch | `Iluminación/Luminaria_Link_Sketch.FCMacro` | Crea o coloca una luminaria como App::Link usando una referencia de Sketch para definir su posicion u orientacion. | media | `inferencia_nombre_gpt` |
| Organizar luminarias por Areas | `Iluminación/Organizar_Luminarias_por_Circuito_y_Apagador.FCMacro` | Organiza las luminarias en el arbol ElectricCR segun su circuito y el apagador que las controla, manteniendo la relacion funcional entre ambos. | alta | `contexto_revisado_gpt` |
| Recalcular Distribucion de Luminarias | `Iluminación/Recalcular_Distribucion_Luminarias_Areas.FCMacro` | Recalcula la distribucion de luminarias de las areas, actualizando filas y columnas a partir de la cantidad requerida y los parametros de cada recinto. | alta | `contexto_revisado_gpt` |
| Reemplazar_Luminaria | `Iluminación/Reemplazar_Luminaria.FCMacro` | Reemplaza uno o varios objetos de luminaria seleccionados por otro modelo 3D manteniendo su posicion y rotacion. | alta | `catalogo_existente_normalizado` |

## Importar y Exportar

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Contar tomacorrientes y exportar | `Tomacorrientes/contar_tomacorrientes_y_exportar.FCMacro` | Cuenta los tomacorrientes del proyecto o seleccion y exporta el resultado a un archivo o tabla para su revision externa. | media | `inferencia_nombre_gpt` |
| Exportar DXF/DWG (plano de trabajo) | `Configuracion del proyecto/Exportar_DXF_DWG_Plano_Trabajo.FCMacro` | Exporta el plano de trabajo del documento a DXF o DWG para intercambio con aplicaciones CAD externas. | alta | `inferencia_nombre_gpt` |
| Exportar Imagen de Planta | `Configuracion del proyecto/Exportar_Imagen_Planta.FCMacro` | Exporta una vista ortografica de planta del documento en PNG o JPEG de alta resolucion. | alta | `catalogo_existente_normalizado` |
| Exportar Luminarias CSV | `Iluminación/Exportar_Luminarias_CSV_ElectricCR.FCMacro` | Exporta a CSV la informacion de luminarias ElectricCR para intercambio o procesamiento externo. | alta | `inferencia_nombre_gpt` |
| Exportar spreadsheets a Excel | `Configuracion del proyecto/Exportar_Spreadsheets_a_Excel.FCMacro` | Exporta las hojas Spreadsheet del documento FreeCAD a un archivo Excel para consulta o procesamiento externo. | alta | `inferencia_nombre_gpt` |
| calcular_area_y_exportar_a_spreadsheet | `Areas/calcular_area_y_exportar_a_spreadsheet.FCMacro` | Calcula el area de los objetos o recintos seleccionados y registra los resultados en una hoja Spreadsheet de FreeCAD. | media | `inferencia_nombre_gpt` |

## Macros

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| MEPWorkbenchCR_Extraer_HVAC_CAD | `MEPWorkbenchCR_Extraer_HVAC_CAD.FCMacro` | Extrae o prepara informacion de elementos HVAC del modelo para un flujo CAD asociado a MEPWorkbenchCR. | baja | `inferencia_nombre_gpt` |

## MEPWorkbenchCR

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| MEPWorkbenchCRLoader | `MEPWorkbenchCR/MEPWorkbenchCRLoader.FCMacro` | Carga o registra MEPWorkbenchCR en la sesion de FreeCAD para disponer de sus comandos y herramientas. | alta | `inferencia_nombre_gpt` |
| MEPWorkbenchCR_CleanHVAC | `MEPWorkbenchCR/MEPWorkbenchCR_CleanHVAC.FCMacro` | Limpia o normaliza elementos HVAC del documento para prepararlos para el flujo de MEPWorkbenchCR. | media | `inferencia_nombre_gpt` |

## Objetos

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Alinear | `Objetos/Alinear.FCMacro` | Alinea los objetos seleccionados respecto al primero usando sus BoundBox, con opciones izquierda, derecha o centro en X; arriba, abajo o centro en Y; y frente, atras o centro en Z. | alta | `codigo_revisado_gpt` |
| BorrarCadena | `Objetos/BorrarCadena.FCMacro` | Renombra los objetos seleccionados eliminando de sus Label una cadena de texto indicada por el usuario; evita aplicar un nombre que ya este usado. | alta | `codigo_revisado_gpt` |
| Cambiar altura y rotacion de objetos | `Objetos/cambiar_altura_y_rotacion_objetos.FCMacro` | Permite modificar de forma conjunta la altura y la rotacion de los objetos seleccionados mediante un dialogo. | alta | `inferencia_nombre_gpt` |
| ContarObjetos | `Objetos/ContarObjetos.FCMacro` | Cuenta objetos del documento o de la seleccion segun los criterios implementados y muestra el resultado al usuario. | media | `inferencia_nombre_gpt` |
| Copiar Formato Electrico | `Objetos/Copiar_Formato_Electrico.FCMacro` | Copia propiedades electricas y estilo visual de un objeto plantilla a otros seleccionados, incluyendo circuito, canalizacion, LinkKind y metadatos comunes; puede reubicarlos en el subgrupo Alimentador o Ramal correspondiente. | alta | `codigo_revisado_gpt` |
| Fix_Link_Transform_FreeCAD | `Objetos/Fix_Link_Transform_FreeCAD.FCMacro` | Diagnostica App::Link cuyo Transform o Placement no funciona y los normaliza activando LinkTransform y desbloqueando Placement; puede agrupar enlaces problematicos en REVISAR_LINKS. | alta | `codigo_revisado_gpt` |
| Habilitar Transform en links de dispositivos | `Objetos/Habilitar_Transform_en_Links_Dispositivos.FCMacro` | Habilita o normaliza la transformacion de App::Link que representan dispositivos ElectricCR como tomas, apagadores, luminarias, sensores, rociadores, altavoces y camaras. | alta | `contexto_revisado_gpt` |
| Insertar_Dispositivo | `Objetos/Insertar_Dispositivo.FCMacro` | Selector generico de dispositivos ElectricCR que crea una instancia del tipo elegido a partir del registro de componentes. | alta | `catalogo_existente_normalizado` |
| RenombrarDiálogo | `Objetos/RenombrarDiálogo.FCMacro` | Abre un dialogo para cambiar el nombre visible de uno o varios objetos seleccionados. | alta | `inferencia_nombre_gpt` |
| Resolve Link From Selection | `Objetos/Resolve_Link_From_Selection.FCMacro` | Resuelve una seleccion asociada a un App::Link para identificar el enlace y su objeto vinculado, facilitando operaciones sobre instancias enlazadas. | media | `inferencia_nombre_gpt` |
| Rotar90 | `Objetos/Rotar90.FCMacro` | Rota 90 grados los objetos seleccionados alrededor del eje definido por la macro, como ajuste rapido de orientacion. | media | `inferencia_nombre_gpt` |
| cuenta_cuántos_objetos_están_seleccionados | `Objetos/cuenta_cuántos_objetos_están_seleccionados.FCMacro` | Cuenta cuantos objetos estan seleccionados actualmente en FreeCAD y muestra el total. | alta | `inferencia_nombre_gpt` |

## Respaldos

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Actualizar Iluminacion Completa | `Respaldos/Iluminacion_Completa_Panel_20260610_085902/Actualizar_Iluminacion_Completa.FCMacro` | Actualiza el calculo integral de iluminacion por recinto: clasifica el uso del espacio, calcula cantidad minima de luminarias y filas/columnas, conserva ajustes manuales cuando corresponde y sincroniza DatosRecintos, tabla legacy y etiquetas. | media | `heredada_de_version_activa` |
| Actualizar Iluminacion Completa | `Respaldos/Iluminacion_Pasillos_Toolbar_20260610_091937/Actualizar_Iluminacion_Completa.FCMacro` | Actualiza el calculo integral de iluminacion por recinto: clasifica el uso del espacio, calcula cantidad minima de luminarias y filas/columnas, conserva ajustes manuales cuando corresponde y sincroniza DatosRecintos, tabla legacy y etiquetas. | media | `heredada_de_version_activa` |
| Actualizar Tabla Iluminacion | `Respaldos/Iluminacion_20260608_175346/Actualizar_Tabla_Iluminacion.FCMacro` | Actualiza la tabla de iluminacion a partir de los datos disponibles de recintos y luminarias; corresponde a una version historica del flujo de iluminacion. | media | `inferencia_contextual_gpt` |
| Actualizar Tabla Iluminacion | `Respaldos/Iluminacion_Archivadas_20260610_092800/Actualizar_Tabla_Iluminacion.FCMacro` | Actualiza la tabla de iluminacion a partir de los datos disponibles de recintos y luminarias; corresponde a una version historica del flujo de iluminacion. | media | `inferencia_contextual_gpt` |
| Areas por click | `Respaldos/Areas_AreaPorClick_20260608_093836/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_boton_rectangulos_20260608_133939/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_calco_working_20260608_112151/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_compacta_20260608_094731/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_inestable_20260608_120520/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_linea_auxiliar_20260608_121126/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_multiradar_shallow_20260608_114146/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_radar_iterativo_20260608_120315/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_radar_working_20260608_102533/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_raster_failed_20260608_100412/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_rect_auto_boundary_20260608_135618/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_AreaPorClick_vector_open_failed_20260608_095609/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| Areas por click | `Respaldos/Areas_PoligonoFromBoundaryLines_20260608_122238/AreaPorClick.FCMacro` | Crea poligonos de recintos haciendo clic dentro de zonas delimitadas; detecta los limites cercanos y genera la geometria del area. | media | `heredada_de_version_activa` |
| AsignarNombreEstandar | `Respaldos/Areas_AsignarNombreEstandar_grupo_hojas_20260622_163722/AsignarNombreEstandar.FCMacro` | Muestra nombres de recinto definidos en la hoja NombresEstandar y aplica el nombre elegido a los objetos seleccionados; permite editar la lista y marca nombres ya utilizados. | media | `heredada_de_version_activa` |
| AsignarNombreEstandar | `Respaldos/Areas_AsignarNombreEstandar_pyside_20260608_142311/AsignarNombreEstandar.FCMacro` | Muestra nombres de recinto definidos en la hoja NombresEstandar y aplica el nombre elegido a los objetos seleccionados; permite editar la lista y marca nombres ya utilizados. | media | `heredada_de_version_activa` |
| AsignarNombreEstandar | `Respaldos/Areas_AsignarNombreEstandar_refresh_20260608_173932/AsignarNombreEstandar.FCMacro` | Muestra nombres de recinto definidos en la hoja NombresEstandar y aplica el nombre elegido a los objetos seleccionados; permite editar la lista y marca nombres ya utilizados. | media | `heredada_de_version_activa` |
| ColocarLuminarias | `Respaldos/Iluminacion_legacy_20260324/ColocarLuminarias.FCMacro` | Version historica para colocar luminarias en recintos segun la distribucion calculada antes de la migracion al flujo moderno con App::Link. | media | `inferencia_contextual_gpt` |
| Electric_Principal | `Respaldos/Reorganizacion_raiz_20260622_095139/Electric_Principal.FCMacro` | Electric_Principal.FCMacro Descripcion (sin acentos): - ObjetoElectromecanico (FeaturePython + GroupExtension) con BasePlacement - Prototipos unicos importados desde Resources: * Toma_2d.step -> ProtoToma2D (Part::Feature unico) * Toma_3d.step -> ProtoToma3D (Part::Feature unico) - Consolidacion del STEP: se crea un solo Part::Feature por proto * 3D: compound de todos los solids (o faces si no hay solids) * 2D: compound de shapes (edges/faces) planos * se ocultan en arbol y se ubican en electrico/_lib * no se reimporta si ya existen protos validos - Instancias: padre + dos App::Link que apuntan a los protos - execute-only: onChanged solo touch; transforms/visibilidad en execute() - AlturaRel solo mueve el Link3D en Z local - Logs [ELEC] | media | `catalogo_existente` |
| Etiquetas | `Respaldos/Iluminacion_Archivadas_20260610_092800/Etiquetas.FCMacro` | Version historica para crear o actualizar etiquetas asociadas a la informacion de iluminacion del proyecto. | media | `inferencia_contextual_gpt` |
| Etiquetas | `Respaldos/Iluminacion_Etiquetas_20260608_181721/Etiquetas.FCMacro` | Version historica para crear o actualizar etiquetas asociadas a la informacion de iluminacion del proyecto. | media | `inferencia_contextual_gpt` |
| Guia Iluminacion | `Respaldos/Iluminacion_Guia_Contraste_20260610_105126/Guia_Iluminacion.FCMacro` | Muestra la guia operativa de la barra Iluminacion y el flujo recomendado para calcular, colocar, asignar y organizar luminarias y apagadores. | media | `heredada_de_version_activa` |
| Guia Iluminacion | `Respaldos/Iluminacion_Guia_Mejorada_20260610_100837/Guia_Iluminacion.FCMacro` | Muestra la guia operativa de la barra Iluminacion y el flujo recomendado para calcular, colocar, asignar y organizar luminarias y apagadores. | media | `heredada_de_version_activa` |
| Guia Iluminacion | `Respaldos/Iluminacion_Guia_Operativa_20260610_101800/Guia_Iluminacion.FCMacro` | Muestra la guia operativa de la barra Iluminacion y el flujo recomendado para calcular, colocar, asignar y organizar luminarias y apagadores. | media | `heredada_de_version_activa` |
| Hoja Iluminacion | `Respaldos/Iluminacion_20260608_175346/Hoja_Iluminación.FCMacro` | Crea o actualiza la hoja de calculo de iluminacion del proyecto con la informacion de recintos, luminarias y parametros usados por ElectricCR. | media | `heredada_de_version_activa` |
| Hoja Iluminacion Legacy | `Respaldos/Iluminacion_Archivadas_20260610_092800/Hoja_Iluminación_Legacy.FCMacro` | Version legacy para crear o actualizar la hoja de calculo de iluminacion utilizada por el flujo anterior de ElectricCR. | media | `inferencia_contextual_gpt` |
| Importar Luminarias CSV | `Respaldos/Iluminacion_legacy_20260324/Importar_Luminarias_CSV_ElectricCR.FCMacro` | Importar_Luminarias_CSV_ElectricCR.FCMacro | media | `catalogo_existente` |
| Insertar Tablero | `Respaldos/ElectricCR_Tablero_Eaton_20260612_093935/Insertar_Tablero.FCMacro` | Inserta tableros, desconectores o interruptores ElectricCR como App::Link a partir del registro de equipos y permite ubicarlos sobre la geometria seleccionada. | media | `heredada_de_version_activa` |
| Insertar_Dispositivo - FUNCIONA | `Respaldos/Reorganizacion_raiz_20260622_095139/Insertar_Dispositivo - FUNCIONA.FCMacro` | Insertar_Dispositivo.FCMacro (rev G) Selector genérico desde registro y creación de instancia usando ElectricCR.electriccr.features.objeto_toma_uno.crear_toma_uno. | media | `catalogo_existente` |
| Poligono desde lineas limite | `Respaldos/Areas_PoligonoFromBoundaryLines_abiertas_20260608_123204/PoligonoFromBoundaryLines.FCMacro` | Construye un poligono Draft cerrado de area a partir de aristas o lineas limite seleccionadas, aplicando tolerancias de snap y cierre. | media | `heredada_de_version_activa` |
| RectFromBoundaryLines | `Respaldos/Areas_PoligonoFromBoundaryLines_20260608_122238/RectFromBoundaryLines.FCMacro` | Crea un rectangulo de Draft usando 2 a N aristas seleccionadas. | media | `catalogo_existente` |
| RectFromBoundaryLines | `Respaldos/Areas_RectFromBoundaryLines_estilo_20260622_150731/RectFromBoundaryLines.FCMacro` | Crea un rectangulo de Draft usando 2 a N aristas seleccionadas. | media | `catalogo_existente` |

## Tableros

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Electrical_Schedule_Base | `Tableros/Electrical_Schedule_Base.FCMacro` | Crea o sirve como base para una hoja de panel schedule electrico en FreeCAD, estructurando la informacion de circuitos del tablero. | media | `catalogo_existente_normalizado` |
| Insertar Tablero | `ElectricCR/Insertar_Tablero.FCMacro` | Inserta tableros, desconectores o interruptores ElectricCR como App::Link a partir del registro de equipos y permite ubicarlos sobre la geometria seleccionada. | alta | `contexto_revisado_gpt` |
| Instalar desconectores de aire acondicionado | `Tableros/Insertar_Desconectores_Aire_Acondicionado.FCMacro` | Inserta un desconector ElectricCR por cada equipo HVAC seleccionado y lo asocia al flujo electrico correspondiente. | alta | `catalogo_existente_normalizado` |

## Tomacorrientes

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Corregir desplazamiento de tomas | `Tomacorrientes/Corregir_Desplazamiento_Reemplazo_Tomas.FCMacro` | Corrige el desplazamiento causado al cambiar un tomacorriente de una clave de registro a otra: calcula la diferencia geometrica entre prototipos antiguo y nuevo y desplaza las tomas para conservar su posicion visual. | alta | `codigo_revisado_gpt` |
| Crear circuitos generales por pared y recinto | `Tomacorrientes/CrearCircuitosGeneralesPorParedYRecinto.FCMacro` | Organiza tomacorrientes generales en circuitos ElectricCR considerando su pared y recinto para formar grupos de circuito coherentes. | alta | `catalogo_existente_normalizado` |
| Etiqueta de circuito | `Tomacorrientes/Insertar_Etiqueta_Circuito.FCMacro` | Inserta una etiqueta grafica con la identificacion de circuito asociada a tomacorrientes u otros elementos electricos seleccionados. | media | `inferencia_nombre_gpt` |
| Etiquetar circuitos (secuencial) | `Tomacorrientes/Etiquetar_Circuitos_Secuencial.FCMacro` | Asigna o actualiza etiquetas de circuito en secuencia para los elementos o circuitos seleccionados. | media | `inferencia_nombre_gpt` |
| InsertarTomacorrientesenPoligonos_objeto_toma | `Tomacorrientes/InsertarTomacorrientesenPoligonos_objeto_toma.FCMacro` | Inserta objetos de tomacorriente ElectricCR sobre cada poligono seleccionado usando el tipo de dispositivo registrado. | alta | `catalogo_existente_normalizado` |
| Insertar_Tomacorriente | `Tomacorrientes/Insertar_Tomacorriente.FCMacro` | Inserta un tomacorriente ElectricCR en el documento utilizando el modelo o tipo configurado para la herramienta. | media | `inferencia_nombre_gpt` |
| Instalar tomacorrientes generales en paredes BIM | `Tomacorrientes/InstalarTomacorrientesEnParedesBIM.FCMacro` | Distribuye de forma asistida tomacorrientes generales sobre paredes Arch/BIM de los recintos seleccionados. | alta | `catalogo_existente_normalizado` |
| Mover tomacorrientes a grupo... | `Tomacorrientes/Mover_Tomacorrientes_a_grupo.FCMacro` | Mueve los tomacorrientes seleccionados a un grupo elegido para reorganizarlos en el arbol del proyecto. | media | `inferencia_nombre_gpt` |
| Ordenar_Tomas_XY | `Tomacorrientes/Ordenar_Tomas_XY.FCMacro` | Ordena los tomacorrientes de un grupo segun sus coordenadas XY, priorizando los elementos superiores y luego su posicion horizontal. | alta | `contexto_revisado_gpt` |
| Ordenar_Tomas_XY_Horario | `Tomacorrientes/Ordenar_Tomas_XY_Horario.FCMacro` | Ordena los tomacorrientes de un grupo en sentido horario alrededor de su centro geometrico, tomando la direccion Y positiva como inicio. | alta | `contexto_revisado_gpt` |
| Pintar tomacorrientes de computo en rojo | `Tomacorrientes/Pintar_Tomacorrientes_Computo_Rojo.FCMacro` | Colorea de rojo las instancias identificadas como tomacorrientes de computo para diferenciarlas visualmente. | alta | `catalogo_existente_normalizado` |
| Reemplazar tomacorrientes (registro) | `Tomacorrientes/Reemplazar_Tomacorrientes_Registro.FCMacro` | Reemplaza tomacorrientes por otro tipo del registro ElectricCR; actualiza KeyRegistro en sitio cuando es posible o crea un reemplazo fisico conservando Placement, Label y pertenencia a grupos. | alta | `codigo_revisado_gpt` |
| Renombrar circuitos... | `Tomacorrientes/Renombrar_Circuitos_Dialogo.FCMacro` | Abre un editor manual para cambiar los nombres de circuitos de tomacorrientes ElectricCR. | alta | `catalogo_existente_normalizado` |
| RotarTomacorriente | `Tomacorrientes/RotarTomacorriente.FCMacro` | Rota los tomacorrientes seleccionados para ajustar su orientacion en el modelo. | alta | `inferencia_nombre_gpt` |
| insertar_tomacorrientes_en_borde | `Tomacorrientes/insertar_tomacorrientes_en_borde.FCMacro` | Distribuye e inserta tomacorrientes ElectricCR a lo largo de bordes o lineas seleccionadas. | alta | `catalogo_existente_normalizado` |

## Xcluidos

| Herramienta | Ruta | Descripcion | Confianza | Fuente |
|---|---|---|---|---|
| Analizar areas rectangulares desde muros BIM | `Xcluidos/Areas/AnalizarAreasRectangularesDesdeMurosBIM.FCMacro` | Analiza muros BIM seleccionados para inferir recintos rectangulares, generar sus areas y etiquetas y crear una hoja con los resultados del analisis. | alta | `contexto_revisado_gpt` |
| CajaEMT | `Xcluidos/Cajas/CajaEMT.FCMacro` | Construye geometricamente una caja octogonal EMT con cavidad y perforaciones laterales para tuberia de 1/2 y 3/4 de pulgada; es una implementacion anterior a la caja EMT moderna basada en STEP y App::Link. | alta | `contexto_revisado_gpt` |
| HVAC_Etiqueta_Libre | `Xcluidos/Objetos/HVAC_Etiqueta_Libre.FCMacro` | Crea una etiqueta de texto Draft independiente para identificar equipos HVAC; la etiqueta no queda vinculada de forma estructurada al equipo. | alta | `contexto_revisado_gpt` |
| actualizar_rectangulos_con_spreadsheet() | `Xcluidos/Areas/actualizar_rectangulos_con_spreadsheet().FCMacro` | Lee datos de una hoja Spreadsheet para actualizar rectangulos, pero la version conservada queda incompleta y no ejecuta la actualizacion geometrica final. | alta | `contexto_revisado_gpt` |
