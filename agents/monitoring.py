"""
Monitoring and metrics module for Tweet AI agent
"""
import time
import uuid
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from functools import wraps
from contextlib import contextmanager
from threading import local

# Thread-local storage for correlation IDs
_thread_local = local()

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    correlation_id: str
    node_name: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    response_size: int = 0
    retry_count: int = 0
    
    @property
    def duration_ms(self) -> float:
        """Duration of the request in milliseconds"""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion to dictionary for logging"""
        return {
            "correlation_id": self.correlation_id,
            "node_name": self.node_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_message": self.error_message,
            "tokens_used": self.tokens_used,
            "response_size": self.response_size,
            "retry_count": self.retry_count
        }


@dataclass
class AggregateMetrics:
    """Aggregated metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    total_tokens_used: int = 0
    total_retries: int = 0
    node_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful requests"""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def average_duration_ms(self) -> float:
        """Average duration of the request"""
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests
    
    @property
    def average_tokens_per_request(self) -> float:
        """Average number of tokens per request"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_tokens_used / self.successful_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion to dictionary"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate_percent": round(self.success_rate, 2),
            "average_duration_ms": round(self.average_duration_ms, 2),
            "total_tokens_used": self.total_tokens_used,
            "average_tokens_per_request": round(self.average_tokens_per_request, 2),
            "total_retries": self.total_retries,
            "node_metrics": self.node_metrics
        }


class MetricsCollector:
    """Metrics collector"""
    
    def __init__(self):
        self._metrics: List[RequestMetrics] = []
        self._active_requests: Dict[str, RequestMetrics] = {}
    
    def start_request(self, node_name: str, correlation_id: Optional[str] = None) -> str:
        """Start tracking the request"""
        if correlation_id is None:
            correlation_id = generate_correlation_id()
        
        metrics = RequestMetrics(
            correlation_id=correlation_id,
            node_name=node_name,
            start_time=time.time()
        )
        
        self._active_requests[correlation_id] = metrics
        set_correlation_id(correlation_id)
        
        logger.info(f"Started request", extra={
            "correlation_id": correlation_id,
            "node_name": node_name
        })
        
        return correlation_id
    
    def end_request(self, correlation_id: str, success: bool = True, 
                   error_message: Optional[str] = None, tokens_used: Optional[int] = None,
                   response_size: int = 0, retry_count: int = 0):
        """End tracking the request"""
        if correlation_id not in self._active_requests:
            logger.warning(f"Request not found for correlation_id: {correlation_id}")
            return
        
        metrics = self._active_requests.pop(correlation_id)
        metrics.end_time = time.time()
        metrics.success = success
        metrics.error_message = error_message
        metrics.tokens_used = tokens_used
        metrics.response_size = response_size
        metrics.retry_count = retry_count
        
        self._metrics.append(metrics)
        
        logger.info(f"Completed request", extra=metrics.to_dict())
    
    def get_aggregate_metrics(self) -> AggregateMetrics:
        """Get aggregated metrics"""
        aggregate = AggregateMetrics()
        
        for metric in self._metrics:
            aggregate.total_requests += 1
            aggregate.total_duration_ms += metric.duration_ms
            aggregate.total_retries += metric.retry_count
            
            if metric.success:
                aggregate.successful_requests += 1
                if metric.tokens_used:
                    aggregate.total_tokens_used += metric.tokens_used
            else:
                aggregate.failed_requests += 1
            
            # Node metrics
            node_name = metric.node_name
            if node_name not in aggregate.node_metrics:
                aggregate.node_metrics[node_name] = {
                    "requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "total_duration_ms": 0.0,
                    "total_tokens": 0,
                    "retries": 0
                }
            
            node_stats = aggregate.node_metrics[node_name]
            node_stats["requests"] += 1
            node_stats["total_duration_ms"] += metric.duration_ms
            node_stats["retries"] += metric.retry_count
            
            if metric.success:
                node_stats["successful"] += 1
                if metric.tokens_used:
                    node_stats["total_tokens"] += metric.tokens_used
            else:
                node_stats["failed"] += 1
        
        return aggregate
    
    def clear_metrics(self):
        """Clear collected metrics"""
        self._metrics.clear()
        self._active_requests.clear()
    
    def get_recent_metrics(self, limit: int = 10) -> List[RequestMetrics]:
        """Get the last N metrics"""
        return self._metrics[-limit:]


# Global metrics collector
_metrics_collector = MetricsCollector()


def generate_correlation_id() -> str:
    """Generate a unique correlation ID"""
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from thread-local storage"""
    return getattr(_thread_local, 'correlation_id', None)


def set_correlation_id(correlation_id: str):
    """Set the correlation ID in thread-local storage"""
    _thread_local.correlation_id = correlation_id


@contextmanager
def track_request(node_name: str, correlation_id: Optional[str] = None):
    """Context manager for tracking the request"""
    cid = _metrics_collector.start_request(node_name, correlation_id)
    try:
        yield cid
        _metrics_collector.end_request(cid, success=True)
    except Exception as e:
        _metrics_collector.end_request(cid, success=False, error_message=str(e))
        raise


def update_request_tokens(correlation_id: str, tokens_used: int):
    """Update the information about tokens for the request"""
    # Find the active or completed request
    collector = get_metrics_collector()
    if correlation_id in collector._active_requests:
        collector._active_requests[correlation_id].tokens_used = tokens_used
    else:
        # Search among the completed requests (the last one with such correlation_id)
        for metric in reversed(collector._metrics):
            if metric.correlation_id == correlation_id:
                metric.tokens_used = tokens_used
                break


def with_monitoring(node_name: str):
    """Decorator for automatic monitoring of functions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            correlation_id = get_correlation_id()
            with track_request(node_name, correlation_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def log_metrics_summary():
    """Log the metrics summary"""
    metrics = _metrics_collector.get_aggregate_metrics()
    logger.info("Metrics Summary", extra=metrics.to_dict())


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector"""
    return _metrics_collector


# Setup JSON formatting for logs
class CorrelationLogFormatter(logging.Formatter):
    """Formatter for logs with correlation ID"""
    
    def format(self, record):
        # Add correlation_id to each log record
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = get_correlation_id()
        
        return super().format(record)


def setup_monitoring_logging():
    """Setup logging with correlation IDs"""
    # Create formatter
    formatter = CorrelationLogFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
    )
    
    # Setup handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    # Setup logger
    monitoring_logger = logging.getLogger('agents')
    monitoring_logger.setLevel(logging.INFO)
    monitoring_logger.addHandler(handler)
    
    return monitoring_logger