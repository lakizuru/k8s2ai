# k8s2ai

A CLI tool that bridges `k8sgpt` and `kubectl-ai` to automatically analyze Kubernetes issues and execute solutions.

## Overview

`k8s2ai` runs `k8sgpt analyze --explain` to detect Kubernetes issues, extracts solution options from the JSON output, prompts you to select a solution, and then executes it using `kubectl-ai`.

## Prerequisites

1. **k8sgpt** - Install from [k8sgpt.io](https://k8sgpt.io)
2. **kubectl-ai** - Install via krew: `kubectl krew install ai`
3. **Python 3.7+** - Uses only standard library, no external dependencies

## Installation

1. Clone or download this repository
2. Make the script executable (Unix/Linux/Mac):
   ```bash
   chmod +x k8s2ai.py
   ```

3. (Optional) Add to your PATH or create an alias:
   ```bash
   alias k8s2ai='python3 /path/to/k8s2ai.py'
   ```

## Usage

### Basic Usage

```bash
# Default: runs k8sgpt analyze --explain
python3 k8s2ai.py

# Pass any k8sgpt arguments directly
python3 k8s2ai.py analyze --explain -f Pod  # Shows prompt to select solution
python3 k8s2ai.py analyze -f Pod             # Just shows solutions, no prompt
python3 k8s2ai.py analyze --explain --namespace default
python3 k8s2ai.py analyze --explain --filter Pod,Deployment
```

This will:
1. Run `k8sgpt` with the provided arguments (defaults to `analyze --explain`)
2. Parse the JSON output
3. Display detected issues and solutions
4. **If `--explain` flag is present**: Prompt you to select a solution and execute it with `kubectl-ai`
5. **If `--explain` flag is NOT present**: Just display solutions and exit (no prompt, no execution)

### Command Line Options

```bash
# View raw JSON output (for debugging)
python3 k8s2ai.py analyze --explain --json-output

# Automatically select solution #1 without prompting
python3 k8s2ai.py analyze --explain -f Pod --auto-select 1

# Combine k8sgpt args with k8s2ai options
python3 k8s2ai.py --auto-select 2 analyze --explain --namespace my-namespace
```

**Note**: All arguments after `k8s2ai`-specific options (`--json-output`, `--auto-select`) are passed directly to `k8sgpt`. The tool automatically adds `--output json` if not already specified to ensure JSON parsing works correctly.

## Example Output

```
Running: k8sgpt analyze --explain -f Pod --output json

================================================================================
DETECTED ISSUES AND SOLUTIONS
================================================================================

[1] Pod: default/hungry-pod
    Error: Back-off pulling image "busybox": ErrImagePull: failed to pull and unpack image...
    Solution: 1. Verify network connectivity.

[2] Pod: default/hungry-pod
    Error: Back-off pulling image "busybox": ErrImagePull: failed to pull and unpack image...
    Solution: 2. Check image name/tag (docker.io/library/busybox:latest).

[3] Pod: default/hungry-pod
    Error: Back-off pulling image "busybox": ErrImagePull: failed to pull and unpack image...
    Solution: 3. Confirm registry access (credentials if needed).

--------------------------------------------------------------------------------
Select a solution to execute (1-3) or 'q' to quit: 1

Executing solution with kubectl-ai...
Solution: 1. Verify network connectivity.
```

## How It Works

1. **Analysis**: Runs `k8sgpt analyze --explain` and captures JSON output
2. **Parsing**: Extracts issues and solutions from the JSON structure
3. **Solution Extraction**: Splits multi-step solutions into individual options
4. **Selection**: Interactive prompt to choose which solution to execute
5. **Execution**: Sends the selected solution to `kubectl-ai` for automated remediation

## JSON Format

The tool expects JSON output from k8sgpt in this format:

```json
{
  "provider": "ollama",
  "errors": null,
  "status": "ProblemDetected",
  "problems": 1,
  "results": [
    {
      "kind": "Pod",
      "name": "default/hungry-pod",
      "error": [
        {
          "Text": "Error message here",
          "KubernetesDoc": "",
          "Sensitive": []
        }
      ],
      "details": "Error: Description\n\nSolution:\n1. First step\n2. Second step\n3. Third step",
      "parentObject": ""
    }
  ]
}
```

## Troubleshooting

### k8sgpt not found
- Ensure `k8sgpt` is installed and in your PATH
- Verify with: `k8sgpt version`

### kubectl-ai not found
- Install via krew: `kubectl krew install ai`
- Verify with: `kubectl ai --help`

### JSON parsing errors
- Use `--json-output` flag to see raw output
- Ensure k8sgpt is configured correctly with your AI provider

## License

MIT License - feel free to use and modify as needed.

