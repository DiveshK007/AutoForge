"""
AutoForge GreenOps Agent — Sustainability Intelligence.

Estimates pipeline energy usage, detects inefficient workflows,
suggests optimizations, and tracks carbon efficiency.
Supports DEMO_MODE.
"""

import math
from typing import Any, Dict
from config import settings
from agents.base_agent import BaseAgent
from agents.reasoning_engine import ReasoningEngine
from models.workflows import AgentTask, Workflow

GREENOPS_SYSTEM_PROMPT = """You are a Sustainability Optimization AI in the AutoForge autonomous engineering organization.

Your responsibilities:
- Estimate CI/CD pipeline compute energy usage
- Detect inefficient workflow patterns
- Suggest optimizations to reduce carbon footprint
- Track and report sustainability metrics
- Recommend greener infrastructure configurations

Guidelines:
- Use realistic energy estimation models
- Consider CPU, memory, network, and storage usage
- Factor in cloud provider carbon intensity
- Suggest practical, implementable optimizations
- Quantify savings in kWh and CO2"""


class GreenOpsAgent(BaseAgent):
    """GreenOps Agent — sustainability and carbon optimization."""

    def __init__(self):
        super().__init__(
            agent_type="greenops",
            capabilities=[
                "energy_estimation",
                "carbon_scoring",
                "efficiency_analysis",
                "optimization_suggestions",
                "pipeline_waste_detection",
            ],
        )
        self.reasoning_engine = ReasoningEngine()

        # Carbon estimation parameters
        self.carbon_factor = settings.GREENOPS_CARBON_FACTOR  # kg CO2 per kWh
        self.cpu_power = settings.GREENOPS_CPU_POWER_DRAW  # watts per core
        self.memory_power = settings.GREENOPS_MEMORY_POWER_DRAW  # watts per GB

    async def perceive(self, task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Parse pipeline efficiency context."""
        payload = task.input_data

        # Extract or estimate pipeline metrics
        context = {
            "action": task.action,
            "project_id": payload.get("project_id"),
            "pipeline_id": payload.get("pipeline_id"),
            "pipeline_duration_seconds": payload.get("pipeline_duration", 300),
            "job_count": len(payload.get("failed_jobs", [])) or 4,
            "retry_count": payload.get("retry_count", 0),
            "cpu_cores": payload.get("cpu_cores", 2),
            "memory_gb": payload.get("memory_gb", 4),
        }

        return context

    async def reason(self, context: Dict[str, Any], prior_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze pipeline efficiency and estimate carbon footprint."""
        # ─── DEMO MODE ───
        if settings.DEMO_MODE:
            from demo.engine import get_demo_energy
            # Detect scenario from context
            retry_count = context.get("retry_count", 0)
            if retry_count > 1:
                energy = get_demo_energy("inefficient_pipeline")
            else:
                energy = get_demo_energy("pipeline_failure")
            return {
                "energy_kwh": energy.get("energy_kwh", 0.01),
                "carbon_kg": energy.get("carbon_kg", 0.000005),
                "retry_waste_kwh": energy.get("retry_waste_kwh", 0.0),
                "efficiency_score": energy.get("efficiency_score", 85),
                "optimizations": energy.get("optimizations", []),
                "waste_sources": energy.get("waste_sources", []),
                "confidence": 0.80,
                "risk_score": 0.15,
            }

        # ─── LIVE MODE ───
        # Calculate energy metrics
        duration_hours = context.get("pipeline_duration_seconds", 300) / 3600
        cpu_cores = context.get("cpu_cores", 2)
        memory_gb = context.get("memory_gb", 4)
        job_count = context.get("job_count", 4)
        retry_count = context.get("retry_count", 0)

        # Energy estimation model
        cpu_energy_kwh = (self.cpu_power * cpu_cores * duration_hours * job_count) / 1000
        memory_energy_kwh = (self.memory_power * memory_gb * duration_hours * job_count) / 1000
        total_energy_kwh = cpu_energy_kwh + memory_energy_kwh

        # Carbon estimation
        carbon_kg = total_energy_kwh * self.carbon_factor

        # Retry waste
        retry_waste_kwh = total_energy_kwh * retry_count * 0.8 if retry_count > 0 else 0

        # Efficiency score (0-100)
        base_efficiency = 100
        if retry_count > 0:
            base_efficiency -= retry_count * 15
        if duration_hours > 0.5:
            base_efficiency -= 10
        if job_count > 8:
            base_efficiency -= 10
        efficiency_score = max(0, min(100, base_efficiency))

        # Get AI optimization suggestions
        ai_analysis = await self.reasoning_engine.reason(
            system_prompt=GREENOPS_SYSTEM_PROMPT,
            context=f"""Pipeline sustainability analysis:

Duration: {context.get('pipeline_duration_seconds')}s
Jobs: {job_count}
Retries: {retry_count}
CPU cores: {cpu_cores}
Memory: {memory_gb}GB
Energy used: {total_energy_kwh:.4f} kWh
Carbon: {carbon_kg:.6f} kg CO2
Efficiency: {efficiency_score}/100

Suggest 3-5 specific optimizations to reduce energy usage and carbon footprint.""",
            output_schema={
                "optimizations": [{"suggestion": "string", "estimated_savings_percent": "float", "priority": "string"}],
                "waste_sources": [{"source": "string", "waste_percent": "float"}],
                "confidence": "float 0-1",
            },
        )

        return {
            "energy_kwh": round(total_energy_kwh, 6),
            "carbon_kg": round(carbon_kg, 8),
            "retry_waste_kwh": round(retry_waste_kwh, 6),
            "efficiency_score": efficiency_score,
            "optimizations": ai_analysis.get("optimizations", []),
            "waste_sources": ai_analysis.get("waste_sources", []),
            "confidence": ai_analysis.get("confidence", 0.75),
            "risk_score": 0.2,
        }

    async def plan(self, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "chosen_action": "report_sustainability_metrics",
            "energy_kwh": reasoning.get("energy_kwh", 0),
            "carbon_kg": reasoning.get("carbon_kg", 0),
            "efficiency_score": reasoning.get("efficiency_score", 0),
            "optimizations": reasoning.get("optimizations", []),
            "waste_sources": reasoning.get("waste_sources", []),
            "confidence": reasoning.get("confidence", 0.75),
            "risk_score": reasoning.get("risk_score", 0.2),
            "reasoning": f"Pipeline efficiency: {reasoning.get('efficiency_score', 0)}/100, Carbon: {reasoning.get('carbon_kg', 0)} kg CO2",
        }

    async def act(self, plan: Dict[str, Any], task: AgentTask, workflow: Workflow) -> Dict[str, Any]:
        """Report sustainability metrics."""
        outputs = {
            "energy_report": {
                "energy_kwh": plan.get("energy_kwh", 0),
                "carbon_kg": plan.get("carbon_kg", 0),
                "efficiency_score": plan.get("efficiency_score", 0),
                "waste_sources": plan.get("waste_sources", []),
            },
            "optimizations": plan.get("optimizations", []),
        }

        workflow.add_timeline_entry(
            "sustainability_analysis",
            agent="greenops",
            detail=f"Efficiency: {plan.get('efficiency_score', 0)}/100, Carbon: {plan.get('carbon_kg', 0):.6f} kg CO2",
            confidence=plan.get("confidence"),
        )

        return {
            "output": outputs,
            "summary": f"GreenOps: Efficiency {plan.get('efficiency_score', 0)}/100, {len(plan.get('optimizations', []))} optimizations suggested",
            "tools_used": ["energy_estimator", "carbon_calculator"],
            "confidence": plan.get("confidence", 0.75),
        }

    async def reflect(self, result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "outcome": result.get("summary", ""),
            "confidence": plan.get("confidence", 0.75),
            "extracted_skill": "pipeline_efficiency_analysis",
        }
