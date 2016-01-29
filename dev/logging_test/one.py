import logging
logger1 = logging.getLogger("lingt.one")
logger1.debug("hi1")

import two as _two
logger2 = logging.getLogger("lingt.two")
logger1.debug("hi1")
logger2.debug("hi2")

import utils
logger3 = logging.getLogger("lingt.three")
logger1.debug("hi1")
logger2.debug("hi2")
logger3.debug("hi3")

import three as _three

_two.doMain()
_three.doMain()

logger1.debug("done1")
logger2.debug("done2")
logger3.debug("done3")

