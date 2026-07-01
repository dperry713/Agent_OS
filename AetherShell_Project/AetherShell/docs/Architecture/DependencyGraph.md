# Dependency Graph (High-Level)

Core → (nothing)
AI → Core
Shell → Core + App
App → Core + Shell + AI
Plugins → Core

No cycles. All dependencies flow inward to Core (Clean Architecture).

Last Updated: Session 1