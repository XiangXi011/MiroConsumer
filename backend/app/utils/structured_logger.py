"""结构化日志工具"""

import json
import logging
from flask import request, g


class StructuredFormatter(logging.Formatter):
    """JSON 结构化日志格式"""

    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 请求上下文
        try:
            if request:
                log_data["request_id"] = getattr(g, "request_id", None)
                log_data["method"] = request.method
                log_data["path"] = request.path
                log_data["remote_addr"] = request.remote_addr
        except RuntimeError:
            pass

        # 异常信息
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_structured_logger(app):
    """为 Flask app 设置结构化日志"""
    formatter = StructuredFormatter()

    for handler in app.logger.handlers:
        handler.setFormatter(formatter)

    app.logger.info("结构化日志已启用")
