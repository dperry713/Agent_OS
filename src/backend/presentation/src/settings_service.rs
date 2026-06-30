use std::sync::Mutex;

use tonic::{Request, Response, Status};
use settings_pb::settings_service_server::{SettingsService, SettingsServiceServer};
use settings_pb::{Empty, GetDarkThemeResponse, SetDarkThemeRequest};

#[derive(Default)]
pub struct MySettingsService {
    // Simple in‑memory flag; a real implementation would use the SQLite pool.
    dark_theme: Mutex<bool>,
}

#[tonic::async_trait]
impl SettingsService for MySettingsService {
    async fn get_dark_theme(&self, _request: Request<Empty>) -> Result<Response<GetDarkThemeResponse>, Status> {
        let is_dark = *self.dark_theme.lock().unwrap();
        Ok(Response::new(GetDarkThemeResponse { is_dark }))
    }

    async fn set_dark_theme(&self, request: Request<SetDarkThemeRequest>) -> Result<Response<Empty>, Status> {
        let val = request.into_inner().is_dark;
        *self.dark_theme.lock().unwrap() = val;
        Ok(Response::new(Empty {}))
    }
}

// Export the server type for use in main.rs
pub fn server() -> SettingsServiceServer<MySettingsService> {
    SettingsServiceServer::new(MySettingsService::default())
}
