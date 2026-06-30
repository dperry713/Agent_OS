use async_trait::async_trait;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum CqrsError {
    #[error("Internal processing error: {0}")]
    Internal(String),
    #[error("Validation error: {0}")]
    Validation(String),
    #[error("Not found: {0}")]
    NotFound(String),
}

/// Base trait for Commands (actions that mutate state).
pub trait Command: Send + Sync {}

/// Base trait for Queries (actions that only read state).
pub trait Query: Send + Sync {}

/// Base trait for Events (domain events emitted after state changes).
pub trait Event: Send + Sync {}

/// Handler for a specific Command.
#[async_trait]
pub trait CommandHandler<C: Command, R> {
    async fn handle(&self, command: C) -> Result<R, CqrsError>;
}

/// Handler for a specific Query.
#[async_trait]
pub trait QueryHandler<Q: Query, R> {
    async fn handle(&self, query: Q) -> Result<R, CqrsError>;
}

/// Handler for a specific Event.
#[async_trait]
pub trait EventHandler<E: Event> {
    async fn handle(&self, event: &E) -> Result<(), CqrsError>;
}
