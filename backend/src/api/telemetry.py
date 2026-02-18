import os
import logging
import time
from typing import Dict, Any
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource

# Standard Logger
logger = logging.getLogger("brand-guardian-telemetry")

# Global variables for metrics
_meter = None
_token_counter = None
_audit_counter = None

def setup_telemetry():
    """
    Configures Azure Monitor with custom resource attributes and automatic instrumentation.
    """
    global _meter, _token_counter, _audit_counter
    
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if not connection_string:
        logger.warning("No APPLICATIONINSIGHTS_CONNECTION_STRING found. Telemetry is DISABLED.")
        return

    # Define resource attributes (makes filtering easy in Azure)
    resource = Resource.create({
        "service.name": "brand-guardian-api",
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development")
    })

    try:
        # 1. Configure Azure Monitor
        # This auto-instruments FastAPI, Requests, etc.
        configure_azure_monitor(
            connection_string=connection_string,
            resource=resource,
            sampling_ratio=1.0 # Capture 100% of data for now
        )
        
        # 2. Setup Custom Metrics
        _meter = metrics.get_meter("brand-guardian-meter")
        
        _token_counter = _meter.create_counter(
            name="total_tokens_used",
            description="Total number of LLM tokens consumed per agent",
            unit="1"
        )
        
        _audit_counter = _meter.create_counter(
            name="audit_decisions",
            description="Number of PASS/FAIL audit decisions",
            unit="1"
        )

        logger.info("🚀 Advanced Azure Monitor Tracking Enabled!")
        
    except Exception as e:
        logger.error(f"Failed to initialize Azure Monitor: {e}")

# --- Helper Functions for Agents ---

def track_token_usage(agent_name: str, count: int):
    """Adds to the global token counter in Azure Monitor."""
    if _token_counter:
        _token_counter.add(count, {"agent": agent_name})
        logger.debug(f"Telemetry: Tracked {count} tokens for {agent_name}")

def track_audit_decision(status: str):
    """Tracks PASS/FAIL stats in Azure Monitor."""
    if _audit_counter:
        _audit_counter.add(1, {"status": status})
        logger.debug(f"Telemetry: Tracked audit decision: {status}")

def start_agent_timer(agent_name: str):
    """Returns the current time to measure latency."""
    return time.time()

def end_agent_timer(agent_name: str, start_time: float):
    """Calculates and logs agent latency to Application Insights."""
    latency = time.time() - start_time
    # Gauges/Histograms are better for latency but standard logs also show duration
    logger.info(f"Telemetry: Agent {agent_name} took {latency:.2f}s", extra={
        "custom_dimensions": {
            "agent": agent_name,
            "latency": latency
        }
    })