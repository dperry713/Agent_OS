# AgentOS

AgentOS is a next-generation Agent Operating System that combines a modern desktop environment, an intelligent agent framework, and a deterministic workflow engine.

## Architecture

AgentOS has been completely rewritten from the ground up using a highly-performant, decoupled client-server architecture:
- **Backend (Rust)**: High-performance core responsible for system operations, CQRS event routing, and SQLite storage. It exposes its services over a gRPC IPC layer.
- **Frontend (.NET 9 C# Avalonia UI)**: A rich, cross-platform Desktop UI using `Dock.Avalonia` for flexible panel layouts and MVVM for decoupled view logic.

## Key Features

- **CQRS Event Bus**: The backend utilizes a scalable in-memory Event and Command bus with thread-safe handler dispatch.
- **Docking Layout**: The UI leverages a fully customizable docking layout out of the box using `Dock.Avalonia`.
- **Custom Shell Replacement**: You can run AgentOS as your default Windows shell. A toggle within the UI will modify the registry to launch AgentOS on boot instead of `explorer.exe`.
- **Auto-Kill Failsafe**: If AgentOS is running as your custom shell and something goes wrong, you can press `CTRL+ALT+SHIFT+K` at any time. A low-level system hook in the Rust kernel will detect this, restore the default Windows shell, and safely restart your computer.
- **OpenTelemetry Logging**: Integrated tracing throughout the Rust backend and C# frontend for complete observability.
- **SQLite Persistence**: Fully configured database migrations and SQLx integration for persistent state management.

## Quickstart

Use the provided `start.ps1` script to build and launch both the backend kernel and the frontend UI concurrently.

### Prerequisites
- **Rust**: Latest stable version installed via `rustup`.
- **.NET 9 SDK**: Installed to build and run the Avalonia frontend.

### Running the System
```powershell
.\start.ps1
```

*(Note: The script handles cleanup automatically by terminating the backend when you close the frontend UI).*
