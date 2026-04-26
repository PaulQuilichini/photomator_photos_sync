from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

PICK_NAMES = {"Pick", "pick"}


def xml_local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def parse_xmp_flag(sidecar_path: Path) -> bool:
    try:
        tree = ET.parse(sidecar_path)
    except (ET.ParseError, OSError):
        return False

    for element in tree.iter():
        name = xml_local_name(element.tag)
        if name in PICK_NAMES and (element.text or "").strip() == "1":
            return True
        for key, value in element.attrib.items():
            if xml_local_name(key) in PICK_NAMES and value.strip() == "1":
                return True
    return False


def parse_pick_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return any(parse_pick_value(item) for item in value)
    return str(value).strip() == "1"
