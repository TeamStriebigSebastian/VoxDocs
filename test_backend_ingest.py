import urllib.request
import urllib.parse
import urllib.error
import json
import time
import subprocess
import sys

BASE_URL = "http://localhost:8000/api"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def mcp_query(case_uuid, query_text):
    # Use docker exec to query MCP directly
    cmd = [
        "docker", "exec", "-i", "voxdocs-mcp", "python", "-m", "mcp_server.server"
    ]
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=0
    )
    
    init_msg = {
        "jsonrpc": "2.0", "method": "initialize", 
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, 
        "id": 1
    }
    initialized_msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    
    # Query tool
    query_msg = {
        "jsonrpc": "2.0", 
        "method": "tools/call", 
        "params": {
            "name": "retrieve_context_for_question", 
            "arguments": {
                "username": "admin", 
                "api_token": "admin-dev-token", 
                "case_id": case_uuid, 
                "query": query_text
            }
        }, 
        "id": 2
    }
    
    try:
        process.stdin.write(json.dumps(init_msg) + "\n")
        process.stdin.flush()
        process.stdout.readline() # Read init response
        
        process.stdin.write(json.dumps(initialized_msg) + "\n")
        process.stdin.flush()
        
        process.stdin.write(json.dumps(query_msg) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if response_line:
            return json.loads(response_line)
        return None
        
    finally:
        process.stdin.close()
        process.terminate()
        process.wait()

def post_json(url, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f"Bearer {token}"
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            print(f"Failed POST {url}: {response.status}")
            return None
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {url}: {e.code} {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error POST {url}: {e}")
        return None

def post_form(url, data, token=None):
    # Very simple form-url-encoded, assumes no files for this test
    encoded_data = urllib.parse.urlencode(data).encode('utf-8')
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    if token:
        headers['Authorization'] = f"Bearer {token}"
        
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            print(f"Failed POST {url}: {response.status}")
            return None
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {url}: {e.code} {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error POST {url}: {e}")
        return None

def main():
    print("1. Logging in as admin...")
    tokens = post_json(f"{BASE_URL}/auth/login", {"username": "admin", "password": "admin123"})
    if not tokens: return
    
    access_token = tokens["access_token"]
    print("   Success.")

    print("2. Creating Test Case...")
    case_data = {"group_id": 1, "title": "RAG Verification Case"}
    case_resp = post_json(f"{BASE_URL}/cases/", case_data, token=access_token)
    if not case_resp: return
    
    case_uuid = case_resp["uuid"]
    print(f"   Created Case UUID: {case_uuid}")

    print("3. Creating Text Entry (Ingestion Trigger)...")
    entry_text = "Der Patient hat akute Schmerzen im linken Knie und benötigt Ibuprofen."
    
    # Use form data for entries endpoint
    data = {
        "case_uuid": case_uuid,
        "text": entry_text
    }
    
    entry_resp = post_form(f"{BASE_URL}/entries/", data, token=access_token)
    if not entry_resp: return
    
    entry_uuid = entry_resp["uuid"]
    print(f"   Created Entry UUID: {entry_uuid}")

    print("4. Waiting 5s for Ingestion...")
    time.sleep(5)

    print("5. Querying RAG via MCP...")
    # Query for "Knie" or "Ibuprofen"
    query = "Welche Medikamente?"
    result_json = mcp_query(case_uuid, query)
    
    if result_json and "result" in result_json:
        # Check for error
        if result_json.get("error"):
            print(f"\n❌ MCP Error: {result_json['error']}")
            return

        content_list = result_json["result"]["content"]
        if not content_list:
             print("\n❌ Empty content list in result.")
             return
             
        content_text = content_list[0]["text"]
        print(f"\nRAG Response:\n{content_text}")
        
        # Check if text is present
        # RAG response is a JSON string inside text
        try:
            rag_data = json.loads(content_text)
            snippets = [item.get("snippet", "") for item in rag_data.get("data", [])]
            combined_snippets = " ".join(snippets)
            
            if "Ibuprofen" in combined_snippets:
                print("\n✅ VERIFICATION SUCCESS: Found ingress text in RAG response.")
            else:
                print(f"\n❌ VERIFICATION FAILED: 'Ibuprofen' not found insnippets: {combined_snippets}")
        except:
            if "Ibuprofen" in content_text:
                 print("\n✅ VERIFICATION SUCCESS: Found ingress text in RAG response (raw check).")
            else:
                 print("\n❌ VERIFICATION FAILED: Did not find text in RAG response.")
            
    else:
        print(f"\n❌ VERIFICATION FAILED: No valid response from MCP. Raw: {result_json}")

if __name__ == "__main__":
    main()
