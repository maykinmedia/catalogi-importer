from .parser import parse_xml


def import_from_xml(file: str):
    zaaktypen = parse_xml(file)

    return zaaktypen
