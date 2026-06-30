use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use std::path::Path;

pub async fn init_db(db_path: impl AsRef<Path>) -> Result<Pool<Sqlite>, sqlx::Error> {
    let path_str = db_path.as_ref().to_string_lossy();
    let url = format!("sqlite:{}?mode=rwc", path_str);

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&url)
        .await?;

    // Create a basic metadata table as part of M6 initialization
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );"
    )
    .execute(&pool)
    .await?;

    // Create a settings table for key/value pairs (e.g., dark mode)
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );"
    )
    .execute(&pool)
    .await?;

    Ok(pool)
}
