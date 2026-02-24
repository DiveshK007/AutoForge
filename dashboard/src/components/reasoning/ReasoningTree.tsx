'use client';

import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { getAgentColor } from '@/lib/utils';
import type { ReasoningVisualization } from '@/lib/api';

interface ReasoningTreeProps {
  data: ReasoningVisualization | null;
}

const nodeTypes: Record<string, string> = {
  event: '#f59e0b',
  perception: '#3b82f6',
  hypothesis: '#8b5cf6',
  reasoning: '#6366f1',
  plan: '#10b981',
  action: '#ef4444',
  reflection: '#ec4899',
  result: '#22c55e',
};

export function ReasoningTree({ data }: ReasoningTreeProps) {
  const { nodes, edges } = useMemo(() => {
    if (!data || !data.nodes || data.nodes.length === 0) {
      return { nodes: [], edges: [] };
    }

    const flowNodes: Node[] = data.nodes.map((node, i) => {
      const col = Math.floor(i / 4);
      const row = i % 4;
      const color = nodeTypes[node.type] || '#6b7280';

      return {
        id: node.id,
        position: { x: col * 280 + 50, y: row * 120 + 50 },
        data: {
          label: (
            <div className="text-xs">
              <div className="font-semibold mb-1" style={{ color }}>
                {node.type.toUpperCase()}
              </div>
              <div className="text-white/80 leading-tight">{node.label}</div>
              {node.confidence !== undefined && (
                <div className="mt-1 text-[10px] text-white/50">
                  Confidence: {(node.confidence * 100).toFixed(0)}%
                </div>
              )}
            </div>
          ),
        },
        style: {
          background: 'rgba(30, 41, 59, 0.9)',
          border: `1px solid ${color}55`,
          borderRadius: '8px',
          padding: '10px',
          minWidth: '200px',
          backdropFilter: 'blur(8px)',
        },
      };
    });

    const flowEdges: Edge[] = data.edges.map((edge, i) => ({
      id: `e-${i}`,
      source: edge.source,
      target: edge.target,
      label: edge.label || '',
      animated: true,
      style: { stroke: '#6366f166', strokeWidth: 2 },
      labelStyle: { fill: '#94a3b8', fontSize: 10 },
    }));

    return { nodes: flowNodes, edges: flowEdges };
  }, [data]);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-surface-200/40">
        <div className="text-center">
          <p className="text-4xl mb-2">🧠</p>
          <p className="text-sm">No reasoning data yet</p>
          <p className="text-xs mt-1 text-surface-200/30">
            Trigger a workflow to see the reasoning tree
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full" style={{ minHeight: '400px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={20} size={1} />
        <Controls
          style={{
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            borderRadius: '8px',
            border: '1px solid rgba(99, 102, 241, 0.2)',
          }}
        />
        <MiniMap
          style={{
            backgroundColor: 'rgba(15, 23, 42, 0.8)',
            borderRadius: '8px',
            border: '1px solid rgba(99, 102, 241, 0.2)',
          }}
          nodeColor={(n) => {
            return '#6366f1';
          }}
          maskColor="rgba(15, 23, 42, 0.7)"
        />
      </ReactFlow>
    </div>
  );
}
