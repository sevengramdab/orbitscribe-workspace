use anyhow::Result;
use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::net::TcpListener;
use tracing::{info, warn};

use crate::docker::{DockerManager, MeshStatus};

#[derive(Clone)]
pub struct AppState {
    pub manager: Arc<DockerManager>,
}

#[derive(Serialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
}

#[derive(Deserialize)]
#[allow(dead_code)]
pub struct StartRequest {
    pub image: Option<String>,
    pub memory_limit_mb: Option<u64>,
}

#[derive(Serialize)]
pub struct StartResponse {
    pub container_id: String,
}

#[derive(Serialize)]
pub struct StopResponse {
    pub wiped: bool,
}

#[derive(Serialize)]
pub struct FailsafeResponse {
    pub killed: bool,
}

#[derive(Serialize)]
pub struct LogsResponse {
    pub lines: Vec<String>,
}

fn ok<T>(data: T) -> Json<ApiResponse<T>> {
    Json(ApiResponse {
        success: true,
        data: Some(data),
        error: None,
    })
}

fn err<T: Serialize>(msg: String) -> Json<ApiResponse<T>> {
    Json(ApiResponse {
        success: false,
        data: None,
        error: Some(msg),
    })
}

async fn mesh_start(
    State(state): State<AppState>,
    Json(req): Json<StartRequest>,
) -> Json<ApiResponse<StartResponse>> {
    info!("POST /mesh/start");
    if let Some(img) = req.image {
        // We don't support dynamic image switching in this simple version,
        // but we could recreate the manager. For now, just log it.
        info!(image = %img, "start request with custom image");
    }
    match state.manager.spawn().await {
        Ok(id) => ok(StartResponse { container_id: id }),
        Err(e) => err(format!("failed to start mesh: {}", e)),
    }
}

async fn mesh_stop(State(state): State<AppState>) -> Json<ApiResponse<StopResponse>> {
    info!("POST /mesh/stop");
    match state.manager.stop().await {
        Ok(()) => ok(StopResponse { wiped: true }),
        Err(e) => err(format!("failed to stop mesh: {}", e)),
    }
}

async fn mesh_status(State(state): State<AppState>) -> Json<ApiResponse<MeshStatus>> {
    let status = state.manager.status().await;
    ok(status)
}

async fn mesh_failsafe(State(state): State<AppState>) -> Json<ApiResponse<FailsafeResponse>> {
    warn!("POST /mesh/failsafe — emergency kill");
    match state.manager.failsafe().await {
        Ok(()) => ok(FailsafeResponse { killed: true }),
        Err(e) => err(format!("failsafe failed: {}", e)),
    }
}

async fn mesh_logs(State(state): State<AppState>) -> Json<ApiResponse<LogsResponse>> {
    match state.manager.logs().await {
        Ok(lines) => ok(LogsResponse { lines }),
        Err(e) => err(format!("failed to fetch logs: {}", e)),
    }
}

async fn health() -> &'static str {
    "ok"
}

pub async fn serve(manager: Arc<DockerManager>, port: u16) -> Result<()> {
    let state = AppState { manager };

    let app = Router::new()
        .route("/health", get(health))
        .route("/mesh/start", post(mesh_start))
        .route("/mesh/stop", post(mesh_stop))
        .route("/mesh/status", get(mesh_status))
        .route("/mesh/failsafe", post(mesh_failsafe))
        .route("/mesh/logs", get(mesh_logs))
        .with_state(state);

    let addr = format!("0.0.0.0:{}", port);
    let listener = TcpListener::bind(&addr).await?;
    info!(addr = %addr, "AOE supervisor listening");

    axum::serve(listener, app).await?;
    Ok(())
}
