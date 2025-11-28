"""
Unit tests for infrastructure monitoring agent.
Tests core functionality: data ingestion, anomaly detection, and output formatting.
"""

import unittest
import json
from models import InputData, Insights, Anomaly, Recommendation, ServiceStatusSummary, OutputData
from nodes import ingestion_node, analysis_node, GraphState, THRESHOLDS


class TestDataIngestion(unittest.TestCase):
    """Test data loading and validation."""
    
    def test_input_data_parsing(self):
        """Verify InputData model parses valid JSON correctly."""
        sample = {
            "timestamp": "2023-10-01T12:00:00Z",
            "cpu_usage": 85,
            "memory_usage": 70,
            "latency_ms": 250,
            "disk_usage": 65,
            "network_in_kbps": 1200,
            "network_out_kbps": 900,
            "io_wait": 5,
            "thread_count": 150,
            "active_connections": 45,
            "error_rate": 0.02,
            "uptime_seconds": 360000,
            "temperature_celsius": 65,
            "power_consumption_watts": 250,
            "service_status": {
                "database": "online",
                "api_gateway": "degraded",
                "cache": "online"
            }
        }
        
        data = InputData(**sample)
        self.assertEqual(data.cpu_usage, 85)
        self.assertEqual(data.service_status.database, "online")
    
    def test_ingestion_node_loads_data(self):
        """Verify ingestion node loads rapport.json successfully."""
        state = GraphState(
            raw_data=[],
            parsed_data=[],
            insights=None,
            anomalies=[],
            recommendations=[],
            service_status_summary=None,
            output=None
        )
        
        result = ingestion_node(state)
        self.assertGreater(len(result["parsed_data"]), 0)
        self.assertIsInstance(result["parsed_data"][0], InputData)


class TestAnomalyDetection(unittest.TestCase):
    """Test anomaly detection logic."""
    
    def test_cpu_threshold_detection(self):
        """Verify CPU anomalies are detected correctly."""
        test_data = [
            InputData(
                timestamp="2023-10-01T12:00:00Z",
                cpu_usage=95,  # Above high threshold
                memory_usage=60,
                latency_ms=100,
                disk_usage=50,
                network_in_kbps=1000,
                network_out_kbps=800,
                io_wait=3,
                thread_count=100,
                active_connections=30,
                error_rate=0.01,
                uptime_seconds=10000,
                temperature_celsius=60,
                power_consumption_watts=200,
                service_status={"database": "online", "api_gateway": "online", "cache": "online"}
            )
        ]
        
        state = GraphState(
            raw_data=[],
            parsed_data=test_data,
            insights=None,
            anomalies=[],
            recommendations=[],
            service_status_summary=None,
            output=None
        )
        
        result = analysis_node(state)
        cpu_anomalies = [a for a in result["anomalies"] if a.metric == "cpu_usage"]
        
        self.assertEqual(len(cpu_anomalies), 1)
        self.assertEqual(cpu_anomalies[0].severity, "high")
        self.assertEqual(cpu_anomalies[0].value, 95)
    
    def test_multiple_anomaly_detection(self):
        """Verify multiple simultaneous anomalies are detected."""
        test_data = [
            InputData(
                timestamp="2023-10-01T12:00:00Z",
                cpu_usage=90,
                memory_usage=85,
                latency_ms=300,
                disk_usage=50,
                network_in_kbps=1000,
                network_out_kbps=800,
                io_wait=12,
                thread_count=100,
                active_connections=30,
                error_rate=0.08,
                uptime_seconds=10000,
                temperature_celsius=80,
                power_consumption_watts=200,
                service_status={"database": "online", "api_gateway": "online", "cache": "online"}
            )
        ]
        
        state = GraphState(
            raw_data=[],
            parsed_data=test_data,
            insights=None,
            anomalies=[],
            recommendations=[],
            service_status_summary=None,
            output=None
        )
        
        result = analysis_node(state)
        
        # Should detect: CPU, memory, latency, error_rate, temperature, io_wait
        self.assertGreaterEqual(len(result["anomalies"]), 5)
        
        detected_metrics = {a.metric for a in result["anomalies"]}
        self.assertIn("cpu_usage", detected_metrics)
        self.assertIn("memory_usage", detected_metrics)
        self.assertIn("latency_ms", detected_metrics)
    
    def test_no_anomalies_when_within_thresholds(self):
        """Verify no anomalies detected when all metrics are normal."""
        test_data = [
            InputData(
                timestamp="2023-10-01T12:00:00Z",
                cpu_usage=50,
                memory_usage=60,
                latency_ms=100,
                disk_usage=50,
                network_in_kbps=1000,
                network_out_kbps=800,
                io_wait=3,
                thread_count=100,
                active_connections=30,
                error_rate=0.01,
                uptime_seconds=10000,
                temperature_celsius=60,
                power_consumption_watts=200,
                service_status={"database": "online", "api_gateway": "online", "cache": "online"}
            )
        ]
        
        state = GraphState(
            raw_data=[],
            parsed_data=test_data,
            insights=None,
            anomalies=[],
            recommendations=[],
            service_status_summary=None,
            output=None
        )
        
        result = analysis_node(state)
        self.assertEqual(len(result["anomalies"]), 0)


