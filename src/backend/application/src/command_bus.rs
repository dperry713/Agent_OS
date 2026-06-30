use std::any::{Any, TypeId};
use std::collections::HashMap;
use tokio::sync::RwLock;

use crate::cqrs::{Command, CommandHandler, CqrsError};

type BoxedCommandHandler<C, R> = Box<dyn CommandHandler<C, R> + Send + Sync>;

/// In-memory command bus to route commands to their exactly one registered handler.
pub struct InMemoryCommandBus {
    // We store handlers by Command TypeId.
    // The value is an Any so we can downcast it to BoxedCommandHandler<C, R>.
    handlers: RwLock<HashMap<TypeId, Box<dyn Any + Send + Sync>>>,
}

impl Default for InMemoryCommandBus {
    fn default() -> Self {
        Self::new()
    }
}

impl InMemoryCommandBus {
    pub fn new() -> Self {
        Self {
            handlers: RwLock::new(HashMap::new()),
        }
    }

    /// Registers a handler for a specific command type. Only one handler per command is allowed.
    pub async fn register<C, R, H>(&self, handler: H) -> Result<(), CqrsError>
    where
        C: Command + 'static,
        R: 'static,
        H: CommandHandler<C, R> + Send + Sync + 'static,
    {
        let type_id = TypeId::of::<C>();
        let mut map = self.handlers.write().await;

        if map.contains_key(&type_id) {
            return Err(CqrsError::Internal(format!("Handler already registered for command type {:?}", type_id)));
        }

        let boxed_handler: BoxedCommandHandler<C, R> = Box::new(handler);
        map.insert(type_id, Box::new(boxed_handler) as Box<dyn Any + Send + Sync>);

        Ok(())
    }

    /// Dispatches a command to its registered handler.
    pub async fn dispatch<C: Command + 'static, R: 'static>(&self, command: C) -> Result<R, CqrsError> {
        let type_id = TypeId::of::<C>();
        let map = self.handlers.read().await;

        let entry = map
            .get(&type_id)
            .ok_or_else(|| CqrsError::Internal(format!("No handler registered for command type {:?}", type_id)))?;

        let handler = entry
            .downcast_ref::<BoxedCommandHandler<C, R>>()
            .ok_or_else(|| CqrsError::Internal("Handler type mismatch".to_string()))?;

        handler.handle(command).await
    }
}
