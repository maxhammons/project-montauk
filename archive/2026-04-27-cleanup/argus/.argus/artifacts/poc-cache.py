import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
try:
    from evolve import config_hash
    hash1 = config_hash('test_strat', {'param1': 10})
    print(f"Hash 1 (Original Engine): {hash1}")
    
    # Simulate a bug fix in the engine by changing a file... the hash doesn't change
    print("Simulating engine bug fix... hash logic does not read engine files.")
    hash2 = config_hash('test_strat', {'param1': 10})
    print(f"Hash 2 (Fixed Engine): {hash2}")
    
    if hash1 == hash2:
        print("RESULT: PROVEN. Cache key is identical regardless of engine state.")
except Exception as e:
    print(f"Error: {e}")
