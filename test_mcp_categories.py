import subprocess
import json
import time
import sys

def run_test():
    # Start the MCP server process via docker exec
    process = subprocess.Popen(
        ["docker", "exec", "-i", "voxdocs-mcp", "python", "-m", "mcp_server.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=0  # Unbuffered
    )

    print("Started MCP server process...")

    # Messages to send
    init_msg = {
        "jsonrpc": "2.0", 
        "method": "initialize", 
        "params": {
            "protocolVersion": "2024-11-05", 
            "capabilities": {}, 
            "clientInfo": {"name": "test", "version": "1.0"}
        }, 
        "id": 1
    }
    
    initialized_msg = {
        "jsonrpc": "2.0", 
        "method": "notifications/initialized"
    }
    
    ingest_msg = {
        "jsonrpc": "2.0", 
        "method": "tools/call", 
        "params": {
            "name": "ingest_transcript", 
            "arguments": {
                "case_id": "687d2ccd-98a8-40b7-bb46-268073ba6f2e", 
                "text": "Der Patient zeigt Anzeichen einer Depression.", 
                "group_id": "1", 
                "author": "admin",
                "categories": ["Psychologie", "Diagnose"]
            }
        }, 
        "id": 2
    }
    
    # Helper to send and read
    def send(msg):
        print(f"Sending ID {msg.get('id', 'notif')}...")
        process.stdin.write(json.dumps(msg) + "\n")
        process.stdin.flush()

    def read_response():
        line = process.stdout.readline()
        if not line:
            return None
        try:
            return json.loads(line)
        except:
            print(f"Raw output: {line.strip()}")
            return None

    try:
        # Handshake
        send(init_msg)
        resp = read_response()
        print(f"Init Response: {json.dumps(resp, indent=2)}")
        
        send(initialized_msg)
        
        # Ingest with categories
        time.sleep(1)
        send(ingest_msg)
        print("Waiting for Ingest response...")
        resp_ingest = read_response()
        print(f"Ingest Response: {json.dumps(resp_ingest, indent=2)}")
        
    finally:
        process.stdin.close()
        process.terminate()
        process.wait()

if __name__ == "__main__":
    run_test()
