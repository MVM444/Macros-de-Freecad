# Memoria: A1 GitHub y experimento NativeIFC

## Estado vigente - 2026-09-09 20:02 -0600 America/Costa_Rica

**A1 aprobado y cerrado en GitHub; experimento NativeIFC completado sin modificar A1.**

A1 cerrado en GitHub: [4a9ade9](https://github.com/MVM444/Macros-de-Freecad/commit/4a9ade9645d9227ac5323676ee911c972502e869), constancia [285d5a7](https://github.com/MVM444/Macros-de-Freecad/commit/285d5a74b6463dc859d0bc0a940b2879aa6c4c2a), rama `codex/cierre-a1-20260909`; ambos pushes confirmados, staging limpio. Se separaron cambios ajenos y la evidencia publica se anonimizo conforme AGENTS. No merge a main ni release Addon. DEV funcional sin cambios.

Prueba real IFC4: cuatro Part::FeaturePython (Outlet, SwitchingDevice, LightFixture, ElectricDistributionBoard), GUID/StepId y Placement/Pset editados persistentes tras FCStd+IFC y reapertura IFC. Type=None; cuatro ocurrencias, un proyecto de infraestructura. Mallas genericas sin solidos, sin excepciones de consola. No se uso Upala ni conversiones existentes. Todo cerrado y evidencia archivada.

Decision provisional: explorar **NativeIFC como capa/adaptador alrededor de A1 (opcion2)**. Los mapas IFC permiten compartir representacion, pero no se probo Type compartido ni equivalencia con App::Link. No adoptar nucleo ni hibrido todavia. No hay integracion implementada. Detalles/campos/limitaciones en [reporte](tests/evidence/2026-09-09_nativeifc_four_elements/README.md) y RESULTADO_CODEX.md. NativeIFC = EXPERIMENTAL / COMPROBADA-PARCIAL; A1 mantiene su estado previo.

---


| Alternativa | Evidencia a favor | Limite / decision provisional |
| --- | --- | --- |
| 1. NativeIFC como nucleo | Clase, GlobalId, atributos IFC, Placement y Pset editados/persistidos nativamente en las cuatro clases. | No adoptar todavia: no se probo edicion colectiva por Type, rendimiento, documentos grandes ni equivalencia con App::Link. |
| 2. NativeIFC como capa/adaptador alrededor de A1 | Permite estudiar semantica/intercambio IFC conservando el A1 aprobado. | **Opcion recomendada para el siguiente diseno exploratorio**, sin implementar aun. Definir primero una sola autoridad para identidad, Placement y propiedades. |
| 3. Hibrida | Los mapas IFC pueden compartir representacion, mientras A1 conserva su autoría y documentacion. | Hipotesis pendiente; duplicar motores introduce sincronizacion y persistencia adicionales. No hay integracion validada. |

Referencia completa: ../../ElectricCR/tests/evidence/2026-09-09_nativeifc_four_elements/README.md