class TestInsightsCalculation(unittest.TestCase):
    """Test metrics aggregation and insights computation."""
    
    def test_insights_aggregation(self):
        """Verify insights are calculated correctly from multiple data points."""
        test_data = [
            InputData(
                timestamp="2023-10-01T12:00:00Z",
                cpu_usage=80,
                memory_usage=70,
                latency_ms=200,
                disk_usage=50,
                network_in_kbps=1000,
                network_out_kbps=800,
                io_wait=3,
                thread_count=100,
                active_connections=30,
                error_rate=0.02,
                uptime_seconds=10000,
                temperature_celsius=60,
                power_consumption_watts=200,
                service_status={"database": "online", "api_gateway": "online", "cache": "online"}
            ),
            InputData(
                timestamp="2023-10-01T12:30:00Z",
                cpu_usage=90,
                memory_usage=75,
                latency_ms=150,
                disk_usage=50,
                network_in_kbps=1000,
                network_out_kbps=800,
                io_wait=3,
                thread_count=100,
                active_connections=30,
                error_rate=0.03,
                uptime_seconds=11800,
                temperature_celsius=60,
                power_consumption_watts=200,
                service_status={"database": "online", "api_gateway": "online", "cache": "online"}
            )
        ]
        
        state = GraphState(
            raw_data=[],
            parsed_data=test_data,
            insights=None,
            anomalies=[],
            recommendations=[],
            service_status_summary=None,
            output=None
        )
        
        result = analysis_node(state)
        insights = result["insights"]
        
        self.assertEqual(insights.average_latency_ms, 175.0)
        self.assertEqual(insights.max_cpu_usage, 90.0)
        self.assertEqual(insights.max_memory_usage, 75.0)
        self.assertEqual(insights.uptime_seconds, 11800)


class TestServiceStatusAggregation(unittest.TestCase):
    """Test service health status tracking."""
    
    def test_service_status_prioritization(self):
        """Verify worst service status is prioritized correctly."""
        test_data = [
            InputData(
                timestamp="2023-10-01T12:00:00Z",
                cpu_usage=50,
                memory_usage=60,
                latency_ms=100,
                disk_usage=50,
                network_in_kbps=1000,
                network_out_kbps=800,
                io_wait=3,
                thread_count=100,
                active_connections=30,
                error_rate=0.01,
                uptime_seconds=10000,
                temperature_celsius=60,
                power_consumption_watts=200,
                service_status={"database": "online", "api_gateway": "degraded", "cache": "online"}
            ),
            InputData(
                timestamp="2023-10-01T12:30:00Z",
                cpu_usage=50,
                memory_usage=60,
                latency_ms=100,
                disk_usage=50,
                network_in_kbps=1000,
                network_out_kbps=800,
                io_wait=3,
                thread_count=100,
                active_connections=30,
                error_rate=0.01,
                uptime_seconds=11800,
                temperature_celsius=60,
                power_consumption_watts=200,
                service_status={"database": "offline", "api_gateway": "online", "cache": "degraded"}
            )
        ]
        
        state = GraphState(
            raw_data=[],
            parsed_data=test_data,
            insights=None,
            anomalies=[],
            recommendations=[],
            service_status_summary=None,
            output=None
        )
        
        result = analysis_node(state)
        status_summary = result["service_status_summary"]
        
        # Database should be offline (worst state)
        self.assertIn("database", status_summary.offline)
        self.assertNotIn("database", status_summary.online)
        self.assertNotIn("database", status_summary.degraded)
        
        # API gateway should be degraded
        self.assertIn("api_gateway", status_summary.degraded)
        
        # Cache should be degraded
        self.assertIn("cache", status_summary.degraded)


class TestOutputSchema(unittest.TestCase):
    """Test output data model validation."""
    
    def test_output_schema_compliance(self):
        """Verify OutputData model matches specification."""
        output_data = {
            "timestamp": "2023-10-01T12:00:00Z",
            "insights": {
                "average_latency_ms": 150.5,
                "max_cpu_usage": 90.0,
                "max_memory_usage": 80.0,
                "error_rate": 0.02,
                "uptime_seconds": 360000
            },
            "anomalies": [
                {
                    "metric": "cpu_usage",
                    "value": 90.0,
                    "threshold": 85.0,
                    "severity": "high",
                    "description": "CPU usage critical"
                }
            ],
            "recommendations": [
                {
                    "id": "rec-001",
                    "action": "scale up resources",
                    "target": "server",
                    "parameters": {"cores": 4},
                    "benefit_estimate": "30% improvement"
                }
            ],
            "service_status_summary": {
                "online": ["cache"],
                "degraded": ["api_gateway"],
                "offline": ["database"]
            }
        }
        
        output = OutputData(**output_data)
        
        self.assertEqual(output.timestamp, "2023-10-01T12:00:00Z")
        self.assertEqual(len(output.anomalies), 1)
        self.assertEqual(len(output.recommendations), 1)
        self.assertEqual(output.anomalies[0].severity, "high")


if __name__ == "__main__":
    unittest.main(verbosity=2)
