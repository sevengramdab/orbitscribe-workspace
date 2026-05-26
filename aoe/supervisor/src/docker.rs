use anyhow::{Context, Result};
use bollard::container::{
    Config, CreateContainerOptions, KillContainerOptions, ListContainersOptions,
    RemoveContainerOptions, StartContainerOptions, StatsOptions, WaitContainerOptions,
};
use bollard::image::CreateImageOptions;
use bollard::models::{ContainerSummary, HostConfig};
use bollard::Docker;
use bytes::Bytes;
use futures::StreamExt;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{error, info, warn};

pub const DEFAULT_IMAGE: &str = "aquaculture-mesh:latest";
pub const DEFAULT_CONTAINER_NAME: &str = "aquaculture-mesh-alpha";
pub const DEFAULT_MEMORY_LIMIT_MB: u64 = 512;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshStatus {
    pub container_id: Option<String>,
    pub running: bool,
    pub memory_usage_mb: f64,
    pub memory_limit_mb: u64,
    pub cpu_percent: f64,
    pub pid_count: u64,
    pub cycles_completed: u64,
}

pub struct DockerManager {
    docker: Docker,
    state: Arc<RwLock<MeshStatus>>,
    image: String,
    container_name: String,
    memory_limit_mb: u64,
}

impl DockerManager {
    pub async fn new(image: String, container_name: String, memory_limit_mb: u64) -> Result<Self> {
        let docker = Docker::connect_with_local_defaults()
            .context("failed to connect to Docker (is Docker Desktop running?)")?;

        docker.ping().await.context("Docker daemon did not respond to ping")?;

        let state = Arc::new(RwLock::new(MeshStatus {
            container_id: None,
            running: false,
            memory_usage_mb: 0.0,
            memory_limit_mb,
            cpu_percent: 0.0,
            pid_count: 0,
            cycles_completed: 0,
        }));

        Ok(Self {
            docker,
            state,
            image,
            container_name,
            memory_limit_mb,
        })
    }

    pub async fn pull_image(&self) -> Result<()> {
        info!(image = %self.image, "pulling image");
        let options = Some(CreateImageOptions {
            from_image: self.image.clone(),
            ..Default::default()
        });
        let mut stream = self.docker.create_image(options, None, None);
        while let Some(item) = stream.next().await {
            match item {
                Ok(status) => {
                    if let Some(id) = status.id {
                        info!(id, "pull progress");
                    }
                }
                Err(e) => {
                    warn!(error = %e, "pull warning");
                }
            }
        }
        Ok(())
    }

    pub async fn spawn(&self) -> Result<String> {
        // Remove any existing container with the same name
        if let Err(e) = self.remove_existing().await {
            warn!(error = %e, "failed to remove existing container");
        }

        let memory_bytes = self.memory_limit_mb * 1024 * 1024;
        let config = Config {
            image: Some(self.image.clone()),
            env: Some(vec![
                "RUST_LOG=info".to_string(),
                "PYTHONUNBUFFERED=1".to_string(),
            ]),
            host_config: Some(HostConfig {
                memory: Some(memory_bytes as i64),
                memory_swap: Some(memory_bytes as i64),
                nano_cpus: Some(1_000_000_000), // 1 CPU
                auto_remove: Some(true),
                network_mode: Some("bridge".to_string()),
                ..Default::default()
            }),
            ..Default::default()
        };

        let create_opts = CreateContainerOptions {
            name: self.container_name.clone(),
            platform: None,
        };

        let container = self
            .docker
            .create_container(Some(create_opts), config)
            .await
            .context("failed to create container")?;

        let id = container.id;
        info!(container_id = %id, "container created");

        self.docker
            .start_container(&id, None::<StartContainerOptions<String>>)
            .await
            .context("failed to start container")?;

        info!(container_id = %id, "container started");

        {
            let mut state = self.state.write().await;
            state.container_id = Some(id.clone());
            state.running = true;
        }

        // Spawn memory monitor
        let docker_clone = self.docker.clone();
        let state_clone = self.state.clone();
        let limit_mb = self.memory_limit_mb;
        tokio::spawn(async move {
            monitor_stats(docker_clone, id.clone(), state_clone, limit_mb).await;
        });

        Ok(id)
    }

