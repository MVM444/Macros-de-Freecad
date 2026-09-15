# Experimento NativeIFC - cuatro elementos desechables

Documentado: 2026-09-09 20:02 -0600, America/Costa_Rica. Ejecucion real: 2026-09-09T09:21:49.645609-06:00 a 2026-09-09T09:22:33.267892-06:00.

**Experimento APROBADO en su alcance. A1 permanece APROBADO y sin cambios.** Recomendacion: opcion 2 como siguiente diseno exploratorio; no adoptar NativeIFC como nucleo ni desarrollar integracion en esta tarea.

## Entorno y archivos

FreeCAD 1.1.3, revision 20260725, commit 145529fe741292ff0b3977a01195bf0247425794. IfcOpenShell 0.8.4. NativeIFC incluido en la instalacion, Workbench BIM activo. Comandos ejecutados en hilo GUI mediante el dispatcher XML-RPC del FreeCADMCP instalado; no simulacion headless ni implementacion propia de IFC.

Documento nuevo: `NativeIFC_four_elements`. Esquema real leido del archivo: **IFC4**. Tablero usado: **IfcElectricDistributionBoard**. Solo cuatro IfcElement; cinco objetos FreeCAD porque el quinto es IfcProject de infraestructura. Contextos, unidades, geometria y relaciones IFC son soporte del archivo; no se crearon Types, puertos ni otras ocurrencias. Los cuatro elementos se agregaron directamente al proyecto de prueba; no se construyo un edificio/jerarquia espacial de produccion ni se valido un MVD.

Archivos desechables conservados en `C:\Users\marco\AppData\Local\Temp\ecr_nativeifc_four_20260909`: `NativeIFC_four_elements.FCStd` y `NativeIFC_four_elements.ifc`. No se uso Upala ni se convirtio ningun objeto existente. Ambos documentos de prueba quedaron cerrados. Evidencia durable en esta carpeta: results.json, console.txt, created.png, reopened.png y verification.json. Modelos permanecen solo en TEMP.

## Matriz por elemento

En los cuatro: **TypeId=Part::FeaturePython**, `Class == IfcClass`, `Type=None`; la propiedad Type existe como `App::PropertyLink`. Todos nacieron sin Psets adjuntos. La columna de plantillas cuenta las disponibles para la clase/PredefinedType inicial, no propiedades ya creadas.

| Class / IfcClass | StepId | GlobalId | PredefinedType inicial | Plantillas Pset | Editar / guardar / reabrir |
| --- | --- | --- | --- | --- | --- |
| IfcOutlet | 23 | 1rFbdunpr2VQ5E1baavUGb | POWEROUTLET | 10 | APROBADO |
| IfcSwitchingDevice | 39 | 0j4zgp8g509O$ZZR__7kAz | TOGGLESWITCH | 12 | APROBADO |
| IfcLightFixture | 55 | 0IEGv02gvDkRo_Jgc4dWmR | POINTSOURCE | 10 | APROBADO |
| IfcElectricDistributionBoard | 71 | 2LirlfVS114ejmyYpSdFi6 | DISTRIBUTIONBOARD | 11 | APROBADO |

Edicion sobre propiedades nativas FreeCAD: Label, Description, PredefinedType -> USERDEFINED, ObjectType -> ProbeDevice, desplazamiento y giro Z=15 grados. Cambios verificados en las entidades IFC, no solo en la interfaz FreeCAD. Se agrego `Pset_ProbeExperiment.ProbeReference` y se edito de `before` a `after` mediante propiedad expuesta por NativeIFC. Los GUID no se editaron. Los cuatro conservaron clase, GUID y StepId en ambas reaperturas.

| Elemento | Placement final [x,y,z] mm | Giro Z grados |
| --- | --- | --- |
| IfcOutlet | [100.0, 200.0, 300.0] | 15 |
| IfcSwitchingDevice | [900.0, 200.0, 300.0] | 15 |
| IfcLightFixture | [1700.0, 200.0, 300.0] | 15 |
| IfcElectricDistributionBoard | [2500.0, 200.0, 300.0] | 15 |

Placement inicial: X=0/800/1600/2400 mm, Y=Z=0 y giro cero. IFC usa metros en este archivo; se cotejaron matrices IFC y Placement FreeCAD. GlobalId y StepId permanecieron 23/39/55/71 en este mismo archivo guardado; StepId es un identificador local STEP, no una identidad garantizada entre reconstrucciones/exportadores.

Inspector nativo: Class, GlobalId, PredefinedType, Placement y Type no estan marcados read-only; IfcClass esta Hidden; StepId esta ReadOnly. No se ensayo cambiar la identidad ni reclasificar entre familias. No confundir Type IFC (vinculo) con Proxy.Type interno ni con ObjectType='ProbeDevice'.

