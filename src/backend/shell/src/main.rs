// src/main.rs – Entry point for the Rust shell runtime

use tonic::{transport::Server, Request, Response, Status};
use runtime::runtime_service_server::{RuntimeService, RuntimeServiceServer};
use runtime::{PingRequest, PingResponse};
use tracing::{info, error};
use tracing_subscriber::{fmt, EnvFilter};

mod runtime {
    tonic::include_proto!("runtime");
}

#[derive(Debug, Default)]
pub struct MyRuntimeService;

#[tonic::async_trait]
impl RuntimeService for MyRuntimeService {
    async fn ping(&self, _request: Request<PingRequest>) -> Result<Response<PingResponse>, Status> {
        info!("Received Ping request");
        let reply = PingResponse {
            message: "pong".into(),
        };
        Ok(Response::new(reply))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing subscriber for structured JSON logs
    fmt()
        .with_env_filter(EnvFilter::from_default_env())
        .json()
        .init();

    info!("Starting AgentOS Rust shell");

    // Configuration (placeholder – could be expanded later)
    let config_path = std::env::var("AGENTOS_CONFIG").unwrap_or_else(|_| "config/settings.json".into());
    info!("Loading configuration from {}", config_path);

    // Start gRPC server on localhost:50051 (adjustable via env)
    let addr = std::env::var("AGENTOS_IPC_ADDR")
        .unwrap_or_else(|_| "127.0.0.1:50051".to_string())
        .parse()?;

    let runtime_service = MyRuntimeService::default();

    Server::builder()
        .add_service(RuntimeServiceServer::new(runtime_service))
        .serve(addr)
        .await?;

    info!("Shell shutdown");
    Ok(())
}
