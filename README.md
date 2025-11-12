# k8s2ai

A CLI tool that bridges `k8sgpt` and `kubectl-ai` to automatically analyze Kubernetes issues and execute solutions.

## Overview

`k8s2ai` is a drop-in alias for `k8sgpt` with enhanced functionality. It passes all arguments directly to `k8sgpt`, and when used with `--explain`, it can interactively select and execute solutions using `kubectl-ai`.

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

`k8s2ai` works as a drop-in replacement for `k8sgpt`. All arguments are passed directly to `k8sgpt`:

```bash
# Works exactly like k8sgpt analyze
python3 k8s2ai.py analyze
python3 k8s2ai.py analyze -f Pod
python3 k8s2ai.py analyze --namespace default

# With --explain: shows solutions and prompts to select one for execution
python3 k8s2ai.py analyze --explain
python3 k8s2ai.py analyze --explain -f Pod
python3 k8s2ai.py analyze --explain --namespace default
```

**Behavior:**
- **Without `--explain`**: Behaves exactly like `k8sgpt` - shows the analysis output and solutions summary
- **With `--explain`**: Runs `k8sgpt analyze --explain`, shows solutions, prompts you to select one, and executes it with `kubectl-ai`

### Command Line Options

```bash
# Automatically select solution #1 without prompting (requires --explain)
python3 k8s2ai.py analyze --explain -f Pod --auto-select 1

# All other arguments are passed directly to k8sgpt
python3 k8s2ai.py analyze --output json
python3 k8s2ai.py analyze --filter Pod,Deployment
```

**Note**: `k8s2ai` passes all arguments directly to `k8sgpt`. The only `k8s2ai`-specific option is `--auto-select`, which requires the `--explain` flag.

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

