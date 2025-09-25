import subprocess
import json
import random
import os
import dotenv
def run_node(script, args):
    dotenv.load_dotenv()
    try:
        result = subprocess.run(
            ['node', f'dist/{script}'] + args,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return json.loads(result.stderr)
    except Exception as e:
        return {'success': False, 'error': str(e)}

def createResource(pid:str, uri:str, hash:str, timestamp:str,owners:list[str])->dict:
    return run_node('createResource.js', [ pid, uri, hash, timestamp,json.dumps(owners)])

def readResource(pid:str)->dict:
    return run_node('readResource.js', [pid])

def getResourcesByInterval(startTime:str,endTime:str)->dict:
    return run_node('getAll.js', [startTime,endTime])

# Example usage
if __name__ == '__main__':
    created = create_resource(
    "PID_"+str(random.randint(1000,10000)),
    "https://example.com/resource",
    "hash_13134bh34bj32b4",
    "timestamp_432432423432",
    ["owner1", "owner2"])
    print('[Python] Created:', created)

    if created.get('success'):
        pid = created.get('pid')
        read = read_resource(pid)
        print('[Python] Read:', read)
