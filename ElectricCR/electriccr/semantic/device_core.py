"""Pure, JSON-compatible semantic projection planning for ElectricCR.

This module deliberately has no FreeCAD, FreeCADGui or Qt dependency.  The
FreeCAD adapter translates document objects to the small string contract used
here and materializes the returned projection only when explicitly requested.
"""

from __future__ import annotations

import re
import unicodedata


SCHEMA_VERSION = 1
STATUS_READY = "READY"
STATUS_INCOMPLETE = "INCOMPLETE"


def _text(value):
    return str(value or "").strip()


def _token(value, fallback="node"):
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^0-9a-z]+", "-", text).strip("-")
    return text or fallback


def build_lighting_projection(element_uid, space_name, circuit_id, switch_id):
    """Return the canonical lighting branch for one semantic luminaire.

    The result contains only JSON-compatible values.  Stable ``key`` values
    identify visual containers independently of their FreeCAD internal names.
    """
    uid = _text(element_uid)
    room = _text(space_name)
    circuit = _text(circuit_id)
    switch = _text(switch_id)
    missing = [
        name
        for name, value in (
            ("ElementUID", uid),
            ("Space", room),
            ("CircuitoID", circuit),
            ("Apagador", switch),
        )
        if not value
    ]
    if missing:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": STATUS_INCOMPLETE,
            "missing": missing,
            "path": [],
            "nodes": [],
            "element_uid": uid,
        }

    circuit_token = _token(circuit, "circuit")
    room_token = _token(room, "room")
    switch_token = _token(switch, "switch")
    definitions = [
        ("Lighting", "Iluminacion", "lighting"),
        ("Circuits", "Circuitos", "lighting/circuits"),
        ("Circuit", circuit, "lighting/circuit/%s" % circuit_token),
        ("Rooms", "Recintos", "lighting/circuit/%s/rooms" % circuit_token),
        (
            "Room",
            room,
            "lighting/circuit/%s/room/%s" % (circuit_token, room_token),
        ),
        (
            "Switches",
            "Apagadores",
            "lighting/circuit/%s/room/%s/switches" % (circuit_token, room_token),
        ),
        (
            "Switch",
            switch,
            "lighting/circuit/%s/room/%s/switch/%s"
            % (circuit_token, room_token, switch_token),
        ),
        (
            "Luminaires",
            "Luminarias",
            "lighting/circuit/%s/room/%s/switch/%s/luminaires"
            % (circuit_token, room_token, switch_token),
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS_READY,
        "missing": [],
        "path": ["electrico"] + [label for _role, label, _key in definitions],
        "nodes": [
            {"role": role, "label": label, "key": key}
            for role, label, key in definitions
        ],
        "element_uid": uid,
        "space_name": room,
        "circuit_id": circuit,
        "switch_id": switch,
    }


__all__ = [
    "SCHEMA_VERSION",
    "STATUS_INCOMPLETE",
    "STATUS_READY",
    "build_lighting_projection",
]

