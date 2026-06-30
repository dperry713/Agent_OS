// src/lib.rs – Service manager placeholder

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Trait that all services must implement.
pub trait Service: Send + Sync {
    fn start(&self);
    fn stop(&self);
}

/// Simple service manager that holds services by name.
#[derive(Clone, Default)]
pub struct ServiceManager {
    services: Arc<Mutex<HashMap<String, Arc<dyn Service>>>>,
}

impl ServiceManager {
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a service with a unique name.
    pub fn register<S: Service + 'static>(&self, name: impl Into<String>, service: S) {
        let mut lock = self.services.lock().unwrap();
        lock.insert(name.into(), Arc::new(service));
    }

    /// Start all registered services.
    pub fn start_all(&self) {
        let lock = self.services.lock().unwrap();
        for (_, svc) in lock.iter() {
            svc.start();
        }
    }

    /// Stop all registered services.
    pub fn stop_all(&self) {
        let lock = self.services.lock().unwrap();
        for (_, svc) in lock.iter() {
            svc.stop();
        }
    }
}
