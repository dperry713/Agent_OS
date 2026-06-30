use std::any::{Any, TypeId};
use std::collections::HashMap;
use tokio::sync::RwLock;

use crate::cqrs::{CqrsError, Query, QueryHandler};

type BoxedQueryHandler<Q, R> = Box<dyn QueryHandler<Q, R> + Send + Sync>;

/// In-memory query bus to route queries to their exactly one registered handler.
pub struct InMemoryQueryBus {
    // We store handlers by Query TypeId.
    // The value is an Any so we can downcast it to BoxedQueryHandler<Q, R>.
    handlers: RwLock<HashMap<TypeId, Box<dyn Any + Send + Sync>>>,
}

impl Default for InMemoryQueryBus {
    fn default() -> Self {
        Self::new()
    }
}

impl InMemoryQueryBus {
    pub fn new() -> Self {
        Self {
            handlers: RwLock::new(HashMap::new()),
        }
    }

    /// Registers a handler for a specific query type. Only one handler per query is allowed.
    pub async fn register<Q, R, H>(&self, handler: H) -> Result<(), CqrsError>
    where
        Q: Query + 'static,
        R: 'static,
        H: QueryHandler<Q, R> + Send + Sync + 'static,
    {
        let type_id = TypeId::of::<Q>();
        let mut map = self.handlers.write().await;

        if map.contains_key(&type_id) {
            return Err(CqrsError::Internal(format!("Handler already registered for query type {:?}", type_id)));
        }

        let boxed_handler: BoxedQueryHandler<Q, R> = Box::new(handler);
        map.insert(type_id, Box::new(boxed_handler) as Box<dyn Any + Send + Sync>);

        Ok(())
    }

    /// Dispatches a query to its registered handler.
    pub async fn dispatch<Q: Query + 'static, R: 'static>(&self, query: Q) -> Result<R, CqrsError> {
        let type_id = TypeId::of::<Q>();
        let map = self.handlers.read().await;

        let entry = map
            .get(&type_id)
            .ok_or_else(|| CqrsError::Internal(format!("No handler registered for query type {:?}", type_id)))?;

        let handler = entry
            .downcast_ref::<BoxedQueryHandler<Q, R>>()
            .ok_or_else(|| CqrsError::Internal("Handler type mismatch".to_string()))?;

        handler.handle(query).await
    }
}
