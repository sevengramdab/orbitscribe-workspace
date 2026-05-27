mod docker;
mod http;

use anyhow::Result;
use clap::Parser;
use std::sync::Arc;
use tokio::signal;
use tracing::{error, info};

#[derive(Parser, Debug)]
#[command(name = "aoe", about = "Agent of Empires — Rust supervisor for the aquaculture mesh")]
struct Args {
    #[arg(short, long, default_value = "58082")]
    port: u16,

    #[arg(short, long, default_value = "aquaculture-mesh:latest")]
    image: String,

    #[arg(short, long, default_value = "aquaculture-mesh-alpha")]
    name: String,

    #[arg(short, long, default_value = "512")]
    memory_limit_mb: u64,

    #[arg(long, default_value = "false")]
    pull: bool,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    let args = Args::parse();

    info!(
        port = args.port,
        image = %args.image,
        container_name = %args.name,
        memory_limit_mb = args.memory_limit_mb,
        "AOE supervisor booting"
    );

    let manager = Arc::new(
        docker::DockerManager::new(
            args.image.clone(),
            args.name.clone(),
            args.memory_limit_mb,
        )
        .await,
    );

    if args.pull {
        if let Err(e) = manager.pull_image().await {
            error!(error = %e, "failed to pull image, continuing anyway");
        }
    }

    let manager_clone = manager.clone();
    let server_handle = tokio::spawn(async move {
        if let Err(e) = http::serve(manager_clone, args.port).await {
            error!(error = %e, "HTTP server crashed");
        }
    });

    // Graceful shutdown on Ctrl+C
    tokio::select! {
        _ = signal::ctrl_c() => {
            info!("SIGINT received — wiping mesh and shutting down");
            if let Err(e) = manager.stop().await {
                error!(error = %e, "failed to stop mesh during shutdown");
            }
        }
        _ = server_handle => {}
    }

    info!("AOE supervisor offline. Memory footprint purged.");
    Ok(())
}
