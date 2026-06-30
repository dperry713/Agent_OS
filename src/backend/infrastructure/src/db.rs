use sqlx::{sqlite::SqlitePoolOptions, Pool, Sqlite};
use std::path::Path;

pub async fn init_db(db_path: impl AsRef<Path>) -> Result<Pool<Sqlite>, sqlx::Error> {
    let path_str = db_path.as_ref().to_string_lossy();
    let url = format!("sqlite:{}?mode=rwc", path_str);

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&url)
        .await?;

    // Apply migrations located in the migrations directory
    sqlx::migrate!("src/backend/infrastructure/src/migrations")
        .run(&pool)
        .await?;

    Ok(pool)
}

