import sys
import json
import http.client
import urllib.parse

def call_ollama(host, model, system_prompt, user_prompt, context_size=8192, timeout=120):
    url = urllib.parse.urlparse(host)
    # Default to localhost:11434 if port is not specified
    netloc = url.netloc if url.netloc else "localhost:11434"
    conn = http.client.HTTPConnection(netloc, timeout=timeout)
    
    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "options": {
            "num_ctx": context_size,
            "temperature": 0
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        conn.request("POST", "/api/generate", json.dumps(payload), headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        
        if response.status == 200:
            return json.loads(data).get('response', 'Error: No response field')
        else:
            print(f"Error: {response.status} {response.reason}\n{data.decode()}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: Connection failed or timed out. {str(e)}", file=sys.stderr)
        sys.exit(1)

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
        res = call_ollama(host, model, system_prompt, user_prompt)
        if res.startswith("Error:"):
            print(res, file=sys.stderr)
            sys.exit(1)
        print(res)
    except Exception as e:
        print(f"Error: Failed to read prompts or call Ollama. {str(e)}", file=sys.stderr)
        sys.exit(1)
