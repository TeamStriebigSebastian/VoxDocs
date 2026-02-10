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
                "text": "Ich bin echt sauer, dass das alles nicht richtig funktioniert hat. Wir müssen immer noch die Sachen von der Apotheke abholen.", 
                "group_id": "1", 
                "author": "admin"
            }
        }, 
        "id": 2
    }
    
    query1 = {
        "jsonrpc": "2.0", 
        "method": "tools/call", 
        "params": {
            "name": "retrieve_context_for_question", 
            "arguments": {
                "username": "admin", 
                "api_token": "admin-dev-token", 
                "case_id": "687d2ccd-98a8-40b7-bb46-268073ba6f2e", 
                "query": "Wurden die Medikamente abgeholt?"
            }
        }, 
        "id": 3
    }
    
    query2 = {
        "jsonrpc": "2.0", 
        "method": "tools/call", 
        "params": {
            "name": "retrieve_context_for_question", 
            "arguments": {
                "username": "admin", 
                "api_token": "admin-dev-token", 
                "case_id": "687d2ccd-98a8-40b7-bb46-268073ba6f2e", 
                "query": "Gab es eine emotionale Reaktion?"
            }
        }, 
        "id": 4
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
        
        # Ingest
        time.sleep(1)
        send(ingest_msg)
        print("Waiting for Ingest response (may take long if downloading model)...")
        resp_ingest = read_response()
        print(f"Ingest Response: {json.dumps(resp_ingest, indent=2)}")
        
        # Tools
        time.sleep(1)
        send(query1)
        print("Waiting for Query 1 response...")
        resp1 = read_response()
        print(f"Query 1 Response: {json.dumps(resp1, indent=2)}")
        
        send(query2)
        print("Waiting for Query 2 response...")
        resp2 = read_response()
        print(f"Query 2 Response: {json.dumps(resp2, indent=2)}")
        
    finally:
        process.stdin.close()
        process.terminate()
        process.wait()

if __name__ == "__main__":
    run_test()
