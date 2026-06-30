pub mod agentos {
    pub mod core {
        tonic::include_proto!("agentos.core");
    }
}
mod settings_service;
use agentos::core::core_ipc_server::{CoreIpc, CoreIpcServer};
use agentos::core::{EmptyRequest, PingRequest, PingResponse, ToggleShellRequest, ToggleShellResponse};
use tonic::{transport::Server, Request, Response, Status};
use winreg::enums::*;
use winreg::RegKey;

#[derive(Default)]
pub struct MyCoreIpc {}

#[tonic::async_trait]
impl CoreIpc for MyCoreIpc {
    async fn ping(&self, request: Request<PingRequest>) -> Result<Response<PingResponse>, Status> {
        Ok(Response::new(PingResponse {
            message: format!("Pong: {}", request.into_inner().message),
        }))
    }

    async fn toggle_custom_shell(&self, request: Request<ToggleShellRequest>) -> Result<Response<ToggleShellResponse>, Status> {
        let enable = request.into_inner().enable;
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let path = r#"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"#;

        if enable {
            let (key, _) = hkcu.create_subkey(path).map_err(|e| Status::internal(e.to_string()))?;
            let current_exe = std::env::current_exe().map_err(|e| Status::internal(e.to_string()))?;
            // Determine frontend path (assuming it runs in the same directory or we use a fixed path)
            // For now, we point to the AgentOS.Desktop executable
            let frontend_exe = current_exe.parent().unwrap().join("AgentOS.Desktop.exe");
            
            key.set_value("Shell", &frontend_exe.to_string_lossy().to_string())
               .map_err(|e| Status::internal(e.to_string()))?;

            Ok(Response::new(ToggleShellResponse {
                is_enabled: true,
                message: "Custom shell enabled.".to_string(),
            }))
        } else {
            if let Ok(key) = hkcu.open_subkey_with_flags(path, KEY_WRITE) {
                let _ = key.delete_value("Shell");
            }
            Ok(Response::new(ToggleShellResponse {
                is_enabled: false,
                message: "Custom shell disabled (restored to explorer.exe).".to_string(),
            }))
        }
    }

    async fn is_custom_shell_enabled(&self, _request: Request<EmptyRequest>) -> Result<Response<ToggleShellResponse>, Status> {
        let hkcu = RegKey::predef(HKEY_CURRENT_USER);
        let path = r#"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"#;
        
        let is_enabled = if let Ok(key) = hkcu.open_subkey_with_flags(path, KEY_READ) {
            let shell_val: Result<String, _> = key.get_value("Shell");
            shell_val.is_ok()
        } else {
            false
        };

        Ok(Response::new(ToggleShellResponse {
            is_enabled,
            message: String::new(),
        }))
    }
}

use opentelemetry::trace::TracerProvider;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};
use std::time::Duration;
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{GetAsyncKeyState, VK_CONTROL, VK_MENU, VK_SHIFT, VK_K};
use std::process::Command;

fn start_auto_kill_monitor() {
    std::thread::spawn(|| {
        loop {
            let ctrl = unsafe { GetAsyncKeyState(VK_CONTROL as i32) };
            let alt = unsafe { GetAsyncKeyState(VK_MENU as i32) };
            let shift = unsafe { GetAsyncKeyState(VK_SHIFT as i32) };
            let k = unsafe { GetAsyncKeyState(VK_K as i32) };

            if (ctrl & 0x8000_u16 as i16) != 0 
                && (alt & 0x8000_u16 as i16) != 0 
                && (shift & 0x8000_u16 as i16) != 0 
                && (k & 0x8000_u16 as i16) != 0 {
                
                tracing::warn!("Auto-kill sequence detected (CTRL+ALT+SHIFT+K)!");
                
                // 1. Remove custom shell registry key
                let hkcu = winreg::RegKey::predef(winreg::enums::HKEY_CURRENT_USER);
                let path = r#"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"#;
                if let Ok(key) = hkcu.open_subkey_with_flags(path, winreg::enums::KEY_WRITE) {
                    let _ = key.delete_value("Shell");
                }
                
                // 2. Restart computer
                tracing::warn!("Restarting system to restore normal Windows shell...");
                let _ = Command::new("shutdown.exe")
                    .args(&["/r", "/t", "0", "/f"])
                    .spawn();
                
                std::process::exit(0);
            }
            std::thread::sleep(Duration::from_millis(100));
        }
    });
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Start failsafe monitor
    start_auto_kill_monitor();

    // Setup OpenTelemetry Tracing (optional)
    if std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT").is_ok() {
        let provider = opentelemetry_otlp::new_pipeline()
            .tracing()
            .with_exporter(opentelemetry_otlp::new_exporter().tonic())
            .install_simple()
            .expect("Failed to initialize OpenTelemetry tracer");
        let tracer = provider.tracer("agentos-backend");
        let telemetry = tracing_opentelemetry::layer().with_tracer(tracer);
        tracing_subscriber::registry()
            .with(tracing_subscriber::fmt::layer())
            .with(telemetry)
            .init();
    } else {
        tracing_subscriber::registry()
            .with(tracing_subscriber::fmt::layer())
            .init();
    }

    tracing::info!("Starting AgentOS gRPC Server...");

    let settings = infrastructure::settings::AppSettings::new()?;
    tracing::info!("Loaded settings: {:?}", settings);

    let addr = format!("{}:{}", settings.server.host, settings.server.port).parse()?;
    
    // Initialize DB
    let _pool = infrastructure::db::init_db(&settings.database.url).await?;
    tracing::info!("Database initialized at {}", settings.database.url);

    let ipc = MyCoreIpc::default();

    Server::builder()
        .add_service(CoreIpcServer::new(ipc))
        .serve(addr)
        .await?;

    Ok(())
}
