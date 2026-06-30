import grpc
import sys

def run():
    print('Trying to connect to Named Pipe...')
    # Some combinations to test
    uris = [
        'unix:\\\\.\\pipe\\agentos_eventbus',
        'unix://./pipe/agentos_eventbus',
        'ipv4:127.0.0.1:50051', # Just in case we decide to fall back to TCP
    ]
    for uri in uris:
        print(f'Testing {uri}')
        try:
            channel = grpc.insecure_channel(uri)
            # Try to fetch channel connectivity
            grpc.channel_ready_future(channel).result(timeout=1)
            print(f'SUCCESS with {uri}')
            return
        except Exception as e:
            print(f'FAILED: {e}')

if __name__ == '__main__':
    run()
