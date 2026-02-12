import subprocess
import tempfile
import os

def run_slither(code: str) -> dict:
    '''
    Run Slither static analysis on Solidity code.
    Returns structured results or error.
    '''
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sol', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        result = subprocess.run(
            ['slither', temp_path, '--json', '-'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        os.unlink(temp_path)
        
        return {
            'status': 'completed',
            'output': result.stdout if result.returncode == 0 else result.stderr,
            'return_code': result.returncode
        }
    except FileNotFoundError:
        return {'status': 'error', 'message': 'Slither not installed. Run: pip install slither-analyzer'}
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'message': 'Slither analysis timed out'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
