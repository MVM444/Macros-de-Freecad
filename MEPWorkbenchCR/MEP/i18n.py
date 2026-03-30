"""Simple localization helpers for MEPWorkbenchCR (en/es)."""

import FreeCAD as App

_STRINGS = {
    "en": {
        # Workbench
        "wb.menu_text": "MEP Workbench CR",
        "wb.tooltip": "MEP tools for HVAC (MVP)",
        "wb.toolbar": "MEP HVAC CR",
        "wb.toolbar.main": "HVAC Main",
        "wb.toolbar.system": "HVAC System",
        "wb.menu": "MEP HVAC CR",
        "wb.menu.main": "Main Flow",
        "wb.menu.system": "System Flow",
        "wb.log.initializing": "Initializing MEPWorkbenchCR",
        "wb.log.activated": "Workbench activated",
        "wb.log.deactivated": "Workbench deactivated",
        "wb.log.clean_registration_failed": "Could not remove previous workbench registration: {error}",
        # Commands
        "cmd.create_project.menu": "Create HVAC Project",
        "cmd.create_project.tooltip": "Create or reuse the global HVAC project object",
        "cmd.create_project.run": "Command: Create HVAC Project",
        "cmd.create_project.error": "Error in Create HVAC Project: {error}",
        "cmd.create_space.menu": "Create or Update HVAC Spaces",
        "cmd.create_space.tooltip": "Create/update HVAC spaces from selected polygon(s) or Areas group",
        "cmd.create_space.run": "Command: Create HVAC Space(s)",
        "cmd.create_space.error": "Error in Create HVAC Space: {error}",
        "cmd.calculate.menu": "Calculate HVAC",
        "cmd.calculate.tooltip": "Recalculate spaces and coverage, and update labels automatically",
        "cmd.calculate.run": "Command: Calculate HVAC",
        "cmd.calculate.quick_spaces": "Quick mode applied to {count} space(s) from selected area geometry",
        "cmd.calculate.error": "Error in Calculate HVAC: {error}",
        "cmd.validate.menu": "Validate HVAC",
        "cmd.validate.tooltip": "Run HVAC consistency checks on spaces, equipment, ports and routes",
        "cmd.validate.run": "Command: Validate HVAC",
        "cmd.validate.error": "Error in Validate HVAC: {error}",
        "cmd.validate.summary": "Validation summary: errors={errors}, warnings={warnings}, info={infos}",
        "cmd.insert_evaporator.menu": "Insert Concrete Evaporator",
        "cmd.insert_evaporator.tooltip": "Insert concrete evaporator with 2D symbol + 3D model at real height",
        "cmd.insert_evaporator.run": "Command: Insert Evaporator",
        "cmd.insert_evaporator.error": "Error in Insert Evaporator: {error}",
        "cmd.insert_condenser.menu": "Insert Condenser",
        "cmd.insert_condenser.tooltip": "Insert condenser manually (position and assignment are manual)",
        "cmd.insert_condenser.run": "Command: Insert Condenser",
        "cmd.insert_condenser.error": "Error in Insert Condenser: {error}",
        "cmd.assign_units.menu": "Assign to Condenser",
        "cmd.assign_units.tooltip": "Assign selected evaporators to selected condenser",
        "cmd.assign_units.run": "Command: Assign to Condenser",
        "cmd.assign_units.error": "Error in Assign to Condenser: {error}",
        "cmd.create_route.menu": "Create HVAC Route",
        "cmd.create_route.tooltip": "Create HVAC route from selected ports or points",
        "cmd.create_route.run": "Command: Create HVAC Route",
        "cmd.create_route.error": "Error in Create HVAC Route: {error}",
        "cmd.toggle_labels.menu": "Show/Hide Labels",
        "cmd.toggle_labels.tooltip": "Toggle HVAC labels visibility",
        "cmd.toggle_labels.run": "Command: Show/Hide Labels",
        "cmd.toggle_labels.error": "Error in Show/Hide Labels: {error}",
        "cmd.reload.menu": "Reload Workbench",
        "cmd.reload.tooltip": "Reload MEPWorkbenchCR without restarting FreeCAD",
        "cmd.reload.run": "Command: Reload Workbench",
        "cmd.reload.error": "Error in Reload Workbench: {error}",
        # Project module
        "project.log.no_active_doc": "No active document",
        "project.log.use_existing": "Using existing HVAC project: {name}",
        "project.log.created": "HVAC project created: {name}",
        "project.log.factor": "Climate factor recalculated: {factor} BTU/h*m2",
        "project.prop.location": "Project location",
        "project.prop.altitude": "Site altitude in meters",
        "project.prop.outdoor_temp": "Outdoor temperature (C)",
        "project.prop.humidity": "Relative humidity (%)",
        "project.prop.indoor_temp": "Target indoor temperature (C)",
        "project.prop.climate_factor": "Calculated factor in BTU/h*m2",
        "project.prop.climate_offset": "Manual climate offset (BTU/h*m2)",
        "project.prop.regional_bonus": "Regional microclimate bonus (BTU/h*m2)",
    },
    "es": {
        # Workbench
        "wb.menu_text": "MEP Workbench CR",
        "wb.tooltip": "Herramientas MEP para HVAC (MVP)",
        "wb.toolbar": "MEP HVAC CR",
        "wb.toolbar.main": "HVAC Principal",
        "wb.toolbar.system": "HVAC Sistema",
        "wb.menu": "MEP HVAC CR",
        "wb.menu.main": "Flujo Principal",
        "wb.menu.system": "Flujo Sistema",
        "wb.log.initializing": "Inicializando MEPWorkbenchCR",
        "wb.log.activated": "Workbench activado",
        "wb.log.deactivated": "Workbench desactivado",
        "wb.log.clean_registration_failed": "No se pudo limpiar registro previo: {error}",
        # Commands
        "cmd.create_project.menu": "Crear Proyecto HVAC",
        "cmd.create_project.tooltip": "Crear o reutilizar el objeto global de proyecto HVAC",
        "cmd.create_project.run": "Comando Crear Proyecto HVAC",
        "cmd.create_project.error": "Error en Crear Proyecto HVAC: {error}",
        "cmd.create_space.menu": "Crear o Actualizar Recintos HVAC",
        "cmd.create_space.tooltip": "Crear/actualizar recintos HVAC desde poligono(s) o grupo Areas",
        "cmd.create_space.run": "Comando Crear Recinto(s) HVAC",
        "cmd.create_space.error": "Error en Crear Recinto HVAC: {error}",
        "cmd.calculate.menu": "Calcular HVAC",
        "cmd.calculate.tooltip": "Recalcular recintos y cobertura, y actualizar etiquetas automaticamente",
        "cmd.calculate.run": "Comando Calcular HVAC",
        "cmd.calculate.quick_spaces": "Modo rapido aplicado a {count} recinto(s) desde la geometria seleccionada",
        "cmd.calculate.error": "Error en Calcular HVAC: {error}",
        "cmd.validate.menu": "Validar HVAC",
        "cmd.validate.tooltip": "Ejecutar validaciones de consistencia en recintos, equipos, puertos y rutas",
        "cmd.validate.run": "Comando Validar HVAC",
        "cmd.validate.error": "Error en Validar HVAC: {error}",
        "cmd.validate.summary": "Resumen validacion: errores={errors}, advertencias={warnings}, info={infos}",
        "cmd.insert_evaporator.menu": "Insertar Evaporadora Concreta",
        "cmd.insert_evaporator.tooltip": "Insertar evaporadora concreta con simbolo 2D + modelo 3D a altura real",
        "cmd.insert_evaporator.run": "Comando Insertar Evaporadora",
        "cmd.insert_evaporator.error": "Error en Insertar Evaporadora: {error}",
        "cmd.insert_condenser.menu": "Insertar Condensadora",
        "cmd.insert_condenser.tooltip": "Insertar condensadora manualmente (ubicacion y asignacion manual)",
        "cmd.insert_condenser.run": "Comando Insertar Condensadora",
        "cmd.insert_condenser.error": "Error en Insertar Condensadora: {error}",
        "cmd.assign_units.menu": "Asignar a Condensadora",
        "cmd.assign_units.tooltip": "Asignar evaporadoras seleccionadas a la condensadora seleccionada",
        "cmd.assign_units.run": "Comando Asignar a Condensadora",
        "cmd.assign_units.error": "Error en Asignar a Condensadora: {error}",
        "cmd.create_route.menu": "Crear Ruta HVAC",
        "cmd.create_route.tooltip": "Crear ruta HVAC conectando puertos o puntos seleccionados",
        "cmd.create_route.run": "Comando Crear Ruta HVAC",
        "cmd.create_route.error": "Error en Crear Ruta HVAC: {error}",
        "cmd.toggle_labels.menu": "Mostrar/Ocultar etiquetas",
        "cmd.toggle_labels.tooltip": "Alternar visibilidad de etiquetas HVAC de recintos",
        "cmd.toggle_labels.run": "Comando Mostrar/Ocultar etiquetas",
        "cmd.toggle_labels.error": "Error en Mostrar/Ocultar etiquetas: {error}",
        "cmd.reload.menu": "Recargar Workbench",
        "cmd.reload.tooltip": "Recargar MEPWorkbenchCR sin reiniciar FreeCAD",
        "cmd.reload.run": "Comando Recargar Workbench",
        "cmd.reload.error": "Error en Recargar Workbench: {error}",
        # Project module
        "project.log.no_active_doc": "No hay documento activo",
        "project.log.use_existing": "Usando proyecto HVAC existente: {name}",
        "project.log.created": "Proyecto HVAC creado: {name}",
        "project.log.factor": "Factor recalculado: {factor} BTU/h*m2",
        "project.prop.location": "Ubicacion del proyecto",
        "project.prop.altitude": "Altitud del sitio en metros",
        "project.prop.outdoor_temp": "Temperatura exterior (C)",
        "project.prop.humidity": "Humedad relativa (%)",
        "project.prop.indoor_temp": "Temperatura interior objetivo (C)",
        "project.prop.climate_factor": "Factor calculado en BTU/h*m2",
        "project.prop.climate_offset": "Ajuste manual del factor (BTU/h*m2)",
        "project.prop.regional_bonus": "Bono regional microclimatico (BTU/h*m2)",
    },
}


def _normalize_lang(raw_value):
    value = str(raw_value or "").strip().lower()
    if not value:
        return "en"
    if value.startswith("es") or "spanish" in value or "espan" in value:
        return "es"
    return "en"


def get_language():
    """Return active language code: 'es' or 'en'."""

    try:
        lang = App.ParamGet("User parameter:BaseApp/Preferences/General").GetString("Language", "")
    except Exception:
        lang = ""
    return _normalize_lang(lang)


def tr(key, **kwargs):
    """Translate key with optional format values."""

    lang = get_language()
    table = _STRINGS.get(lang, _STRINGS["en"])
    text = table.get(key, _STRINGS["en"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