Plantillas aplicables al estado inicial:

- `IfcOutlet`: `Pset_EnvironmentalImpactIndicators`, `Pset_EnvironmentalImpactValues`, `Pset_SoundGeneration`, `Pset_Condition`, `Pset_ManufacturerOccurrence`, `Pset_ManufacturerTypeInformation`, `Pset_ServiceLife`, `Pset_Warranty`, `Pset_ElectricalDeviceCommon`, `Pset_OutletTypeCommon`.
- `IfcSwitchingDevice`: `Pset_EnvironmentalImpactIndicators`, `Pset_EnvironmentalImpactValues`, `Pset_SoundGeneration`, `Pset_Condition`, `Pset_ManufacturerOccurrence`, `Pset_ManufacturerTypeInformation`, `Pset_ServiceLife`, `Pset_Warranty`, `Pset_ElectricalDeviceCommon`, `Pset_SwitchingDeviceTypeCommon`, `Pset_SwitchingDeviceTypePHistory`, `Pset_SwitchingDeviceTypeToggleSwitch`.
- `IfcLightFixture`: `Pset_EnvironmentalImpactIndicators`, `Pset_EnvironmentalImpactValues`, `Pset_SoundGeneration`, `Pset_Condition`, `Pset_ManufacturerOccurrence`, `Pset_ManufacturerTypeInformation`, `Pset_ServiceLife`, `Pset_Warranty`, `Pset_ElectricalDeviceCommon`, `Pset_LightFixtureTypeCommon`.
- `IfcElectricDistributionBoard`: `Pset_EnvironmentalImpactIndicators`, `Pset_EnvironmentalImpactValues`, `Pset_SoundGeneration`, `Pset_Condition`, `Pset_ManufacturerOccurrence`, `Pset_ManufacturerTypeInformation`, `Pset_ServiceLife`, `Pset_Warranty`, `Pset_ElectricalDeviceCommon`, `Pset_ElectricDistributionBoardOccurrence`, `Pset_ElectricDistributionBoardTypeCommon`.

## Persistencia y comprobacion visual

Cuatro fases: created, edited, fcstd_reopened, ifc_reopened; siempre 4 IfcElement y 5 objetos FreeCAD. `passed=true`. Guardado explicito del IFC mediante ifc_tools.save, despues FCStd, cierre, reapertura FCStd con su archivo IFC companero, nuevo cierre y apertura independiente del IFC con NativeIFC. GUIDs, StepIds, clase, PredefinedType, Type, Placement, descripcion y Pset simple persistieron. Etiqueta tambien cotejada. ObjectType figura en ambos inventarios de reapertura y en el IFC, aunque se agrego a la captura despues de los dos primeros inventarios.

Se conservaron los dos hashes de archivos en results.json y se verificaron al archivar evidencia. Capturas revisadas: cuatro representaciones genericas presentes al crear y al reabrir, con desplazamiento/giro. Son geometria de malla/superficies (Shape no nula, **0 solidos**); no se probo edicion parametrica de solidos, booleanas ni volumen fisico. El avatar y rejilla de las capturas son referencias GUI de BIM, no elementos IFC nuevos.

Consola capturada: sin excepciones, errores Placement ni Access violation en esta prueba. NativeIFC imprime diagnostico de las propiedades al materializar Psets; no es un error. Edicion probada mediante propiedades Python nativas y callbacks reales, no mediante clic manual en el panel de propiedades. El guardado aprobado requiere el IFC companero; no acredita autonomia del FCStd sin ese archivo.

## Type y reutilizacion: investigacion sin desarrollo

IFC permite que un Type contenga RepresentationMaps y que varias ocurrencias referencien el mismo mapa mediante IfcMappedItem, con transformacion propia. Compartir Type sin esos mapas no demuestra compartir geometria. NativeIFC edit_type valida la clase de Type y llama a IfcOpenShell type.assign_type con mapping por defecto. Por ello hay un mecanismo nativo reutilizable a investigar.

Esto no equivale operativamente a A1 Master + App::Link: NativeIFC materializa Part::FeaturePython por ocurrencia, asigna Shape por objeto y su cache usa el id del elemento. No se midieron memoria ni rendimiento y no se crearon ocurrencias extra para simular una prueba de Type compartido. Los cuatro Type permanecieron None. La equivalencia se investigó documentalmente, no se demuestra experimentalmente.

