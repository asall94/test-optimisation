"""
Infrastructure Monitoring & Optimization Agent

Multi-node LangGraph agent for autonomous infrastructure analysis:
1. Data ingestion and validation
2. Statistical analysis and anomaly detection  
3. LLM-powered recommendation generation
4. Structured JSON report output

Technical choices:
- LangGraph: Orchestrates agent nodes with state management
- Pydantic: Enforces schema validation (input/output integrity)
- OpenAI GPT-4: Generates contextual, business-oriented recommendations
- Python: Rapid development with strong data processing ecosystem

Usage:
1. Set OPENAI_API_KEY in .env file
2. Run: python main.py
3. Output: output.json
"""

import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from nodes import (
    GraphState,
    ingestion_node,
    analysis_node,
    llm_enrichment_node,
    output_node
)


def create_workflow() -> StateGraph:
    """
    Builds the LangGraph agent with 4 sequential nodes.
    
    Agent Flow: Ingestion -> Analysis -> LLM Enrichment -> Output
    """
    workflow = StateGraph(GraphState)
    
    # Define nodes
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("llm_enrichment", llm_enrichment_node)
    workflow.add_node("generate_output", output_node)
    
    # Define edges (sequential processing)
    workflow.set_entry_point("ingestion")
    workflow.add_edge("ingestion", "analysis")
    workflow.add_edge("analysis", "llm_enrichment")
    workflow.add_edge("llm_enrichment", "generate_output")
    workflow.add_edge("generate_output", END)
    
    return workflow.compile()


def main():
    """Execute the monitoring agent."""
    # Load environment variables
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not found. Create .env file with API key.")
    
    print("Starting infrastructure monitoring agent...")
    
    # Initialize and run agent
    app = create_workflow()
    
    # Execute with empty initial state
    result = app.invoke({
        "raw_data": [],
        "parsed_data": [],
        "insights": None,
        "anomalies": [],
        "recommendations": [],
        "service_status_summary": None,
        "output": None
    })
    
    print(f"\nAgent execution completed successfully.")
    print(f"Processed {len(result['parsed_data'])} data points")
    print(f"Detected {len(result['anomalies'])} anomalies")
    print(f"Generated {len(result['recommendations'])} recommendations")
    print(f"\nOutput saved to: output.json")


if __name__ == "__main__":
    main()
