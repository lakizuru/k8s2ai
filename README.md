# k8s2ai

A powerful CLI tool that bridges `k8sgpt` and `kubectl-ai` to automatically analyze Kubernetes issues and execute AI-powered solutions.

## Overview

`k8s2ai` enhances your Kubernetes troubleshooting workflow by:
- Acting as a drop-in replacement for `k8sgpt` with all its features
- Parsing and presenting solutions in an interactive, user-friendly format
- Allowing you to select and execute solutions automatically using `kubectl-ai`
- Supporting custom solutions for complex scenarios
- Providing beautiful, colorized output with progress indicators

## Features

✓ **Drop-in replacement** for `k8sgpt` - all arguments pass through seamlessly  
✓ **Interactive solution selection** - choose from AI-generated fixes  
✓ **Custom solutions** - enter your own remediation steps  
✓ **Multi-error handling** - work through multiple issues systematically  
✓ **Auto-execution** - solutions run automatically via `kubectl-ai`  
✓ **Beautiful output** - colorized, emoji-enhanced terminal display  
✓ **Easy setup** - built-in `init` command for quick configuration  
✓ **Zero dependencies** - uses only Python standard library  

## Prerequisites

1. **k8sgpt** - Install from [docs.k8sgpt.ai](https://docs.k8sgpt.ai/getting-started/installation/)
2. **kubectl-ai** - Install via krew: `kubectl krew install ai`
3. **Python 3.7+** - Uses only standard library, no external dependencies
4. **Gemini API Key** - Get one from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/lakizuru/k8s2ai.git
cd k8s2ai
```

### 2. Make executable
```bash
chmod +x k8s2ai
```

### 3. Add to PATH (Choose one method)

#### Option A: Symlink to /usr/local/bin (Recommended)
```bash
sudo ln -s "$(pwd)/k8s2ai" /usr/local/bin/k8s2ai
```

#### Option B: Add to PATH in shell config
```bash
# For zsh (add to ~/.zshrc)
echo 'export PATH="$HOME/GitHub/k8s2ai:$PATH"' >> ~/.zshrc
source ~/.zshrc

# For bash (add to ~/.bashrc)
echo 'export PATH="$HOME/GitHub/k8s2ai:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Option C: Create an alias
```bash
# For zsh (add to ~/.zshrc)
echo 'alias k8s2ai="$HOME/GitHub/k8s2ai/k8s2ai"' >> ~/.zshrc
source ~/.zshrc

# For bash (add to ~/.bashrc)
echo 'alias k8s2ai="$HOME/GitHub/k8s2ai/k8s2ai"' >> ~/.bashrc
source ~/.bashrc
```

**Note:** Replace `$HOME/GitHub/k8s2ai` with the actual path where you cloned the repository.

### 4. Verify installation
```bash
k8s2ai --help
```

### 5. Initialize and configure
```bash
k8s2ai init
```

The `init` command will:
- ✓ Check if `k8sgpt` and `kubectl-ai` are installed
- ✓ Prompt for your Gemini API key
- ✓ Export the API key to your shell configuration
- ✓ Configure `k8sgpt` with Google/Gemini backend
- ✓ Set Gemini as the default AI provider

## Usage

### Initialize (First Time Setup)

```bash
k8s2ai init
```

Run this command first to set up your environment with the Gemini API key and configure k8sgpt.

### Basic Analysis

`k8s2ai` works as a drop-in replacement for `k8sgpt`. All arguments are passed directly:

```bash
# Basic analysis (same as k8sgpt analyze)
k8s2ai analyze

# Filter by resource type
k8s2ai analyze -f Pod
k8s2ai analyze --filter Deployment,Service

# Specify namespace
k8s2ai analyze --namespace kube-system

# Get JSON output
k8s2ai analyze --output json
```

### Interactive Mode with Solutions

Use the `--explain` flag to get AI-generated solutions and execute them interactively:

```bash
# Interactive solution selection
k8s2ai analyze --explain

# With filters
k8s2ai analyze --explain -f Pod
k8s2ai analyze --explain --namespace default

# Auto-select solution #1 (no prompts)
k8s2ai analyze --explain --auto-select 1
```

### Workflow with --explain

1. **Analysis**: k8sgpt analyzes your cluster and finds issues
2. **Error Display**: All detected issues are listed with numbers
3. **Error Selection**: Choose which error to work on (if multiple)
4. **Solution Display**: View AI-generated solution steps
5. **Solution Selection**: Pick a solution or enter a custom one
6. **Execution**: kubectl-ai executes the chosen solution automatically

## Command Reference

### k8s2ai init
Initialize the tool by checking dependencies and configuring API keys.

**What it does:**
- Checks if `k8sgpt` is installed
- Checks if `kubectl-ai` is installed
- Prompts for Gemini API key
- Exports `GEMINI_API_KEY` to your shell config
- Configures k8sgpt with Google backend
- Sets Google as the default AI provider

**Example:**
```bash
k8s2ai init
```

### k8s2ai analyze
Analyze your Kubernetes cluster for issues (passes through to k8sgpt).

**Options:**
- `--explain`: Get AI-generated solutions and execute them interactively
- `-f, --filter`: Filter by resource types (Pod, Deployment, Service, etc.)
- `-n, --namespace`: Specify namespace(s)
- `--output json`: Get JSON output
- `--auto-select N`: Auto-select solution N (requires --explain)

**Examples:**
```bash
# Basic analysis
k8s2ai analyze

# Interactive with solutions
k8s2ai analyze --explain

# Filter specific resources
k8s2ai analyze --explain -f Pod,Deployment

# Auto-execute first solution
k8s2ai analyze --explain --auto-select 1
```

### Custom Solutions

When prompted to select a solution, you can enter 'c' to provide a custom solution:

```bash
Select a solution to execute (1-3), 'c' for custom solution, or 'q' to quit: c

Enter your custom solution:
(Enter your solution text. Press Enter on an empty line to finish)
> Scale the deployment to 3 replicas and add resource limits
> 
```

The custom solution will be sent to kubectl-ai for execution.

## Example Output

### Without --explain (Standard Mode)
```
$ k8s2ai analyze -f Pod

0 default/nginx-pod(Deployment/nginx-pod)
- Error: ImagePullBackOff: Back-off pulling image "nginx:invalid-tag"

================================================================================
📋 SOLUTIONS SUMMARY
================================================================================

Error: Pod: default/nginx-pod
  ImagePullBackOff: Back-off pulling image "nginx:invalid-tag"

  Solutions:
    [1] Verify the image tag exists in the registry
    [2] Check your registry credentials and access
    [3] Use a valid nginx image tag like 'latest' or '1.21'

(Use --explain flag to interactively select and execute solutions)
```

### With --explain (Interactive Mode)
```
$ k8s2ai analyze --explain -f Pod

================================================================================
🐛 DETECTED ISSUES
================================================================================

[1] Pod: default/hungry-pod
    Error: Back-off pulling image "busybox": ImagePullBackOff

[2] Pod: default/nginx-deployment-abc123
    Error: CrashLoopBackOff: Container exited with code 1

--------------------------------------------------------------------------------
Select an error to work on (1-2) or 'q' to quit: 1

================================================================================
💡 SOLUTIONS FOR: Pod: default/hungry-pod
================================================================================
Error: Back-off pulling image "busybox": ImagePullBackOff

🔧 Solutions:

1. Verify network connectivity to the container registry
2. Check if the image name and tag are correct (busybox:latest)
3. Ensure registry credentials are properly configured

--------------------------------------------------------------------------------
→ Select a solution to execute (1-3), 'c' for custom solution, or 'q' to quit: 2

🚀 Executing solution with kubectl-ai...
Solution: Check if the image name and tag are correct (busybox:latest)

  Running: kubectl get pod hungry-pod -n default -o jsonpath='{.spec.containers[*].image}'
  
  Output: busybox:latest
  
  The image specification looks correct. The issue might be temporary.
  Would you like to delete and recreate the pod? (y/N): y
  
  Running: kubectl delete pod hungry-pod -n default
  pod "hungry-pod" deleted
```

### Initialization
```
$ k8s2ai init

🚀 k8s2ai Initialization
================================================================================

🔍 Checking dependencies...
  ✓ k8sgpt is installed
  ✓ kubectl-ai is installed

🔧 Setting up Gemini API...
Enter your Gemini API key: AIza****************************

ℹ Exporting GEMINI_API_KEY to environment...
  ✓ Added GEMINI_API_KEY to /Users/username/.zshrc

🔧 Configuring k8sgpt authentication...
  Removing existing Google backend (if any)...
  Adding Google backend...
  ✓ Google backend added successfully
  Setting Google as default provider...
  ✓ Google set as default provider

⭐ Initialization complete!

ℹ Note: GEMINI_API_KEY has been set for this session.
To use it in other terminal sessions, either:
  1. Restart your terminal to load from /Users/username/.zshrc
  2. Or run: source /Users/username/.zshrc
```

## How It Works

### Architecture

```
┌─────────────┐
│   k8s2ai    │
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌─────────────┐  ┌──────────────┐
│   k8sgpt    │  │  kubectl-ai  │
└──────┬──────┘  └──────┬───────┘
       │                │
       ▼                ▼
┌─────────────┐  ┌──────────────┐
│ Gemini API  │  │ Gemini API   │
└─────────────┘  └──────────────┘
       │                │
       └────────┬───────┘
                ▼
         ┌──────────────┐
         │  Kubernetes  │
         │   Cluster    │
         └──────────────┘
```

### Workflow

1. **Analysis Phase** (k8sgpt):
   - Runs `k8sgpt analyze --explain --output json`
   - k8sgpt analyzes your cluster for issues
   - Gemini AI generates detailed explanations and solutions
   - Output is captured and parsed by k8s2ai

2. **Parsing Phase** (k8s2ai):
   - Extracts issues from JSON output
   - Parses multi-step solutions into individual options
   - Groups solutions by error for better organization
   - Presents them in a user-friendly format

3. **Selection Phase** (k8s2ai):
   - Displays all detected issues with numbers
   - Prompts user to select which issue to address
   - Shows solution options for the selected issue
   - Allows custom solution input if needed

4. **Execution Phase** (kubectl-ai):
   - Sends selected solution to kubectl-ai
   - kubectl-ai uses Gemini to generate kubectl commands
   - Commands are executed against your cluster
   - Results are displayed in real-time

### Key Components

- **k8sgpt**: Analyzes Kubernetes resources and generates AI-powered diagnostics
- **kubectl-ai**: Translates natural language into kubectl commands and executes them
- **Gemini API**: Google's AI model that powers both tools
- **k8s2ai**: Orchestrates the workflow and provides the user interface

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

### Common Issues

#### k8sgpt not found
```
Error: k8sgpt command not found
```
**Solution**: Install k8sgpt from https://docs.k8sgpt.ai/getting-started/installation/

Verify installation:
```bash
k8sgpt version
```

#### kubectl-ai not found
```
Error: kubectl-ai command not found
```
**Solution**: Install via kubectl krew plugin manager
```bash
kubectl krew install ai
```

Verify installation:
```bash
kubectl ai --help
```

#### Gemini API key not set
```
Error: GEMINI_API_KEY environment variable not set
```
**Solution**: Run the init command
```bash
python3 k8s2ai.py init
```

Or manually export the key:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

#### JSON parsing errors
```
Error: Could not parse JSON output from k8sgpt
```
**Solution**: 
- Ensure k8sgpt is properly configured with an AI backend
- Check k8sgpt authentication: `k8sgpt auth list`
- Verify the backend is set: `k8sgpt auth default -p google`

#### No AI backend configured
```
Error: No default AI provider configured
```
**Solution**: Run init command or manually configure:
```bash
k8sgpt auth add --backend google --model gemini-pro --password "YOUR_API_KEY"
k8sgpt auth default -p google
```

#### Permission denied
```
Error: Permission denied when writing to ~/.zshrc
```
**Solution**: Check file permissions and run with appropriate access:
```bash
chmod 644 ~/.zshrc
```

### Getting Help

- **k8sgpt issues**: https://github.com/k8sgpt-ai/k8sgpt/issues
- **kubectl-ai issues**: https://github.com/sozercan/kubectl-ai/issues
- **k8s2ai issues**: https://github.com/lakizuru/k8s2ai/issues

## Advanced Usage

### Disable Colors

Set the `NO_COLOR` environment variable:
```bash
export NO_COLOR=1
k8s2ai analyze --explain
```

### Use with Different AI Models

k8s2ai uses `gemini-2.5-flash` for both k8sgpt and kubectl-ai by default.

To use different models, modify the configuration:
```bash
# For k8sgpt - during init or manually
k8sgpt auth add --backend google --model gemini-1.5-pro --password "YOUR_API_KEY"

# For kubectl-ai - modify the script or set environment variable
export KUBECTL_AI_MODEL="gemini-1.5-pro"
```

### Automation

Use `--auto-select` for automated workflows:
```bash
# Always select the first solution
k8s2ai analyze --explain --auto-select 1

# In scripts
if k8s2ai analyze --explain --auto-select 1; then
    echo "Issue resolved successfully"
else
    echo "Failed to resolve issue"
fi
```

### Running Without Adding to PATH

If you prefer not to add k8s2ai to your PATH:
```bash
# Run directly from the cloned directory
cd /path/to/k8s2ai
./k8s2ai analyze --explain

# Or use the full path
/path/to/k8s2ai/k8s2ai analyze --explain

# Or create a one-time alias
alias k8s2ai='/path/to/k8s2ai/k8s2ai'
```

## Configuration

### Shell Configuration Files

The `init` command automatically detects your shell and updates the appropriate config file:

- **Zsh**: `~/.zshrc`
- **Bash**: `~/.bashrc`
- **Other**: `~/.profile`

### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `NO_COLOR`: Disable colorized output (optional)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Support for multiple AI backends (OpenAI, Anthropic, etc.)
- [ ] Solution history and favorites
- [ ] Batch processing multiple errors
- [ ] Web UI for remote cluster management
- [ ] Integration with CI/CD pipelines
- [ ] Solution effectiveness tracking

## License

MIT License - feel free to use and modify as needed.

## Acknowledgments

- [k8sgpt](https://k8sgpt.ai/) - AI-powered Kubernetes diagnostics
- [kubectl-ai](https://github.com/sozercan/kubectl-ai) - Natural language kubectl commands
- [Google Gemini](https://ai.google.dev/) - Powerful AI model backing both tools

## Author

Created by [Lakizuru](https://github.com/lakizuru)

---

**Star this repository if you find it useful! ⭐**