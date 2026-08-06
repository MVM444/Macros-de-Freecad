"""Pure helpers for placing ElectricCR luminaires on a ceiling-module grid."""

from __future__ import annotations


EPSILON = 1.0e-6


def balanced_phase(length, module=600.0):
    """Return a boundary phase that leaves equal cuts at both ends."""
    length = float(length)
    module = float(module)
    if length <= EPSILON or module <= EPSILON:
        raise ValueError("La longitud y el modulo deben ser positivos.")
    remainder = length % module
    if remainder <= EPSILON or module - remainder <= EPSILON:
        return 0.0
    return remainder / 2.0


def full_module_cells(length, module=600.0):
    """Return ``(cell_index, centre)`` pairs for complete ceiling cells."""
    length = float(length)
    module = float(module)
    phase = balanced_phase(length, module)
    boundaries = [0.0]
    value = phase if phase > EPSILON else module
    while value < length - EPSILON:
        boundaries.append(value)
        value += module
    boundaries.append(length)
    cells = []
    for index in range(len(boundaries) - 1):
        start, end = boundaries[index], boundaries[index + 1]
        if abs((end - start) - module) <= 0.01:
            cells.append((index, (start + end) / 2.0))
    return cells


def select_balanced_cells(length, count, module=600.0):
    """Select complete cells symmetrically across an axis."""
    count = int(count)
    if count < 1:
        raise ValueError("La cantidad debe ser al menos uno.")
    cells = full_module_cells(length, module)
    if count > len(cells):
        raise ValueError(
            "No caben %d luminarias de %.0f mm en %.1f mm; solo hay %d celdas completas."
            % (count, float(module), float(length), len(cells))
        )
    if count == len(cells):
        return cells
    selected_positions = []
    used = set()
    for item in range(count):
        target_rank = (item + 1.0) * (len(cells) + 1.0) / (count + 1.0) - 1.0
        candidates = sorted(
            range(len(cells)),
            key=lambda index: (abs(index - target_rank), abs(index - (len(cells) - 1.0) / 2.0), index),
        )
        chosen = next(index for index in candidates if index not in used)
        used.add(chosen)
        selected_positions.append(cells[chosen])
    return sorted(selected_positions, key=lambda item: item[1])


def modular_grid_positions(width, depth, columns, rows, module=600.0):
    """Return grid-aware local positions for a rectangular room."""
    x_cells = select_balanced_cells(width, columns, module)
    y_cells = select_balanced_cells(depth, rows, module)
    result = []
    for row_order, (cell_row, y) in enumerate(y_cells):
        for column_order, (cell_column, x) in enumerate(x_cells):
            result.append(
                {
                    "x": x,
                    "y": y,
                    "cell_row": cell_row,
                    "cell_column": cell_column,
                    "row_order": row_order,
                    "column_order": column_order,
                }
            )
    return result
