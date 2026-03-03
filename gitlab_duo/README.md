# AutoForge — GitLab Duo Agent Platform Configuration
#
# This directory contains the agent prompts and flow YAML configs
# designed for the GitLab AI Hackathon.
#
# ## Structure
#
# ```
# gitlab_duo/
# ├── README.md              ← You are here
# ├── agents/                ← System prompts for custom agents
# │   ├── sre_agent_prompt.md
# │   ├── security_agent_prompt.md
# │   └── greenops_agent_prompt.md
# └── flows/                 ← Flow Registry v1 YAML configs
#     ├── autoforge_sre_flow.yaml
#     ├── autoforge_security_flow.yaml
#     └── autoforge_greenops_flow.yaml
# ```
#
# ## How to Register
#
# ### Agents (via GitLab UI)
# 1. Go to your project → Automate → Agents → New Agent
# 2. Name: "AutoForge SRE Agent" (or Security/GreenOps)
# 3. Paste the system prompt from agents/*.md
# 4. Select the tools listed in the prompt file
# 5. Set visibility to Public
# 6. Enable in your project
#
# ### Flows (via GitLab UI)
# 1. Go to your project → Automate → Flows → New Flow
# 2. Name: "AutoForge SRE — Pipeline Fix" (or Security/GreenOps)
# 3. Paste the YAML from flows/*.yaml
# 4. Set visibility to Public
# 5. Enable in your project with triggers:
#    - Mention (when you @mention the service account)
#    - Assign (when you assign the service account)
#    - Assign reviewer (for security review flow)
#
# ## Prize Targeting
#
# | Flow/Agent | Target Prizes |
# |------------|---------------|
# | SRE Flow | Grand Prize, Most Technically Impressive, Anthropic Prize |
# | Security Flow | Most Impactful, Anthropic Prize |
# | GreenOps Flow | Green Agent Prize ($3K), Sustainable Design Bonus ($500×4) |
# | All Combined | Grand Prize ($15K) — multi-agent orchestration |
