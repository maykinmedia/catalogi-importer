import logging

from .loader import load_data
from .parser import parse_xml

logger = logging.getLogger(__name__)


def import_from_xml(file: str, catalogus: str, year: int, force: bool):
    logger.info("start parsing")

    zaaktypen, iotypen = parse_xml(file, year)

    logger.info("finish parsing")
    logger.info("start loading")

    load_data(zaaktypen, iotypen, catalogus, force)

    logger.info("finish loading")
