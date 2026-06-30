// src/lib.rs – Health service implementation for AgentOS

use tonic::{Request, Response, Status};
use sqlx::SqlitePool;
use std::time::{SystemTime, UNIX_EPOCH};

pub mod health_pb {
    tonic::include_proto!("agentos.health");
}

use health_pb::health_server::{Health, HealthServer};
use health_pb::{HealthCheckResponse, HealthCheckRequest};

#[derive(Clone)]
pub struct MyHealthService {
    pub db_pool: SqlitePool,
    start_time: SystemTime,
}

#[tonic::async_trait]
impl Health for MyHealthService {
    async fn check(
        &self,
        _request: Request<HealthCheckRequest>,
    ) -> Result<Response<HealthCheckResponse>, Status> {
        // Simple health check: uptime and DB connectivity
        let uptime = SystemTime::now()
            .duration_since(self.start_time)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        // Verify DB connection
        if let Err(e) = sqlx::query!("SELECT 1 as ok")
            .fetch_one(&self.db_pool)
            .await {
            return Err(Status::unavailable(format!("DB unavailable: {}", e)));
        }
        let reply = HealthCheckResponse {
            uptime,
            status: "SERVING".into(),
        };
        Ok(Response::new(reply))
    }
}

impl MyHealthService {
    pub fn new(db_pool: SqlitePool) -> Self {
        Self {
            db_pool,
            start_time: SystemTime::now(),
        }
    }
    pub fn server(self) -> HealthServer<MyHealthService> {
        HealthServer::new(self)
    }
}
