# Facil Arquitectura - Checklist de primera RELEASE

Version: `0.14.11`  
Build de preparacion: `2026.09.02.8`  
FreeCAD: `1.1.3`

## Bloqueadores antes de publicar

- [ ] Ejecutar `python tools/sync_bundled_crbimcore.py --check`; si falla, revisar con `--dry-run` y resincronizar antes de continuar.
- [ ] Probar en perfil limpio con **solo Facil Arquitectura** instalado; no debe existir un `CRBIMCore` externo accesible.
- [ ] Confirmar `CRBIM_SelectRoom`, `CRBIM_RoomInfo`, `CRBIM_NameRoom` y `CRBIM_RoomGuide` usando el fallback interno.
- [ ] Ejecutar suite de pruebas y `py_compile` de los modulos publicados.
- [ ] Smoke Demo fija y aleatoria, incluida la regresion del dock tras Hot restart.
- [ ] Smoke `FA JSON`: Salida -> copiar -> Entrada/Ejemplo -> Validar -> Dry-run -> Aplicar -> repetir UPDATE sin duplicados -> Undo/Redo -> copiar resultado/error.
- [ ] Smoke DWG/DXF: importar, verificar unidad/escala con distancia conocida y comprobar flujo de capas/centros.
- [ ] Smoke paredes, puertas, ventanas, tablas y `Cerrar buques`.
- [ ] Smoke Recintos/Espacios experimentales y persistencia de identidad.
- [ ] Smoke techo desde rectangulo y cielorraso.
- [ ] Compilar catalogos `.qm` y recorrer interfaz completa en Espanol e Ingles.
- [ ] Auditar procedencia/licencia de todos los recursos graficos; actualizar `THIRD_PARTY_NOTICES.md`.
- [ ] Crear repositorio RELEASE y agregar a `package.xml` URLs reales de repository, bugtracker y readme.
- [ ] Confirmar que `package.xml` es valido y muestra nombre, version, icono y descripcion correctos en Addon Manager Developer Tools.
- [ ] Staging limpio: comprobar que no contiene respaldos, logs, tareas internas, caches, datos personales ni rutas locales.
- [ ] Instalar desde el repositorio RELEASE en otro perfil limpio; probar actualizar/desinstalar/reinstalar.

## Criterio de salida

No marcar PUBLICABLE mientras exista un bloqueador sin comprobar. La advertencia de desarrollo asistido por IA debe permanecer visible en Ayuda -> Informacion y en README.
