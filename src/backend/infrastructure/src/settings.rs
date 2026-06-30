use config::{Config, ConfigError, Environment, File};
use serde::Deserialize;
use std::env;

#[derive(Debug, Deserialize)]
pub struct ServerSettings {
    pub host: String,
    pub port: u16,
}

#[derive(Debug, Deserialize)]
pub struct DatabaseSettings {
    pub url: String,
}

#[derive(Debug, Deserialize)]
pub struct AppSettings {
    pub server: ServerSettings,
    pub database: DatabaseSettings,
}

impl AppSettings {
    pub fn new() -> Result<Self, ConfigError> {
        let run_mode = env::var("RUN_MODE").unwrap_or_else(|_| "development".into());

        // Determine the base config directory.
        // It can be overridden via the `AGENTOS_CONFIG_DIR` environment variable.
        let config_base = std::env::var("AGENTOS_CONFIG_DIR")
            .unwrap_or_else(|_| "src/backend/presentation/config".to_string());

        let s = Config::builder()
            // Load the default configuration file.
            .add_source(File::with_name(&format!("{}/default", config_base)).required(false))
            // Load the environment‑specific configuration file (optional).
            .add_source(
                File::with_name(&format!("{}/{}", config_base, run_mode)).required(false),
            )
            // Add in settings from the environment (with a prefix of AGENTOS).
            .add_source(Environment::with_prefix("agentos").separator("_"))
            .build()?;

        s.try_deserialize()
    }
}
