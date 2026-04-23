import json
import logging
import sys

_BUILTIN_ATTRS = frozenset({
    "args", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg",
    "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "taskName", "thread", "threadName",
})


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        payload: dict = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in _BUILTIN_ATTRS}
        if extra:
            payload["extra"] = extra
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(env: str) -> None:
    level = logging.DEBUG if env == "development" else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _JsonFormatter()
        if env == "production"
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logging.basicConfig(level=level, handlers=[handler], force=True)
