import logging

from .loader import load_data
from .parser import parse_xml

logger = logging.getLogger(__name__)


def import_from_xml(file: str, catalogus: str, year: int):
    logger.info("start parsing")

    zaaktypen = parse_xml(file, year)

    logger.info("finish parsing")
    logger.info("start loading")

    load_data(zaaktypen, catalogus)

    logger.info("finish loading")
