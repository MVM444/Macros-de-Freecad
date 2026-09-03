# `_bundled` - archivos generados para distribucion

Este directorio permite que Facil Arquitectura sea un Addon autosuficiente.

`_bundled/CRBIMCore` es una copia generada del runtime necesario de la fuente autoritativa `Macros-de-Freecad/CRBIMCore`. No editar los archivos internos de este espejo manualmente. Los cambios se realizan primero en la fuente neutral y luego se resincronizan antes de RELEASE.

En el monorepo de desarrollo, `InitGui.py` prefiere importar `CRBIMCore` externo. En una instalacion independiente donde no exista, utiliza automaticamente `FacilArquitecturaWB._bundled.CRBIMCore`.
