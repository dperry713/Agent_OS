from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

class MetricsManager:
    """Central manager for Prometheus metrics."""
    def __init__(self):
        self.registry = CollectorRegistry()
        
        self.task_requests_total = Counter(
            "agent_os_task_requests_total",
            "Total number of task requests",
            ["tenant_id", "agent_id", "status"],
            registry=self.registry
        )
        
        self.task_execution_seconds = Histogram(
            "agent_os_task_execution_seconds",
            "Histogram of task execution time",
            ["tenant_id", "agent_id"],
            registry=self.registry
        )

        self.tool_execution_total = Counter(
            "agent_os_tool_execution_total",
            "Total number of tool executions",
            ["tenant_id", "tool_name", "status"],
            registry=self.registry
        )

        self.sandbox_errors_total = Counter(
            "agent_os_sandbox_errors_total",
            "Total number of sandbox environment errors",
            ["tenant_id", "error_type"],
            registry=self.registry
        )

    def get_latest_metrics(self) -> Response:
        return Response(generate_latest(self.registry), media_type=CONTENT_TYPE_LATEST)

metrics = MetricsManager()
