"""
AutoForge Reasoning Engine — Claude-powered structured reasoning.

Provides multi-strategy reasoning:
- Chain-of-thought analysis
- Tree-of-thought hypothesis branching
- Decision graph evaluation
- Risk scoring
- Confidence estimation
"""

import json
from typing import Any, Dict, List, Optional

import anthropic

from config import settings


class ReasoningEngine:
    """
    Shared reasoning engine powered by Anthropic Claude.

    Implements structured reasoning patterns:
    1. Chain-of-Thought — Linear step-by-step
    2. Tree-of-Thought — Multi-path hypothesis exploration
    3. ReAct — Reason + Act loops
    4. Reflection — Self-critique and refinement
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS

    async def reason(
        self,
        system_prompt: str,
        context: str,
        reasoning_framework: str = "chain_of_thought",
        output_schema: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute structured reasoning with Claude.

        Args:
            system_prompt: Agent role and behavior definition
            context: Task-specific context and data
            reasoning_framework: Type of reasoning to apply
            output_schema: Expected JSON output structure

        Returns:
            Structured reasoning result
        """
        # Build the reasoning prompt
        framework_prompt = self._get_framework_prompt(reasoning_framework)
        schema_prompt = self._get_schema_prompt(output_schema) if output_schema else ""

        full_prompt = f"""{context}

{framework_prompt}

{schema_prompt}

Provide your analysis now. Return your response as a valid JSON object."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": full_prompt}],
            )

            # Parse response
            response_text = response.content[0].text

            # Try to extract JSON from response
            result = self._extract_json(response_text)

            if result:
                result["_raw_response"] = response_text[:500]
                result["_model"] = self.model
                result["_reasoning_framework"] = reasoning_framework
                return result

            # If no JSON found, structure the text response
            return {
                "analysis": response_text,
                "confidence": 0.5,
                "risk_score": 0.5,
                "_raw_response": response_text[:500],
                "_model": self.model,
                "_reasoning_framework": reasoning_framework,
            }

        except anthropic.APIError as e:
            return self._fallback_reasoning(context, str(e))

    async def generate_hypotheses(
        self, system_prompt: str, context: str, max_hypotheses: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate multiple hypotheses using tree-of-thought reasoning."""
        prompt = f"""{context}

Generate exactly {max_hypotheses} hypotheses for the root cause of this issue.

For each hypothesis, provide:
1. Description of the hypothesis
2. Probability estimate (0.0 to 1.0)
3. Supporting evidence
4. Risk if this hypothesis is wrong
5. Suggested fix action

Return as a JSON array of objects with keys:
"description", "probability", "evidence", "risk_if_wrong", "suggested_action"
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            result = self._extract_json(response_text)

            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "hypotheses" in result:
                return result["hypotheses"]

            return [{"description": response_text, "probability": 0.5, "evidence": [], "risk_if_wrong": 0.5, "suggested_action": "manual_review"}]

        except anthropic.APIError:
            return self._fallback_hypotheses(context)

    async def evaluate_plan(
        self, system_prompt: str, hypotheses: List[Dict], context: str
    ) -> Dict[str, Any]:
        """Evaluate hypotheses and select the optimal action plan."""
        hypotheses_text = json.dumps(hypotheses, indent=2)

        prompt = f"""{context}

Here are the generated hypotheses:
{hypotheses_text}

Evaluate each hypothesis and select the optimal action plan.

Consider:
1. Probability of correctness
2. Risk of the fix
3. Complexity of implementation
4. Safety of the approach

