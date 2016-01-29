
import logging
logger1 = logging.getLogger("lingt.one")
logger1.debug("hi1")

import utils
logger2 = logging.getLogger("lingt.three")
logger1.debug("hi1")
logger2.debug("hi2")

def doMain():
    logger1.debug(utils.funcName())
    logger2.debug(utils.funcName())
