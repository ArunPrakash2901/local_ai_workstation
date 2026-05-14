import sys
import json
import http.client
import urllib.parse

def call_ollama(host, model, system_prompt, user_prompt, context_size=8192, timeout=120):
    url = urllib.parse.urlparse(host)
    # Default to localhost:11434 if parse fails
    hostname = url.hostname or "localhost"
    port = url.port or 11434
    
    conn = http.client.HTTPConnection(hostname, port, timeout=timeout)
    
    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "stream": False,
        "options": {
            "num_ctx": context_size
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    try:
        conn.request("POST", "/api/generate", json.dumps(payload), headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        
        if response.status == 200:
            return json.loads(data).get('response', 'Error: No response field')
        else:
            return f"Error: {response.status} {response.reason}\n{data.decode()}"
    except Exception as e:
        return f"Error: Connection failed or timed out. {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: ollama_call.py <host> <model> <system_prompt_path> <user_prompt_path>")
        sys.exit(1)
        
    host = sys.argv[1]
    model = sys.argv[2]
    system_prompt_path = sys.argv[3]
    user_prompt_path = sys.argv[4]
    
    try:
        with open(system_prompt_path, 'r') as f:
            system_prompt = f.read()
        with open(user_prompt_path, 'r') as f:
            user_prompt = f.read()
        print(call_ollama(host, model, system_prompt, user_prompt))
    except Exception as e:
        print(f"Error: Failed to read prompts or call Ollama. {str(e)}")
