// build.rs – compile the runtime.proto for Rust using tonic-build

fn main() {
    tonic_build::configure()
        .build_server(true)
        .compile(&["../../shared/protos/runtime.proto"], &["../../shared/protos"])
        .expect("Failed to compile protos");
}
