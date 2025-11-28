"""
LangGraph agent nodes for infrastructure monitoring analysis.

Agent Architecture:
1. Ingestion Node: Load and validate input data
2. Analysis Node: Compute insights and detect anomalies
3. LLM Enrichment Node: Generate contextual recommendations
4. Output Node: Format final JSON report

Production considerations:
- Anomaly detection uses statistical thresholds (prod: ML-based models like Isolation Forest)
- LLM for recommendations (prod: hybrid approach with rule engine + LLM fallback)
- In-memory processing (prod: streaming architecture with Kafka/Kinesis)
"""

import json
import logging
import statistics
from typing import List, Dict, Any, TypedDict
from datetime import datetime
from models import InputData, Insights, Anomaly, Recommendation, ServiceStatusSummary, OutputData
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


# Configure structured JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """State passed between workflow nodes."""
    raw_data: List[Dict[str, Any]]
    parsed_data: List[InputData]
    insights: Insights
    anomalies: List[Anomaly]
    recommendations: List[Recommendation]
    service_status_summary: ServiceStatusSummary
    output: OutputData


# Anomaly detection thresholds (business-defined SLAs)
THRESHOLDS = {
    "cpu_usage": {"high": 85, "medium": 75},
    "memory_usage": {"high": 80, "medium": 70},
    "latency_ms": {"high": 250, "medium": 180},
    "error_rate": {"high": 0.05, "medium": 0.02},
    "temperature_celsius": {"high": 75, "medium": 65},
    "io_wait": {"high": 10, "medium": 7},
}


def ingestion_node(state: GraphState) -> GraphState:
    """
    Node 1: Load and validate input data.
    Ensures data integrity before processing.
    """
    logger.info("Starting data ingestion")
    
    with open("rapport.json", "r") as f:
        raw_data = json.load(f)
    
    parsed_data = [InputData(**entry) for entry in raw_data]
    
    logger.info(f"Ingestion complete: {len(parsed_data)} snapshots loaded")
    
    state["raw_data"] = raw_data
    state["parsed_data"] = parsed_data
    return state


def analysis_node(state: GraphState) -> GraphState:
    """
    Node 2: Compute insights and detect anomalies.
    
    Insights: Aggregated metrics across all snapshots
    Anomalies: Threshold-based detection with severity scoring
    """
    logger.info("Starting analysis phase")
    data = state["parsed_data"]
    
    # Compute insights
    latencies = [d.latency_ms for d in data]
    cpu_usages = [d.cpu_usage for d in data]
    memory_usages = [d.memory_usage for d in data]
    error_rates = [d.error_rate for d in data]
    
    insights = Insights(
        average_latency_ms=round(statistics.mean(latencies), 2),
        max_cpu_usage=round(max(cpu_usages), 2),
        max_memory_usage=round(max(memory_usages), 2),
        error_rate=round(statistics.mean(error_rates), 4),
        uptime_seconds=data[-1].uptime_seconds
    )
    
    # Detect anomalies (deduplication: keep worst case per metric)
    anomaly_map: Dict[str, Anomaly] = {}
    
    for entry in data:
        # CPU anomaly
        if entry.cpu_usage > THRESHOLDS["cpu_usage"]["high"]:
            severity = "high"
            if "cpu_usage" not in anomaly_map or entry.cpu_usage > anomaly_map["cpu_usage"].value:
                anomaly_map["cpu_usage"] = Anomaly(
                    metric="cpu_usage",
                    value=entry.cpu_usage,
                    threshold=THRESHOLDS["cpu_usage"]["high"],
                    severity=severity,
                    description=f"CPU usage reached {entry.cpu_usage}% at {entry.timestamp}"
                )
        elif entry.cpu_usage > THRESHOLDS["cpu_usage"]["medium"]:
            if "cpu_usage" not in anomaly_map:
                anomaly_map["cpu_usage"] = Anomaly(
                    metric="cpu_usage",
                    value=entry.cpu_usage,
                    threshold=THRESHOLDS["cpu_usage"]["medium"],
                    severity="medium",
                    description=f"CPU usage elevated at {entry.cpu_usage}%"
                )
        
        # Memory anomaly
        if entry.memory_usage > THRESHOLDS["memory_usage"]["high"]:
            if "memory_usage" not in anomaly_map or entry.memory_usage > anomaly_map["memory_usage"].value:
                anomaly_map["memory_usage"] = Anomaly(
                    metric="memory_usage",
                    value=entry.memory_usage,
                    threshold=THRESHOLDS["memory_usage"]["high"],
                    severity="high",
                    description=f"Memory usage critical at {entry.memory_usage}%"
                )
        
        # Latency anomaly
        if entry.latency_ms > THRESHOLDS["latency_ms"]["high"]:
            if "latency_ms" not in anomaly_map or entry.latency_ms > anomaly_map["latency_ms"].value:
                anomaly_map["latency_ms"] = Anomaly(
                    metric="latency_ms",
                    value=entry.latency_ms,
                    threshold=THRESHOLDS["latency_ms"]["high"],
                    severity="high",
                    description=f"Latency spike to {entry.latency_ms}ms"
                )
        
        # Error rate anomaly
        if entry.error_rate > THRESHOLDS["error_rate"]["high"]:
            if "error_rate" not in anomaly_map or entry.error_rate > anomaly_map["error_rate"].value:
                anomaly_map["error_rate"] = Anomaly(
                    metric="error_rate",
                    value=entry.error_rate,
                    threshold=THRESHOLDS["error_rate"]["high"],
                    severity="high",
                    description=f"Error rate critical at {entry.error_rate*100}%"
                )
        
        # Temperature anomaly
        if entry.temperature_celsius > THRESHOLDS["temperature_celsius"]["high"]:
            if "temperature_celsius" not in anomaly_map or entry.temperature_celsius > anomaly_map["temperature_celsius"].value:
                anomaly_map["temperature_celsius"] = Anomaly(
                    metric="temperature_celsius",
                    value=entry.temperature_celsius,
                    threshold=THRESHOLDS["temperature_celsius"]["high"],
                    severity="high",
                    description=f"Server temperature at {entry.temperature_celsius}C"
                )
        
        # IO wait anomaly
        if entry.io_wait > THRESHOLDS["io_wait"]["high"]:
            if "io_wait" not in anomaly_map or entry.io_wait > anomaly_map["io_wait"].value:
                anomaly_map["io_wait"] = Anomaly(
                    metric="io_wait",
                    value=entry.io_wait,
                    threshold=THRESHOLDS["io_wait"]["high"],
                    severity="medium",
                    description=f"IO wait time elevated at {entry.io_wait}%"
                )
    
    # Service status aggregation
    status_tracker = {"online": set(), "degraded": set(), "offline": set()}
    for entry in data:
        for service, status in entry.service_status.model_dump().items():
            status_tracker[status].add(service)
    
    # Remove duplicates across statuses (prioritize worst state)
    if status_tracker["offline"]:
        for service in status_tracker["offline"]:
            status_tracker["degraded"].discard(service)
            status_tracker["online"].discard(service)
    if status_tracker["degraded"]:
        for service in status_tracker["degraded"]:
            status_tracker["online"].discard(service)
    
    service_status_summary = ServiceStatusSummary(
        online=sorted(list(status_tracker["online"])),
        degraded=sorted(list(status_tracker["degraded"])),
        offline=sorted(list(status_tracker["offline"]))
    )
    
    logger.info(f"Analysis complete: {len(list(anomaly_map.values()))} anomalies detected")
    
    state["insights"] = insights
    state["anomalies"] = list(anomaly_map.values())
    state["service_status_summary"] = service_status_summary
    return state


