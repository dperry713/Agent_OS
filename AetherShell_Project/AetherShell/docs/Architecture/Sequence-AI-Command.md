# Sequence: AI Command Flow

1. User triggers Command Palette (hotkey/voice)
2. Query routed to SupervisorAgent
3. Supervisor decomposes task (planning)
4. RAG retrieves context from Memory
5. Tools/Plugins executed via Semantic Kernel
6. Response rendered in UI / spoken / widget updated
7. Telemetry recorded

This pattern ensures deterministic yet intelligent behavior.