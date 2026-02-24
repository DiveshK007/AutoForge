'use client';

import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { getAgentColor, getAgentIcon } from '@/lib/utils';

interface CommLink {
  from: string;
  to: string;
  dataType: string;
  volume: number; // 0-1 normalized
}

interface AgentCommGraphProps {
  agents: string[];
  links: CommLink[];
}

/**
 * Agent-to-Agent Communication Visualization.
 * Shows data flow between agents in the shared context bus.
 */
export function AgentCommGraph({ agents, links }: AgentCommGraphProps) {
  const { nodes, edges } = useMemo(() => {
    const angleStep = (2 * Math.PI) / agents.length;
    const radius = 200;
    const centerX = 300;
    const centerY = 250;

    const flowNodes: Node[] = agents.map((agent, i) => {
      const angle = angleStep * i - Math.PI / 2;
      return {
        id: agent,
        position: {
          x: centerX + radius * Math.cos(angle) - 50,
          y: centerY + radius * Math.sin(angle) - 25,
        },
        data: {
          label: (
            <div className="flex items-center gap-2 px-3 py-2">
              <span className="text-lg">{getAgentIcon(agent)}</span>
              <div>
                <div className="text-xs font-bold text-white uppercase">{agent}</div>
                <div className="text-[10px] text-surface-200/50">Agent</div>
              </div>
            </div>
          ),
        },
        style: {
          background: `${getAgentColor(agent)}22`,
          border: `2px solid ${getAgentColor(agent)}`,
          borderRadius: '12px',
          padding: 0,
          width: 120,
        },
      };
    });

    const flowEdges: Edge[] = links.map((link, i) => ({
      id: `e-${i}`,
      source: link.from,
      target: link.to,
      label: link.dataType,
      animated: link.volume > 0.5,
      style: {
        stroke: getAgentColor(link.from),
        strokeWidth: Math.max(1, link.volume * 4),
        opacity: 0.4 + link.volume * 0.6,
      },
      labelStyle: {
        fontSize: 9,
        fill: '#94a3b8',
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: getAgentColor(link.from),
      },
    }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [agents, links]);

  return (
    <div className="h-[500px] rounded-lg overflow-hidden bg-surface-900/40" role="img" aria-label="Agent communication graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={20} />
        <Controls
          showInteractive={false}
          className="!bg-surface-800/80 !border-surface-700/50 !rounded-lg"
        />
      </ReactFlow>
    </div>
  );
}

/**
 * Demo data for the communication graph.
 */
export const DEMO_COMM_LINKS: CommLink[] = [
  { from: 'sre', to: 'security', dataType: 'fix_patch', volume: 0.9 },
  { from: 'sre', to: 'qa', dataType: 'fix_branch', volume: 0.85 },
  { from: 'sre', to: 'greenops', dataType: 'pipeline_data', volume: 0.5 },
  { from: 'security', to: 'review', dataType: 'scan_result', volume: 0.7 },
  { from: 'security', to: 'qa', dataType: 'vuln_context', volume: 0.4 },
  { from: 'qa', to: 'review', dataType: 'test_results', volume: 0.8 },
  { from: 'qa', to: 'docs', dataType: 'coverage_report', volume: 0.5 },
  { from: 'review', to: 'docs', dataType: 'review_notes', volume: 0.75 },
  { from: 'greenops', to: 'docs', dataType: 'carbon_report', volume: 0.4 },
  { from: 'greenops', to: 'sre', dataType: 'optimization', volume: 0.3 },
];
