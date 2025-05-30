import logging


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m "
    yellow = "\x1b[33;21m "
    red = "\x1b[31;21m "
    bold_red = "\x1b[31;1m "
    reset = " \x1b[0m"

    format = "%(asctime)s %(levelname)8s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def initial_logger(filename="app.log"):
    logger = logging.getLogger(__name__)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    handler1 = logging.StreamHandler()
    handler2 = logging.FileHandler(filename=f"{filename}")
    handler1.setFormatter(CustomFormatter())
    handler2.setFormatter(CustomFormatter())
    logger.addHandler(handler1)
    logger.addHandler(handler2)
    return logger


logger = initial_logger()
