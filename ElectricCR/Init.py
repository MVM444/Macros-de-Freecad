# -*- coding: utf-8 -*-

import os

# Punto de entrada opcional para recursos o rutas.
# FreeCAD llama a este archivo si el workbench está instalado en Mod/,
# pero en nuestro caso cargaremos el paquete desde un macro cargador.

BASE_DIR = os.path.dirname(__file__)
ICONS_DIR = os.path.join(BASE_DIR, "icons")

