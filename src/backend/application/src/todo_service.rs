// src/backend/application/src/todo_service.rs – Todo service and handlers

use async_trait::async_trait;
use crate::cqrs::{Command, CommandHandler, Query, QueryHandler, CqrsError};
use crate::commands;
use crate::queries;
use backend_domain::todo::{Todo};
use backend_domain::repository::TodoRepository;
use std::sync::Arc;

/// Service that encapsulates Todo business logic.
#[derive(Clone)]
pub struct TodoService {
    repo: Arc<dyn TodoRepository>,
}

impl TodoService {
    pub fn new(repo: Arc<dyn TodoRepository>) -> Self {
        Self { repo }
    }
}

// ----- Command handlers -----

pub struct CreateTodoHandler {
    service: TodoService,
}

impl CreateTodoHandler {
    pub fn new(service: TodoService) -> Self {
        Self { service }
    }
}

#[async_trait]
impl CommandHandler<commands::CreateTodo, Todo> for CreateTodoHandler {
    async fn handle(&self, command: commands::CreateTodo) -> Result<Todo, CqrsError> {
        let todo = self.service.repo.create(&command.title).await.map_err(|e| CqrsError::Internal(e.to_string()))?;
        Ok(todo)
    }
}

pub struct UpdateTodoHandler {
    service: TodoService,
}

impl UpdateTodoHandler {
    pub fn new(service: TodoService) -> Self {
        Self { service }
    }
}

#[async_trait]
impl CommandHandler<commands::UpdateTodo, Todo> for UpdateTodoHandler {
    async fn handle(&self, command: commands::UpdateTodo) -> Result<Todo, CqrsError> {
        let mut existing = self.service.repo.get(command.id).await.map_err(|e| CqrsError::Internal(e.to_string()))?.ok_or_else(|| CqrsError::NotFound(format!("Todo {} not found", command.id)))?;
        if let Some(title) = command.title {
            existing.title = title;
        }
        if let Some(completed) = command.completed {
            existing.completed = completed;
        }
        let updated = self.service.repo.update(&existing).await.map_err(|e| CqrsError::Internal(e.to_string()))?;
        Ok(updated)
    }
}

pub struct DeleteTodoHandler {
    service: TodoService,
}

impl DeleteTodoHandler {
    pub fn new(service: TodoService) -> Self {
        Self { service }
    }
}

#[async_trait]
impl CommandHandler<commands::DeleteTodo, ()> for DeleteTodoHandler {
    async fn handle(&self, command: commands::DeleteTodo) -> Result<(), CqrsError> {
        self.service.repo.delete(command.id).await.map_err(|e| CqrsError::Internal(e.to_string()))
    }
}

// ----- Query handlers -----

pub struct GetTodoHandler {
    service: TodoService,
}

impl GetTodoHandler {
    pub fn new(service: TodoService) -> Self {
        Self { service }
    }
}

#[async_trait]
impl QueryHandler<queries::GetTodo, Option<Todo>> for GetTodoHandler {
    async fn handle(&self, query: queries::GetTodo) -> Result<Option<Todo>, CqrsError> {
        let todo = self.service.repo.get(query.id).await.map_err(|e| CqrsError::Internal(e.to_string()))?;
        Ok(todo)
    }
}

pub struct ListTodosHandler {
    service: TodoService,
}

impl ListTodosHandler {
    pub fn new(service: TodoService) -> Self {
        Self { service }
    }
}

#[async_trait]
impl QueryHandler<queries::ListTodos, Vec<Todo>> for ListTodosHandler {
    async fn handle(&self, _query: queries::ListTodos) -> Result<Vec<Todo>, CqrsError> {
        let list = self.service.repo.list().await.map_err(|e| CqrsError::Internal(e.to_string()))?;
        Ok(list)
    }
}
