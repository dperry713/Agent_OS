// src/repository.rs – Todo repository trait and SQLite implementation

use async_trait::async_trait;
use sqlx::{SqlitePool, Row};
use crate::todo::Todo;

#[async_trait]
pub trait TodoRepository: Clone + Send + Sync + 'static {
    async fn create(&self, title: &str) -> Result<Todo, sqlx::Error>;
    async fn get(&self, id: i64) -> Result<Option<Todo>, sqlx::Error>;
    async fn list(&self) -> Result<Vec<Todo>, sqlx::Error>;
    async fn update(&self, todo: &Todo) -> Result<Todo, sqlx::Error>;
    async fn delete(&self, id: i64) -> Result<(), sqlx::Error>;
}

#[derive(Clone)]
pub struct SqliteTodoRepository {
    pool: SqlitePool,
}

impl SqliteTodoRepository {
    pub fn new(pool: SqlitePool) -> Self {
        Self { pool }
    }
}

#[async_trait]
impl TodoRepository for SqliteTodoRepository {
    async fn create(&self, title: &str) -> Result<Todo, sqlx::Error> {
        let rec = sqlx::query!(
            "INSERT INTO todos (title, completed) VALUES (?1, false) RETURNING id, title, completed, priority, status",
            title
        )
        .fetch_one(&self.pool)
        .await?;
        Ok(Todo {
            id: rec.id,
            title: rec.title,
            completed: rec.completed != 0,
            priority: rec.priority.parse().unwrap_or(crate::todo::Priority::Medium),
            status: rec.status.parse().unwrap_or(crate::todo::Status::Pending),
        })
    }

    async fn get(&self, id: i64) -> Result<Option<Todo>, sqlx::Error> {
        let rec = sqlx::query!(
            "SELECT id, title, completed, priority, status FROM todos WHERE id = ?1",
            id
        )
        .fetch_optional(&self.pool)
        .await?;
        Ok(rec.map(|r| Todo {
            id: r.id,
            title: r.title,
            completed: r.completed != 0,
            priority: r.priority.parse().unwrap_or(crate::todo::Priority::Medium),
            status: r.status.parse().unwrap_or(crate::todo::Status::Pending),
        }))
    }

    async fn list(&self) -> Result<Vec<Todo>, sqlx::Error> {
        let rows = sqlx::query!("SELECT id, title, completed, priority, status FROM todos")
            .fetch_all(&self.pool)
            .await?;
        Ok(rows
            .into_iter()
            .map(|r| Todo {
                id: r.id,
                title: r.title,
                completed: r.completed != 0,
                priority: r.priority.parse().unwrap_or(crate::todo::Priority::Medium),
                status: r.status.parse().unwrap_or(crate::todo::Status::Pending),
            })
            .collect())
    }

    async fn update(&self, todo: &Todo) -> Result<Todo, sqlx::Error> {
        let rec = sqlx::query!(
            "UPDATE todos SET title = ?1, completed = ?2 WHERE id = ?3 RETURNING id, title, completed, priority, status",
            &todo.title,
            todo.completed as i32,
            todo.id
        )
        .fetch_one(&self.pool)
        .await?;
        Ok(Todo {
            id: rec.id,
            title: rec.title,
            completed: rec.completed != 0,
            priority: rec.priority.parse().unwrap_or(crate::todo::Priority::Medium),
            status: rec.status.parse().unwrap_or(crate::todo::Status::Pending),
        })
    }

    async fn delete(&self, id: i64) -> Result<(), sqlx::Error> {
        sqlx::query!("DELETE FROM todos WHERE id = ?1", id)
            .execute(&self.pool)
            .await?;
        Ok(())
    }
}
