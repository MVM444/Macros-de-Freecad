"""
Nombre: models.py
Proposito: Modelos de datos compartidos para el nucleo sanitario MEP.
Funcionamiento: Define resultados y mensajes serializables para tanque septico, FAFA y drenaje.
Modificaciones futuras: Mantener independiente de FreeCAD, FreeCADGui y Qt.
Version: 0.1.0
Fecha: 2026-08-26
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

@dataclass
class ValidationMessage:
    level: str
    code: str
    message: str

@dataclass
class CalculationResult:
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    messages: List[ValidationMessage] = field(default_factory=list)

    def to_dict(self):
        return {"ok": self.ok, "data": self.data, "messages": [asdict(m) for m in self.messages]}
