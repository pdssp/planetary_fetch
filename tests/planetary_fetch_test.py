# -*- coding: utf-8 -*-
import logging

import pytest

import planetary_fetch

logger = logging.getLogger(__name__)


@pytest.fixture
def setup():
    logger.info("----- Init the tests ------")


def test_init_setup(setup):
    logger.info("Setup is initialized")


def test_name():
    name = planetary_fetch.__name_soft__
    assert name == "planetary_fetch"


def test_logger():
    loggers = [logging.getLogger()]
    loggers = loggers + [
        logging.getLogger(name) for name in logging.root.manager.loggerDict
    ]
    assert loggers[0].name == "root"


def test_new_level():
    planetary_fetch.custom_logging.UtilsLogs.add_logging_level("TRACE", 20)
    logger = logging.getLogger("__main__")
    logger.setLevel(logging.TRACE)  # type: ignore
    ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.trace("Test the logger")  # type: ignore
    logger.log(logging.TRACE, "test")  # type: ignore


def test_message():
    record = planetary_fetch.custom_logging.LogRecord(
        "__main__",
        logging.INFO,
        "pathname",
        2,
        "message {val1} {val2}",
        {"val1": 10, "val2": "test"},
        None,
    )
    assert "message 10 test", record.getMessage()

    record = planetary_fetch.custom_logging.LogRecord(
        "__main__",
        logging.INFO,
        "pathname",
        2,
        "message {0} {1}",
        ("val1", "val2"),
        None,
    )
    assert "message val1 val2", record.getMessage()


def test_color_formatter():
    formatter = planetary_fetch.custom_logging.CustomColorFormatter()
    logger = logging.getLogger("planetary_fetch.custom_logging")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    logger.addHandler(logging.NullHandler())
    logger.info("test")

    shell_formatter = planetary_fetch.custom_logging.ShellColorFormatter()
    record = planetary_fetch.custom_logging.LogRecord(
        "__main__",
        logging.INFO,
        "pathname",
        2,
        "message {0} {1}",
        ("val1", "val2"),
        None,
    )
    shell_formatter.format(record)
