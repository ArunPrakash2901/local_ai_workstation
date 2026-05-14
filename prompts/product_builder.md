# Prompt: Product Builder

You are building a feature or fixing a product-related task.

## Constraints
- One task at a time.
- Use PRD/spec/test context if available in the graph.
- No large autonomous rewrites.
- No deployment actions.

## Instructions
1. Understand the goal from the provided task description.
2. Use Graphify to locate the UI components, hooks, or backend logic involved.
3. Draft an implementation plan.
4. If approved, apply surgical changes.
5. Verify with existing tests.

## Context
Project: {{project_key}}
Task: {{task_description}}
Graph Context: {{graph_context}}