    pub async fn stop(&self) -> Result<()> {
        let id = {
            let state = self.state.read().await;
            match &state.container_id {
                Some(id) => id.clone(),
                None => return Ok(()),
            }
        };

        info!(container_id = %id, "stopping container");

        let _ = self
            .docker
            .kill_container(&id, Some(KillContainerOptions { signal: "SIGKILL" }))
            .await;

        let _ = self
            .docker
            .wait_container(&id, None::<WaitContainerOptions<String>>)
            .await;

        let _ = self
            .docker
            .remove_container(
                &id,
                Some(RemoveContainerOptions {
                    force: true,
                    ..Default::default()
                }),
            )
            .await;

        {
            let mut state = self.state.write().await;
            state.container_id = None;
            state.running = false;
        }

        info!("container removed, state wiped");
        Ok(())
    }

    pub async fn failsafe(&self) -> Result<()> {
        warn!("FAILSAFE triggered — immediate container kill");
        self.stop().await
    }

    pub async fn status(&self) -> MeshStatus {
        self.state.read().await.clone()
    }

    pub async fn logs(&self) -> Result<Vec<String>> {
        let id = {
            let state = self.state.read().await;
            match &state.container_id {
                Some(id) => id.clone(),
                None => return Ok(vec![]),
            }
        };

        let opts = bollard::container::LogsOptions::<String> {
            stdout: true,
            stderr: true,
            tail: "100".to_string(),
            ..Default::default()
        };

        let mut stream = self.docker.logs(&id, Some(opts));
        let mut lines = Vec::new();
        while let Some(chunk) = stream.next().await {
            match chunk {
                Ok(bytes) => {
                    if let Ok(line) = String::from_utf8(bytes.to_vec()) {
                        lines.push(line.trim().to_string());
                    }
                }
                Err(e) => {
                    error!(error = %e, "log stream error");
                }
            }
        }
        Ok(lines)
    }

    async fn remove_existing(&self) -> Result<()> {
        let filters = serde_json::json!({"name": [&self.container_name]});
        let opts = ListContainersOptions {
            all: true,
            filters,
            ..Default::default()
        };
        let containers = self.docker.list_containers(Some(opts)).await?;
        for c in containers {
            if let Some(id) = c.id {
                let _ = self
                    .docker
                    .remove_container(
                        &id,
                        Some(RemoveContainerOptions {
                            force: true,
                            ..Default::default()
                        }),
                    )
                    .await;
            }
        }
        Ok(())
    }
}

async fn monitor_stats(
    docker: Docker,
    container_id: String,
    state: Arc<RwLock<MeshStatus>>,
    limit_mb: u64,
) {
    let opts = StatsOptions {
        stream: true,
        one_shot: false,
    };
    let mut stream = docker.stats(&container_id, Some(opts));

    while let Some(item) = stream.next().await {
        match item {
            Ok(stats) => {
                let mem_usage = stats.memory_stats.usage.unwrap_or(0) as f64 / (1024.0 * 1024.0);
                let mem_limit = stats.memory_stats.limit.unwrap_or(1) as f64 / (1024.0 * 1024.0);
                let cpu_delta = stats.cpu_stats.cpu_usage.total_usage.unwrap_or(0)
                    - stats.precpu_stats.cpu_usage.total_usage.unwrap_or(0);
                let system_delta = stats.cpu_stats.system_cpu_usage.unwrap_or(0)
                    - stats.precpu_stats.system_cpu_usage.unwrap_or(0);
                let cpu_percent = if system_delta > 0 {
                    (cpu_delta as f64 / system_delta as f64)
                        * stats.cpu_stats.online_cpus.unwrap_or(1) as f64
                        * 100.0
                } else {
                    0.0
                };

                {
                    let mut s = state.write().await;
                    s.memory_usage_mb = mem_usage;
                    s.cpu_percent = cpu_percent;
                    s.pid_count = stats.pids_stats.current.unwrap_or(0) as u64;
                }

                if mem_usage > limit_mb as f64 {
                    error!(
                        usage_mb = mem_usage,
                        limit_mb = limit_mb,
                        "MEMORY LEAK DETECTED — killing container"
                    );
                    let _ = docker
                        .kill_container(
                            &container_id,
                            Some(KillContainerOptions { signal: "SIGKILL" }),
                        )
                        .await;
                    let mut s = state.write().await;
                    s.running = false;
                    break;
                }
            }
            Err(e) => {
                error!(error = %e, "stats stream error");
                break;
            }
        }
    }
}