Return a JSON object with:
- "chosen_hypothesis": index of selected hypothesis (0-based)
- "chosen_action": description of the action to take
- "confidence": your confidence in this plan (0.0 to 1.0)
- "risk_score": risk level of this plan (0.0 to 1.0)
- "reasoning": step-by-step justification
- "alternative_actions": list of backup strategies
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            result = self._extract_json(response_text)

            if result:
                return result

            return {
                "chosen_hypothesis": 0,
                "chosen_action": "apply_most_probable_fix",
                "confidence": 0.5,
                "risk_score": 0.5,
                "reasoning": response_text,
            }

        except anthropic.APIError:
            return {
                "chosen_hypothesis": 0,
                "chosen_action": "apply_most_probable_fix",
                "confidence": 0.4,
                "risk_score": 0.6,
                "reasoning": "Fallback to most probable hypothesis",
            }

    async def reflect(
        self, system_prompt: str, action_taken: str, outcome: str, context: str
    ) -> Dict[str, Any]:
        """Perform reflection on an action's outcome."""
        prompt = f"""Context:
{context}

Action Taken:
{action_taken}

Outcome:
{outcome}

Reflect on this action:
1. Did the action fully resolve the issue?
2. Were there any unintended side effects?
3. Could a better approach have been used?
4. What reusable skill or pattern can be extracted?
5. How confident are you in the outcome?

Return a JSON object with:
- "success": boolean
- "outcome": brief outcome description
- "side_effects": list of any side effects
- "improvement_suggestions": list of improvements
- "extracted_skill": a reusable pattern description (or null)
- "confidence": confidence in the outcome (0.0 to 1.0)
- "lesson_learned": key insight from this experience
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            result = self._extract_json(response_text)

            if result:
                return result

            return {
                "success": True,
                "outcome": response_text,
                "confidence": 0.5,
            }

        except anthropic.APIError:
            return {
                "success": True,
                "outcome": "Reflection unavailable",
                "confidence": 0.4,
            }

    # ─── Internal Helpers ───

    def _get_framework_prompt(self, framework: str) -> str:
        frameworks = {
            "chain_of_thought": """Follow this step-by-step reasoning process:
1. Identify the problem type and category
2. Analyze the available evidence
3. Determine the root cause
4. Evaluate possible solutions
5. Select the safest and most effective approach
6. Assess confidence and risk levels""",

            "tree_of_thought": """Explore multiple reasoning paths:
- Branch 1: Consider the most common cause
- Branch 2: Consider environmental factors
- Branch 3: Consider recent changes
- Branch 4: Consider dependency conflicts
For each branch, assign a probability and evaluate the evidence.""",

            "react": """Use the Reason-Act pattern:
Thought: What do I observe?
Action: What should I investigate?
Observation: What did I find?
Thought: What does this mean?
Action: What fix should I apply?""",

            "reflection": """After analysis, critically evaluate:
- Are my assumptions correct?
- What could I be missing?
- Is there a simpler explanation?
- What are the risks of my conclusion?""",
        }
        return frameworks.get(framework, frameworks["chain_of_thought"])

    def _get_schema_prompt(self, schema: Dict) -> str:
        return f"""Return your response as a JSON object matching this schema:
{json.dumps(schema, indent=2)}"""

    def _extract_json(self, text: str) -> Optional[Any]:
        """Extract JSON from a text response."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in markdown
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except json.JSONDecodeError:
                    pass

        # Try to find JSON object/array
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            if start >= 0:
                # Find matching end
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == start_char:
                        depth += 1
                    elif text[i] == end_char:
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start:i + 1])
                            except json.JSONDecodeError:
                                break

        return None

    def _fallback_reasoning(self, context: str, error: str) -> Dict[str, Any]:
        """Provide fallback reasoning when LLM is unavailable."""
        return {
            "analysis": f"Fallback analysis (LLM unavailable: {error})",
            "hypotheses": [
                {"description": "Dependency issue", "probability": 0.4},
                {"description": "Configuration error", "probability": 0.3},
                {"description": "Code syntax error", "probability": 0.3},
            ],
            "confidence": 0.3,
            "risk_score": 0.7,
            "recommendation": "manual_review_required",
            "_fallback": True,
        }

    def _fallback_hypotheses(self, context: str) -> List[Dict[str, Any]]:
        """Provide fallback hypotheses when LLM is unavailable."""
        return [
            {
                "description": "Missing or incompatible dependency",
                "probability": 0.4,
                "evidence": ["Common cause of build failures"],
                "risk_if_wrong": 0.3,
                "suggested_action": "Check and update dependencies",
            },
            {
                "description": "Configuration or environment issue",
                "probability": 0.3,
                "evidence": ["Environment differences can cause failures"],
                "risk_if_wrong": 0.4,
                "suggested_action": "Review CI configuration",
            },
            {
                "description": "Code syntax or logic error",
                "probability": 0.3,
                "evidence": ["Recent changes may contain errors"],
                "risk_if_wrong": 0.3,
                "suggested_action": "Review recent commits",
            },
        ]
