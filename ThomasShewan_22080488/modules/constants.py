"""Shared constants for web health monitoring stack & Lambdas."""

# CloudWatch Namespace & Metric Names
METRIC_NAMESPACE = "WebMonitoring/Health"
METRIC_AVAILABILITY = "Availability"
METRIC_LATENCY = "Latency"
METRIC_THROUGHPUT = "Throughput"

# Dimension Names
DIM_WEBSITE = "Website"

# Default website list (name + url)
DEFAULT_WEBSITES = [
    {"name": "Google", "url": "https://www.google.com"},
    {"name": "Amazon", "url": "https://www.amazon.com"},
    {"name": "GitHub", "url": "https://www.github.com"},
]

# Environment variable keys
ENV_WEBSITES = "WEBSITES"
ENV_ALARM_LOG_TABLE = "ALARM_LOG_TABLE"

# Misc
USER_AGENT = "AWS-Lambda-Canary/1.0"
DEFAULT_TIMEOUT_SECONDS = 10

# Per-site alarm threshold configuration
# latency_ms: maximum acceptable average latency over evaluation period.
# throughput_bps_min: minimum acceptable average throughput.
THRESHOLDS = {
    "default": {"latency_ms": 1500, "throughput_bytes_per_sec_min": 200000},
    "Google": {"latency_ms": 1000, "throughput_bytes_per_sec_min": 15000},
    "Amazon": {"latency_ms": 2000, "throughput_bytes_per_sec_min": 90000},
    "GitHub": {"latency_ms": 1000, "throughput_bytes_per_sec_min": 500000},
}

def get_site_threshold(site_name: str) -> dict:
    """Return thresholds for site or default if not explicitly configured."""
    return THRESHOLDS.get(site_name, THRESHOLDS["default"])
