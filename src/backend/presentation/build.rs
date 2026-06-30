fn main() -> Result<(), Box<dyn std::error::Error>> {
    let protoc_path = r"C:\Users\d\.nuget\packages\grpc.tools\2.81.1\tools\windows_x64\protoc.exe";
    std::env::set_var("PROTOC", protoc_path);
    tonic_build::compile_protos("../../shared/protos/agent_os.proto")?;
    Ok(())
}
