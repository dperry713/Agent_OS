// src/commands.rs – Application command structs for Todo

// Create Todo command
pub struct CreateTodo {
    pub title: String,
}

// Update Todo command
pub struct UpdateTodo {
    pub id: i64,
    pub title: Option<String>,
    pub completed: Option<bool>,
}

// Delete Todo command
pub struct DeleteTodo {
    pub id: i64,
}
