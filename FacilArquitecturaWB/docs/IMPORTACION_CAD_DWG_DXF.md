# Importacion controlada de referencias DWG y DXF

El comando `FA Importar referencia DWG/DXF` conserva el procedimiento validado con
`Puriscal Aire Acondicionado.dwg` y evita depender de que el modelo BIM principal
este abierto o sincronizado.

## Uso rapido

1. Active el workbench **Facil Arquitectura**.
2. Ejecute **FA Importar referencia DWG/DXF**.
3. Seleccione el archivo `.dwg` o `.dxf`.
4. Indique la unidad real usada por sus coordenadas: automatica, metros,
   milimetros o centimetros.
5. Revise el documento nuevo y guardelo solamente cuando corresponda.

El comando recuerda el ultimo directorio y la ultima unidad. Siempre crea un
documento nuevo sin guardar; nunca inserta la referencia dentro del FCStd activo.

## Que automatiza

- Para DWG usa `importDWG.convertToDxf()` y, por tanto, el convertidor configurado
  en las preferencias de FreeCAD (normalmente ODA File Converter).
- Lee `$INSUNITS` y `$MEASUREMENT` del DXF convertido.
- Calcula el factor manual de Draft para que la escala efectiva corresponda a la
  unidad real elegida. Por ejemplo, si la cabecera dice milimetros pero el dibujo
  esta en metros, aplica `dxfScaling = 1000` durante esa importacion.
- Desactiva temporalmente el dialogo adicional de DXF y restaura tanto ese ajuste
  como `dxfScaling` al finalizar, incluso si ocurre un error.
- Usa `doc.Name`, el nombre interno seguro de FreeCAD, y no `doc.Label`. Esto evita
  el error `Try to activate unknown document` cuando la etiqueta contiene espacios.
- Coloca la vista superior, ajusta el contenido y agrega `FA_CADImportMetadata`
  con ruta fuente, unidades, escala y cantidad de objetos.
- Elimina la conversion DXF temporal cuando fue creada dentro de la carpeta
  temporal del sistema.

## Validacion recomendada

La comprobacion principal usa la cantidad de objetos y el rango de posiciones de
las inserciones. No se rechaza una importacion solo por la caja global de las
Shapes: textos, cotas y definiciones de bloques pueden producir extensiones enormes
aunque las instancias visibles esten correctamente ubicadas.

Revise especialmente:

- que una distancia conocida mida correctamente en milimetros dentro de FreeCAD;
- que no exista un simbolo aislado lejos de la planta;
- que textos o cotas contenidos en bloques dinamicos no se hayan separado;
- que el documento tenga asterisco de cambios pendientes y no `FileName` asignado.

## Limitaciones

- ODA y el importador Draft pueden emitir avisos al encontrar textos o dimensiones
  dentro de definiciones de bloque. La geometria restante puede importarse bien.
- Un DWG puede mezclar una planta en milimetros dentro de un bloque con inserciones
  expresadas en metros. El comando conserva la transformacion del archivo, pero la
  caja del bloque base puede no representar la extension visible de su instancia.
- El comando no limpia layers, no convierte automaticamente la referencia a BIM y
  no guarda el documento. Esas decisiones permanecen bajo control del usuario.

## Macro de acceso directo

`ImportarReferenciaCADFacilArquitectura.FCMacro`, ubicada en el directorio general
de macros, abre el mismo dialogo y ejecuta exactamente este nucleo. Sirve cuando el
workbench todavia no esta activo.
