"""
Structured logging with context propagation for multi-tenant tracing.

Uses contextvars for async-safe metadata propagation (tenant_id, request_id, interview_id).
Outputs JSON lines for easy ingestion by log aggregation tools.
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Any

# === Context Variables (async-safe metadata carriers) ===
_tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_interview_id_var: ContextVar[Optional[str]] = ContextVar("interview_id", default=None)
_agent_name_var: ContextVar[Optional[str]] = ContextVar("agent_name", default=None)


# === Context Setters ===

def set_tenant_id(tenant_id: str):
    _tenant_id_var.set(tenant_id)

def set_request_id(request_id: str):
    _request_id_var.set(request_id)

def set_interview_id(interview_id: str):
    _interview_id_var.set(interview_id)

def set_agent_name(name: str):
    _agent_name_var.set(name)


# === Context Getters ===

def get_tenant_id() -> Optional[str]:
    return _tenant_id_var.get()

def get_request_id() -> Optional[str]:
    return _request_id_var.get()

def get_interview_id() -> Optional[str]:
    return _interview_id_var.get()


# === Context Manager ===

class LogContext:
    """Context manager to set multiple log metadata at once."""

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        interview_id: Optional[str] = None,
        agent_name: Optional[str] = None,
    ):
        self.tenant_id = tenant_id
        self.request_id = request_id
        self.interview_id = interview_id
        self.agent_name = agent_name
        self._reset_tokens = []

    def __enter__(self):
        if self.tenant_id is not None:
            self._reset_tokens.append(_tenant_id_var.set(self.tenant_id))
        if self.request_id is not None:
            self._reset_tokens.append(_request_id_var.set(self.request_id))
        if self.interview_id is not None:
            self._reset_tokens.append(_interview_id_var.set(self.interview_id))
        if self.agent_name is not None:
            self._reset_tokens.append(_agent_name_var.set(self.agent_name))
        return self

    def __exit__(self, *args):
        for token in reversed(self._reset_tokens):
            _tenant_id_var.reset(token) if self.tenant_id is not None else None

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *args):
        self.__exit__(*args)


# === JSON Formatter ===

class JsonFormatter(logging.Formatter):
    """Format log records as JSON lines with context metadata."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": _request_id_var.get(),
            "tenant_id": _tenant_id_var.get(),
            "interview_id": _interview_id_var.get(),
            "agent": _agent_name_var.get(),
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        extras = getattr(record, "extras", None)
        if extras:
            log_entry["extras"] = extras

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# === Logger Factory ===

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """Get or create a structured logger."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    _loggers[name] = logger
    return logger


# === Structured Logging Helper ===

class StructuredLogger:
    """Logger wrapper that adds extra metadata fields."""

    def __init__(self, name: str):
        self._logger = get_logger(name)

    def _log(self, level: int, msg: str, **extras):
        record = self._logger.makeRecord(
            self._logger.name, level, "", 0, msg, (), None
        )
        if extras:
            record.extras = extras  # type: ignore
        self._logger.handle(record)

    def debug(self, msg: str, **extras):
        self._log(logging.DEBUG, msg, **extras)

    def info(self, msg: str, **extras):
        self._log(logging.INFO, msg, **extras)

    def warning(self, msg: str, **extras):
        self._log(logging.WARNING, msg, **extras)

    def error(self, msg: str, **extras):
        self._log(logging.ERROR, msg, **extras)

    def exception(self, msg: str, **extras):
        self._logger.exception(msg, extra={"extras": extras} if extras else {})


# === Convenience accessor ===

def get_structured_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
