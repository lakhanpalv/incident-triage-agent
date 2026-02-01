import json
import os
import sys
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Mock azure.functions before importing function_app
sys.modules['azure.functions'] = MagicMock()

# Add parent directory to path to import function_app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from function_app import run_agent_core, validate_incident_output

# Define paths to golden inputs and outputs
golden_inputs_dir = os.path.join(os.path.dirname(__file__), "golden_inputs")

def load_golden_input(file_path: str) -> str:
    with open(file_path, 'r') as f:
        return f.read()

def load_golden_output(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        return json.load(f)

def run_regression_test(input_file: str) -> bool:
    input_text = load_golden_input(input_file)
    
    # Run the agent core function
    output_result = run_agent_core(input_text)
    print(f"Agent Output: {output_result}")
    eval_result = validate_incident_output(output_result)

    if eval_result["hard_fail"]:
      print(f"Pre-run evaluation failed for input {input_file}: {eval_result['errors']}")
      exit(1)
    
    return True

def main():
  """Run regression tests on all golden input files."""
  if not os.path.exists(golden_inputs_dir):
    print(f"Golden inputs directory not found: {golden_inputs_dir}")
    exit(1)
  
  # Get all input files from the golden inputs directory
  input_files = [f for f in os.listdir(golden_inputs_dir) if f.endswith('.txt') or f.endswith('.md')]
  
  if not input_files:
    print(f"No input files found in {golden_inputs_dir}")
    exit(1)
  
  print(f"Running regression tests on {len(input_files)} files...")
  
  for input_file in input_files:
    file_path = os.path.join(golden_inputs_dir, input_file)
    print(f"\nTesting: {input_file}")
    
    try:
      run_regression_test(file_path)
      print(f"✓ Passed: {input_file}")
    except Exception as e:
      print(f"✗ Failed: {input_file} - {str(e)}")
      exit(1)
  
  print(f"\n{'='*50}")
  print(f"All {len(input_files)} regression tests passed!")

if __name__ == "__main__":
  main()