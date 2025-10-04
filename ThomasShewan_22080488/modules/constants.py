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
