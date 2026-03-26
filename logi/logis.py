# logger.py
import logging
import sys
from pathlib import Path


# Создаем папку для логов
Path("logi/info").mkdir(exist_ok=True)  # ,parents=True
# нужно что то предпринимать с путем


def info_bot():
    logger = logging.getLogger("для справки")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler("logi/info/info_pars.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def error_bot():
    logger = logging.getLogger("ошибка")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler("logi/info/error_pars.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


inf = info_bot()
err = error_bot()
