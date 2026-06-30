use std::any::{Any, TypeId};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::cqrs::{CqrsError, Event, EventHandler};

type BoxedEventHandler<E> = Box<dyn EventHandler<E> + Send + Sync>;
type HandlerList<E> = Vec<BoxedEventHandler<E>>;

/// In-memory event bus to dispatch domain events to their registered handlers.
pub struct InMemoryEventBus {
    // We store handlers grouped by the Event's TypeId.
    // The value is an Any so we can downcast it to the specific HandlerList<E>.
    handlers: RwLock<HashMap<TypeId, Box<dyn Any + Send + Sync>>>,
}

impl Default for InMemoryEventBus {
    fn default() -> Self {
        Self::new()
    }
}

impl InMemoryEventBus {
    pub fn new() -> Self {
        Self {
            handlers: RwLock::new(HashMap::new()),
        }
    }

    /// Registers a handler for a specific event type.
    pub async fn subscribe<E: Event + 'static, H: EventHandler<E> + Send + Sync + 'static>(&self, handler: H) {
        let type_id = TypeId::of::<E>();
        let mut map = self.handlers.write().await;

        let entry = map.entry(type_id).or_insert_with(|| {
            let list: HandlerList<E> = Vec::new();
            Box::new(list) as Box<dyn Any + Send + Sync>
        });

        if let Some(list) = entry.downcast_mut::<HandlerList<E>>() {
            list.push(Box::new(handler));
        }
    }

    /// Publishes an event to all registered handlers concurrently.
    pub async fn publish<E: Event + 'static>(&self, event: E) -> Result<(), CqrsError> {
        let type_id = TypeId::of::<E>();
        let map = self.handlers.read().await;

        if let Some(entry) = map.get(&type_id) {
            if let Some(list) = entry.downcast_ref::<HandlerList<E>>() {
                let arc_event = Arc::new(event);
                let mut futures = Vec::new();

                for handler in list {
                    futures.push(handler.handle(&arc_event));
                }

                // Wait for all handlers
                for result in futures::future::join_all(futures).await {
                    result?;
                }
            }
        }
        Ok(())
    }
}
