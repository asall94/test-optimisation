"""
Validation script for output.json schema compliance.
Ensures generated report matches specification requirements.
"""

import json
from models import OutputData


def validate_output():
    """Validate output.json against specification schema."""
    
    print("Validating output.json...")
    
    try:
        # Load generated output
        with open("output.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Validate using Pydantic model
        output = OutputData(**data)
        
        # Schema validation checks
        checks = {
            "timestamp_format": output.timestamp.endswith("Z") and "T" in output.timestamp,
            "insights_complete": all([
                output.insights.average_latency_ms >= 0,
                output.insights.max_cpu_usage >= 0,
                output.insights.max_memory_usage >= 0,
                output.insights.error_rate >= 0,
                output.insights.uptime_seconds >= 0
            ]),
            "anomalies_valid": all([
                a.severity in ["low", "medium", "high"] for a in output.anomalies
            ]),
            "recommendations_valid": all([
                len(r.id) > 0 and len(r.action) > 0 for r in output.recommendations
            ]),
            "service_status_valid": (
                isinstance(output.service_status_summary.online, list) and
                isinstance(output.service_status_summary.degraded, list) and
                isinstance(output.service_status_summary.offline, list)
            )
        }
        
        # Report results
        print("\n--- Validation Results ---")
        for check_name, passed in checks.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {check_name}")
        
        if all(checks.values()):
            print("\n✓ output.json is fully compliant with specification")
            print(f"\nMetrics:")
            print(f"  - Anomalies detected: {len(output.anomalies)}")
            print(f"  - Recommendations generated: {len(output.recommendations)}")
            print(f"  - Services online: {len(output.service_status_summary.online)}")
            print(f"  - Services degraded: {len(output.service_status_summary.degraded)}")
            print(f"  - Services offline: {len(output.service_status_summary.offline)}")
            return True
        else:
            print("\n✗ Validation failed - see errors above")
            return False
            
    except Exception as e:
        print(f"\n✗ Validation error: {str(e)}")
        return False


if __name__ == "__main__":
    validate_output()
