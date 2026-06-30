// build.rs – compile the runtime.proto for Rust using tonic-build

fn main() {
    // Use the non‑deprecated `compile_protos` API and let Cargo determine the output directory.
    tonic_build::configure()
        .build_server(true)
        .compile_protos(&["../../shared/protos/runtime.proto"], &["../../shared/protos"])
        .expect("Failed to compile protos");
}
