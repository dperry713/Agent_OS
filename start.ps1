$ErrorActionPreference = "Stop"

# Clean up any leftover backend processes
Get-Process -Name rustc -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name presentation -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Get-Process -Name AgentOS.Desktop -ErrorAction SilentlyContinue | Stop-Process -Force

# Remove stale Rust build artifacts
$targetPath = "src/backend/presentation/target"
if (Test-Path $targetPath) { Remove-Item -Recurse -Force $targetPath -ErrorAction SilentlyContinue }

# Set log level to error to reduce startup latency
$env:RUST_LOG = "error"

# Build backend cleanly
Write-Host "Building backend (Rust) in Release mode..." -ForegroundColor Cyan
Start-Process -FilePath "cargo" -ArgumentList "build --manifest-path src/backend/presentation/Cargo.toml --release" -Wait -NoNewWindow

# Launch backend (detached)
Write-Host "Starting backend..." -ForegroundColor Cyan
$backendProcess = Start-Process -FilePath "cargo" -ArgumentList "run --manifest-path src/backend/presentation/Cargo.toml --release" -PassThru -NoNewWindow

try {
    # Short pause for backend to be ready
    Start-Sleep -Seconds 1

    # Launch Avalonia frontend using absolute path
    Write-Host "Launching Avalonia frontend..." -ForegroundColor Cyan
    $frontendProj = Join-Path $PSScriptRoot "src/frontend/AgentOS.Desktop.csproj"
    dotnet run -c Release --project $frontendProj
} finally {
    # Cleanup backend when UI exits
    Write-Host "AgentOS Desktop closed. Shutting down backend..." -ForegroundColor Yellow
    if ($backendProcess -ne $null -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
    Write-Host "AgentOS shutdown complete." -ForegroundColor Green
}
