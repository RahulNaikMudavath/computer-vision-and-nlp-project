import time
import json
import uuid
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("document_ocr.json_logger")

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware capturing request durations, routes, and response statuses,
    printing telemetry logs as structured JSON lines to stdout.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        # Inject or capture Request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Capture endpoint details
        method = request.method
        path = request.url.path
        
        # Proceed with request pipeline
        try:
            response = await call_next(request)
            duration = (time.time() - start_time) * 1000
            
            # Formulate structured JSON details
            log_data = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "client_ip": request.client.host if request.client else "unknown"
            }
            
            # Inject Request-ID in Response headers
            response.headers["X-Request-ID"] = request_id
            
            # Print JSON dump string
            logger.info(json.dumps(log_data))
            return response
            
        except Exception as exc:
            duration = (time.time() - start_time) * 1000
            error_data = {
                "request_id": request_id,
                "method": method,
                "path": path,
                "duration_ms": round(duration, 2),
                "error_class": exc.__class__.__name__,
                "error_detail": str(exc),
                "client_ip": request.client.host if request.client else "unknown"
            }
            logger.error(json.dumps(error_data))
            raise exc
