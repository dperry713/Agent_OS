// src/todo.rs – Todo domain model

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Todo {
    pub id: i64,
    pub title: String,
    pub completed: bool,
    pub priority: Priority,
    pub status: Status,
}

#[derive(Debug, Clone, PartialEq, Eq, sqlx::Type)]
#[sqlx(type = "text", rename_all = "snake_case")]
pub enum Priority {
    Low,
    Medium,
    High,
}

#[derive(Debug, Clone, PartialEq, Eq, sqlx::Type)]
#[sqlx(type = "text", rename_all = "snake_case")]
pub enum Status {
    Pending,
    InProgress,
    Completed,
}

impl Todo {
    pub fn new(id: i64, title: impl Into<String>) -> Self {
        let title_str = title.into();
        let priority = Self::infer_priority(&title_str);
        let completed = false;
        let status = Self::infer_status(completed);
        Self {
            id,
            title: title_str,
            completed,
            priority,
            status,
        }
    }

    fn infer_priority(title: &str) -> Priority {
        let lower = title.to_lowercase();
        if lower.contains("high") || lower.contains("urgent") {
            Priority::High
        } else if lower.contains("low") {
            Priority::Low
        } else {
            Priority::Medium
        }
    }

    fn infer_status(completed: bool) -> Status {
        if completed {
            Status::Completed
        } else {
            Status::Pending
        }
    }
}