Limitaciones concretas del codigo inspeccionado: desasignar Type al poner None contiene TODO/pass en ifc_types.py; no se ejecuto esa ruta. ifc_psets.get_psets presupone NominalValue para SingleValue y deja cantidades pendientes. El exito de un Pset propio simple no acredita todas las formas de Psets, propiedades estandar ni cantidades. IFC4.3 usa IfcDistributionBoard y depreca IfcElectricDistributionBoard; el experimento solo prueba el IFC4 real generado.

## Matriz de decision

| Alternativa | Evidencia a favor | Limite / decision provisional |
| --- | --- | --- |
| 1. NativeIFC como nucleo | Clase, GlobalId, atributos IFC, Placement y Pset editados/persistidos nativamente en las cuatro clases. | No adoptar todavia: no se probo edicion colectiva por Type, rendimiento, documentos grandes ni equivalencia con App::Link. |
| 2. NativeIFC como capa/adaptador alrededor de A1 | Permite estudiar semantica/intercambio IFC conservando el A1 aprobado. | **Opcion recomendada para el siguiente diseno exploratorio**, sin implementar aun. Definir primero una sola autoridad para identidad, Placement y propiedades. |
| 3. Hibrida | Los mapas IFC pueden compartir representacion, mientras A1 conserva su autoría y documentacion. | Hipotesis pendiente; duplicar motores introduce sincronizacion y persistencia adicionales. No hay integracion validada. |


Clasificacion: SOPORTE / EXPERIMENTAL / COMPROBADA-PARCIAL. Se reutiliza NativeIFC existente; no reemplaza A1, no agrega adaptador ni define una arquitectura nueva. No se probaron Undo/Redo NativeIFC, intercambio con terceros, MVD, rendimiento ni Type compartido: no formaban parte del experimento solicitado. Los limites son parte de la decision, no regresiones A1.

## Fuentes primarias

- [IfcOutlet IFC4](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/schema/ifcelectricaldomain/lexical/ifcoutlet.htm), [IfcSwitchingDevice IFC4](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/schema/ifcelectricaldomain/lexical/ifcswitchingdevice.htm), [IfcLightFixture IFC4](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/schema/ifcelectricaldomain/lexical/ifclightfixture.htm).
- [IfcElectricDistributionBoard IFC4](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD1/HTML/schema/ifcelectricaldomain/lexical/ifcelectricdistributionboard.htm); [IfcDistributionBoard IFC4.3](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcDistributionBoard.htm); [deprecacion de IfcElectricDistributionBoard en IFC4.3](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcElectricDistributionBoard.htm).
- [IfcRepresentationMap](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcRepresentationMap.htm) y [IfcMappedItem](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcMappedItem.htm): reutilizacion de representacion con transformacion por ocurrencia.
- [IfcOpenShell assign_type](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/type/assign_type/index.html) y [map_type_representations](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/type/map_type_representations/index.html): mapping habilitado por defecto cuando el Type tiene mapas.
- NativeIFC 1.1.3: [ifc_tools.py](https://github.com/FreeCAD/FreeCAD/blob/1.1.3/src/Mod/BIM/nativeifc/ifc_tools.py), [ifc_types.py](https://github.com/FreeCAD/FreeCAD/blob/1.1.3/src/Mod/BIM/nativeifc/ifc_types.py), [ifc_generator.py](https://github.com/FreeCAD/FreeCAD/blob/1.1.3/src/Mod/BIM/nativeifc/ifc_generator.py), [ifc_psets.py](https://github.com/FreeCAD/FreeCAD/blob/1.1.3/src/Mod/BIM/nativeifc/ifc_psets.py). Codigo instalado cotejado en `Mod/BIM/nativeifc` de la aplicacion probada.


## Reproduccion y archivos cambiados

Helper nuevo `ElectricCR/tests/freecad_nativeifc_four_elements_probe.py`: en FreeCAD 1.1.3/BIM, importar con importlib, construir NativeIfcProbe con una ruta TEMP nueva y llamar create(), edit(), save_reopen(). Rechaza una carpeta existente. No importa A1 ni usa archivos productivos. Las APIs nativas crean entidades IFC desde cero, no convierten objetos FreeCAD existentes.

Se actualizaron RESULTADO_CODEX.md, ESTADO_PROYECTO.md, TAREA_ACTUAL.md y Memoria_FreeCAD/sesiones/2026-09-09_electriccr-nativeifc-cuatro-elementos.md. Los 13 archivos de codigo/pruebas A1 revisados para GitHub mantienen sus hashes DEV originales. Sintaxis del helper nuevo aprobada. El experimento queda local, separado de los commits de cierre A1; no se hizo commit/push de NativeIFC ni de una integracion.
