'use client';

import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { getAgentColor, getAgentIcon } from '@/lib/utils';

interface DagTask {
  task_id: string;
  agent_type: string;
  action: string;
  status: string;
  dependencies: string[];
  wave?: number;
}

interface DAGViewProps {
  tasks: DagTask[];
}

export function DAGView({ tasks }: DAGViewProps) {
  const { nodes, edges } = useMemo(() => {
    if (!tasks || tasks.length === 0) return { nodes: [], edges: [] };

    // Group tasks by wave (computed from dependencies)
    const taskMap = new Map(tasks.map(t => [t.task_id, t]));
    const waves: Map<number, DagTask[]> = new Map();

    // Compute wave for each task
    const taskWave = new Map<string, number>();
    const computeWave = (taskId: string): number => {
      if (taskWave.has(taskId)) return taskWave.get(taskId)!;
      const task = taskMap.get(taskId);
      if (!task || task.dependencies.length === 0) {
        taskWave.set(taskId, 0);
        return 0;
      }
      const maxDepWave = Math.max(
        ...task.dependencies.map(d => computeWave(d))
      );
      const wave = maxDepWave + 1;
      taskWave.set(taskId, wave);
      return wave;
    };

    tasks.forEach(t => computeWave(t.task_id));

    // Group by wave
    tasks.forEach(t => {
      const w = taskWave.get(t.task_id) || 0;
      if (!waves.has(w)) waves.set(w, []);
      waves.get(w)!.push(t);
    });

    const statusColors: Record<string, string> = {
      completed: '#22c55e',
      running: '#3b82f6',
      pending: '#6b7280',
      failed: '#ef4444',
    };

    const flowNodes: Node[] = [];
    const flowEdges: Edge[] = [];

    // Layout: waves go left→right, tasks within wave go top→bottom
    const sortedWaves = Array.from(waves.keys()).sort();
    sortedWaves.forEach(waveIdx => {
      const waveTasks = waves.get(waveIdx)!;
      waveTasks.forEach((task, taskIdx) => {
        const agentColor = getAgentColor(task.agent_type);
        const statusColor = statusColors[task.status] || '#6b7280';
        const icon = getAgentIcon(task.agent_type);

        flowNodes.push({
          id: task.task_id,
          position: { x: waveIdx * 300 + 50, y: taskIdx * 140 + 50 },
          data: {
            label: (
              <div className="text-xs p-1">
                <div className="flex items-center gap-1 mb-1">
                  <span>{icon}</span>
                  <span className="font-bold uppercase tracking-wider" style={{ color: agentColor }}>
                    {task.agent_type}
                  </span>
                </div>
                <div className="text-white/70 text-[11px]">{task.action}</div>
                <div className="mt-1 flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: statusColor }} />
                  <span className="text-[10px] text-white/50">{task.status}</span>
                </div>
                <div className="text-[9px] text-white/30 mt-0.5">Wave {waveIdx}</div>
              </div>
            ),
          },
          style: {
            background: 'rgba(30, 41, 59, 0.95)',
            border: `2px solid ${agentColor}`,
            borderRadius: '12px',
            padding: '8px',
            minWidth: 160,
          },
        });

        // Edges from dependencies
        task.dependencies.forEach(depId => {
          flowEdges.push({
            id: `e_${depId}_${task.task_id}`,
            source: depId,
            target: task.task_id,
            animated: task.status === 'running',
            style: { stroke: agentColor, strokeWidth: 2 },
            type: 'smoothstep',
          });
        });
      });
    });

    return { nodes: flowNodes, edges: flowEdges };
  }, [tasks]);

  if (!tasks || tasks.length === 0) {
    return (
      <div className="text-center py-8 text-surface-200/40">
        <p className="text-sm">No DAG data available</p>
      </div>
    );
  }

  return (
    <div className="w-full h-[400px] rounded-xl overflow-hidden border border-white/5">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1e293b" gap={20} />
        <Controls
          className="!bg-surface-800 !border-white/10 !rounded-lg"
          showInteractive={false}
        />
      </ReactFlow>
    </div>
  );
}