def llm_enrichment_node(state: GraphState) -> GraphState:
    """
    Node 3: Generate contextual recommendations using LLM.
    
    Leverages OpenAI to produce business-oriented, actionable recommendations
    based on detected anomalies and infrastructure patterns.
    """
    logger.info("Starting LLM enrichment phase")
    
    anomalies = state["anomalies"]
    insights = state["insights"]
    
    # Build context for LLM
    anomaly_summary = "\n".join([
        f"- {a.metric}: {a.value} (threshold: {a.threshold}, severity: {a.severity})"
        for a in anomalies
    ])
    
    system_prompt = """You are an infrastructure optimization expert for a French SME.
Generate 3-5 precise technical recommendations based on detected anomalies.
Each recommendation must be actionable, specific, and estimate business impact.

Respond ONLY with valid JSON (no markdown, no code blocks):
[
  {
    "id": "rec-001",
    "action": "specific technical action",
    "target": "affected component",
    "parameters": {"key": "value"},
    "benefit_estimate": "quantified business benefit"
  }
]"""
    
    user_prompt = f"""Infrastructure analysis summary:

Anomalies detected:
{anomaly_summary if anomaly_summary else "No critical anomalies"}

Key metrics:
- Average latency: {insights.average_latency_ms}ms
- Max CPU: {insights.max_cpu_usage}%
- Max memory: {insights.max_memory_usage}%
- Error rate: {insights.error_rate*100}%

Generate optimization recommendations in JSON format."""
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    # Parse LLM response
    recommendations_data = json.loads(response.content)
    recommendations = [Recommendation(**rec) for rec in recommendations_data]
    
    logger.info(f"LLM enrichment complete: {len(recommendations)} recommendations generated")
    
    state["recommendations"] = recommendations
    return state


def output_node(state: GraphState) -> GraphState:
    """
    Node 4: Format and export final analysis report.
    """
    logger.info("Generating output report")
    
    output = OutputData(
        timestamp=datetime.utcnow().isoformat() + "Z",
        insights=state["insights"],
        anomalies=state["anomalies"],
        recommendations=state["recommendations"],
        service_status_summary=state["service_status_summary"]
    )
    
    # Write to output.json
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
    
    logger.info("Output report saved to output.json")
    
    state["output"] = output
    return state
