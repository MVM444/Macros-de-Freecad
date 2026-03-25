# Organizacion del proyecto - Ordenar grupos

Descripcion breve
Esta macro reordena contenedores en el arbol del documento de FreeCAD. Puede ordenar el nivel root, uno o varios grupos seleccionados, o ambos. Incluye modo manual, alfabetico y por prefijo numerico.

Uso rapido
1. Abrir un documento en FreeCAD.
2. (Opcional) Seleccionar uno o varios grupos o Part en el arbol.
3. Ejecutar la macro "Ordenar grupos" desde el menu ElectricCR > Organizacion del proyecto.
4. Elegir Modo, Metodo y opciones.
5. Revisar la vista previa y pulsar Aplicar.

Metodos
- Manual: usar botones Subir/Bajar/Top/Bottom sobre la lista.
- Alfabetico: ordena por Label (o Name si se activa la opcion).
- Prefijo: si el Label inicia con numero, ordena por ese numero; si no, va despues en orden alfabetico.

Ejemplos de prefijo
- 01_Grupo, 02-Grupo, 10_Equipo  -> orden numerico 1, 2, 10
- E-Tablero, Z-Tablero            -> despues de los numericos, orden alfabetico

Limitaciones y seguridad
- Modo conservador: solo reordena contenedores (Group, App::Part, Std Part). Los objetos sueltos se omiten.
- No se modifica el orden interno de PartDesign Body ni su timeline.
- La opcion "Incluir no contenedores en grupos" permite ordenar objetos sueltos dentro del grupo.
- El orden del nivel root usa doc.reorderObjects si esta disponible; si falla, se intenta un fallback.

Instalacion
Colocar la macro en:
- .../Macros/Macros-de-Freecad/Organizacion del proyecto/Ordenar_Grupos_ElectricCR.FCMacro

El workbench ElectricCR detecta automaticamente la carpeta y crea el menu:
ElectricCR > Organizacion del proyecto > Ordenar grupos

# Organizacion del proyecto - Multirenombrar

Descripcion breve
Esta macro renombra en lote Labels de objetos del arbol. Soporta buscar/reemplazar, prefijo/sufijo, case y contador, con vista previa.

Uso rapido
1. Abrir un documento en FreeCAD.
2. Seleccionar objetos o grupos (recomendado).
3. Ejecutar la macro "Multirenombrar" desde el menu ElectricCR > Organizacion del proyecto.
4. Configurar reglas y revisar la vista previa.
5. Pulsar Aplicar.

Funciones
- Search/Replace: opcional, con regex o texto simple.
- Case: no change / lower / upper / title.
- Prefix / Suffix.
- Counter: start, step, digits, posicion y separador.

Limitaciones y seguridad
- Solo cambia Label (no Name).
- Se omiten PartDesign Body y objetos dentro de Body.

Instalacion
Colocar la macro en:
- .../Macros/Macros-de-Freecad/Organizacion del proyecto/Multirenombrar_ElectricCR.FCMacro

El workbench ElectricCR detecta automaticamente la carpeta y crea el menu:
ElectricCR > Organizacion del proyecto > Multirenombrar

