# Requisitos Recurrentes - Organizacion de Iluminacion

Fecha base: 2026-03-21

## Objetivo
Usar una estructura tipo explorador de archivos para organizar el arbol del documento de FreeCAD y mantener consistencia con la logica del diagrama unifilar.

## Estructura canonica luminarias
`electrico/Iluminacion/Circuitos/<Circuito>/Recintos/<Recinto>/Apagadores/<Apagador>/Luminarias`

## Reglas funcionales
- Cada recinto debe tener al menos un apagador asociado.
- Las luminarias de un recinto deben organizarse bajo el apagador de ese recinto.
- Un circuito puede alimentar luminarias de varios recintos.
- Sensores de humo se organizan por zonas, no por recintos.
- La deteccion de recintos debe preferir rectangulos del grupo de Areas (o alias), con fallback por propiedades/ancestros.

## Criterios de Areas
- Permitir seleccion manual del grupo de Areas.
- Soportar alias de nombre: Areas, Recintos, Espacios, Zonas.
- Evitar mezclar con grupos de sensores/humo en deteccion automatica.

## Criterios de iconos de macro
- Mantener `# Icon:` en cabecera.
- Mantener el icono junto a la macro.
- Mantener copia del icono en `ElectricCR/icons/` para toolbar.

