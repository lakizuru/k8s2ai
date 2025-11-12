#!/usr/bin/env python3
"""
k8s2ai - CLI tool to analyze Kubernetes issues with k8sgpt and execute solutions via kubectl-ai
"""

import json
import subprocess
import sys
import argparse
import re
import os
import threading
import time
from typing import Dict, List, Any, Optional, Tuple

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'

# Emojis
class Emoji:
    CHECK = '✓'
    CROSS = '✗'
    WARNING = '⚠'
    INFO = 'ℹ'
    ROCKET = '🚀'
    WRENCH = '🔧'
    CLIPBOARD = '📋'
    MAG = '🔍'
    BUG = '🐛'
    LIGHTBULB = '💡'
    ARROW = '→'
    STAR = '⭐'

# Disable colors if output is not a terminal or NO_COLOR env var is set
def should_colorize():
    return os.getenv('NO_COLOR') is None and sys.stdout.isatty()

def colorize(text: str, color: str) -> str:
    """Apply color to text if colorization is enabled."""
    if should_colorize():
        return f"{color}{text}{Colors.RESET}"
    return text

def bold(text: str) -> str:
    """Make text bold."""
    return colorize(text, Colors.BOLD)


def run_k8sgpt(k8sgpt_args: List[str], need_json: bool = False) -> Tuple[subprocess.CompletedProcess, Optional[Dict[str, Any]]]:
    """Run k8sgpt with provided arguments and return the result and optionally parsed JSON."""
    try:
        # Build the command
        cmd = ["k8sgpt"] + k8sgpt_args
        
        # If we need JSON output, add --output json if not present
        has_output_flag = False
        if need_json:
            for arg in k8sgpt_args:
                if arg in ["--output", "-o"]:
                    has_output_flag = True
                    break
            
            if not has_output_flag:
                cmd.extend(["--output", "json"])
        
        # If we need JSON, stream output live but also capture it
        if need_json:
            # Use Popen to stream output live while capturing it
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Stream output live and capture it
            stdout_chunks = []
            stderr_chunks = []
            
            def read_stdout():
                """Read from stdout in small chunks to preserve progress bars."""
                try:
                    json_started = False
                    while True:
                        # Read in small chunks to preserve \r for progress bars
                        chunk = process.stdout.read(1024)
                        if not chunk:
                            break
                        stdout_chunks.append(chunk)  # Always capture for parsing
                        
                        # Check if JSON has started (look for opening brace)
                        if not json_started:
                            # Check if this chunk contains the start of JSON
                            if '{' in chunk:
                                # Find where JSON starts
                                json_idx = chunk.find('{')
                                # Print everything before JSON
                                if json_idx > 0:
                                    sys.stdout.write(chunk[:json_idx])
                                    sys.stdout.flush()
                                # Don't print the JSON part
                                json_started = True
                            else:
                                # No JSON yet, print everything
                                sys.stdout.write(chunk)
                                sys.stdout.flush()
                        # If JSON has started, don't print it (but it's already in stdout_chunks for parsing)
                except (ValueError, OSError):
                    pass  # Stream closed
            
            def read_stderr():
                """Read from stderr in small chunks."""
                try:
                    while True:
                        chunk = process.stderr.read(1024)
                        if not chunk:
                            break
                        stderr_chunks.append(chunk)
                        # Print stderr immediately
                        sys.stderr.write(chunk)
                        sys.stderr.flush()
                except (ValueError, OSError):
                    pass  # Stream closed
            
            # Start threads to read both streams concurrently
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process to complete
            returncode = process.wait()
            
            # Wait for threads to finish reading
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)
            
            # Use captured chunks (which may have JSON filtered out in display)
            stdout = ''.join(stdout_chunks)
            stderr = ''.join(stderr_chunks)
            
            # Create a CompletedProcess-like result
            result = subprocess.CompletedProcess(
                cmd, returncode, stdout, stderr
            )
            
            # If command failed and we added --output json, try without it (in case it's not supported)
            if returncode != 0 and not has_output_flag:
                # Retry without --output json
                cmd_no_output = ["k8sgpt"] + k8sgpt_args
                process = subprocess.Popen(
                    cmd_no_output,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                stdout_chunks = []
                stderr_chunks = []
                
                def read_stdout_retry():
                    try:
                        while True:
                            chunk = process.stdout.read(1024)
                            if not chunk:
                                break
                            stdout_chunks.append(chunk)
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                    except (ValueError, OSError):
                        pass
                
                def read_stderr_retry():
                    try:
                        while True:
                            chunk = process.stderr.read(1024)
                            if not chunk:
                                break
                            stderr_chunks.append(chunk)
                            sys.stderr.write(chunk)
                            sys.stderr.flush()
                    except (ValueError, OSError):
                        pass
                
                stdout_thread = threading.Thread(target=read_stdout_retry, daemon=True)
                stderr_thread = threading.Thread(target=read_stderr_retry, daemon=True)
                
                stdout_thread.start()
                stderr_thread.start()
                
                returncode = process.wait()
                
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)
                
                stdout = ''.join(stdout_chunks)
                stderr = ''.join(stderr_chunks)
                
                result = subprocess.CompletedProcess(
                    cmd_no_output, returncode, stdout, stderr
                )
        else:
            # For non-JSON mode, just run normally (output goes directly to terminal)
            result = subprocess.run(
                cmd,
                text=True,
                check=False
            )
            # When not capturing output, stdout/stderr are None
            stdout = result.stdout if result.stdout is not None else ""
            stderr = result.stderr if result.stderr is not None else ""
        
        # Parse JSON if needed
        parsed_json = None
        if need_json and result.returncode == 0:
            output = stdout.strip()
            
            # Try to parse JSON from stdout
            if output.startswith("{"):
                try:
                    parsed_json = json.loads(output)
                except json.JSONDecodeError:
                    pass
            else:
                # Try to find JSON in the output
                lines = output.split('\n')
                json_start = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('{'):
                        json_start = i
                        break
                
                if json_start is not None:
                    json_str = '\n'.join(lines[json_start:])
                    try:
                        parsed_json = json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
        
        return result, parsed_json
                
    except FileNotFoundError:
        print(colorize(f"{Emoji.CROSS} Error: k8sgpt command not found. Please install k8sgpt first.", Colors.BOLD + Colors.RED), file=sys.stderr)
        sys.exit(1)


def extract_solutions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract solutions from k8sgpt output."""
    solutions = []
    
    if not data.get("results"):
        return solutions
    
    for result in data["results"]:
        if result.get("error") and result.get("details"):
            # Parse the details field which contains the solution
            details = result.get("details", "")
            
            # Get error text (handle both single error object and list)
            error_text = "Unknown error"
            error_obj = result.get("error", [])
            if isinstance(error_obj, list) and len(error_obj) > 0:
                error_text = error_obj[0].get("Text", "Unknown error")
            elif isinstance(error_obj, dict):
                error_text = error_obj.get("Text", "Unknown error")
            
            # Split solution into individual steps
            solution_steps = []
            if "Solution:" in details:
                solution_part = details.split("Solution:")[1].strip()
                # Split by numbered steps (1., 2., 3., etc.)
                # Match lines starting with a number followed by a dot and space
                step_pattern = r'^(\d+)\.\s+(.+)$'
                lines = solution_part.split('\n')
                current_step = ""
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if line matches the numbered step pattern
                    match = re.match(step_pattern, line)
                    if match:
                        # Save previous step if exists
                        if current_step:
                            solution_steps.append(current_step.strip())
                        # Start new step
                        current_step = line
                    else:
                        # Continuation of current step
                        if current_step:
                            current_step += " " + line
                        else:
                            # First line without number, treat as step 1
                            current_step = line
                
                # Add the last step
                if current_step:
                    solution_steps.append(current_step.strip())
            else:
                # If no structured solution, use the whole details as one solution
                solution_steps = [details]
            
            # Create a solution entry for each step
            for idx, step in enumerate(solution_steps, 1):
                solutions.append({
                    "id": len(solutions) + 1,
                    "kind": result.get("kind", "Unknown"),
                    "name": result.get("name", "Unknown"),
                    "error": error_text,
                    "solution": step,
                    "full_details": details
                })
    
    return solutions


def group_solutions_by_error(solutions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group solutions by error (kind + name + error text)."""
    grouped = {}
    for sol in solutions:
        # Create a unique key for each error
        key = f"{sol['kind']}|{sol['name']}|{sol['error']}"
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(sol)
    return grouped


def display_errors(grouped: Dict[str, List[Dict[str, Any]]]):
    """Display errors in a user-friendly format."""
    if not grouped:
        print(colorize("No errors found.", Colors.YELLOW))
        return
    
    print("\n" + colorize("="*80, Colors.CYAN))
    print(colorize(f"{Emoji.BUG} DETECTED ISSUES", Colors.BOLD + Colors.CYAN))
    print(colorize("="*80, Colors.CYAN) + "\n")
    
    error_id = 1
    for error_key, error_solutions in grouped.items():
        first_sol = error_solutions[0]
        error_display = first_sol['error'][:150] + "..." if len(first_sol['error']) > 150 else first_sol['error']
        kind_name = f"{first_sol['kind']}: {first_sol['name']}"
        print(colorize(f"[{error_id}]", Colors.BRIGHT_CYAN) + " " + 
              colorize(kind_name, Colors.BOLD + Colors.YELLOW))
        print("    " + colorize(error_display, Colors.RED))
        print()
        error_id += 1


def display_solutions_for_error(error_solutions: List[Dict[str, Any]]):
    """Display solutions for a specific error."""
    if not error_solutions:
        print(colorize("No solutions found for this error.", Colors.YELLOW))
        return
    
    first_sol = error_solutions[0]
    kind_name = f"{first_sol['kind']}: {first_sol['name']}"
    print("\n" + colorize("="*80, Colors.CYAN))
    print(colorize(f"{Emoji.LIGHTBULB} SOLUTIONS FOR: {kind_name}", Colors.BOLD + Colors.CYAN))
    print(colorize("="*80, Colors.CYAN))
    error_display = first_sol['error'][:150] + "..." if len(first_sol['error']) > 150 else first_sol['error']
    print(colorize("Error:", Colors.BOLD + Colors.RED) + " " + colorize(error_display, Colors.RED))
    print("\n" + colorize(f"{Emoji.WRENCH} Solutions:", Colors.BOLD + Colors.GREEN) + "\n")
    
    # Display as a numbered list
    for idx, sol in enumerate(error_solutions, 1):
        sol['display_id'] = idx
        print(colorize(f"{idx}.", Colors.BRIGHT_CYAN) + " " + 
              colorize(sol['solution'], Colors.WHITE))
    print()


def select_error(grouped: Dict[str, List[Dict[str, Any]]]) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    """Prompt user to select which error to work on."""
    if not grouped:
        return None
    
    error_list = list(grouped.items())
    
    while True:
        try:
            print("\n" + "-"*80)
            choice = input(f"Select an error to work on (1-{len(error_list)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(error_list):
                return error_list[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(error_list)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def select_solution(error_solutions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prompt user to select a solution or enter a custom one for the selected error."""
    if not error_solutions:
        return None
    
    # Create a mapping from display_id to solution
    id_to_solution = {}
    for sol in error_solutions:
        if 'display_id' in sol:
            id_to_solution[sol['display_id']] = sol
    
    max_id = max(id_to_solution.keys()) if id_to_solution else len(error_solutions)
    
    while True:
        try:
            print("\n" + colorize("-"*80, Colors.DIM))
            prompt_text = colorize(f"{Emoji.ARROW} Select a solution to execute", Colors.BOLD + Colors.CYAN) + \
                         colorize(f" (1-{max_id})", Colors.CYAN) + \
                         colorize(", 'c' for custom solution", Colors.MAGENTA) + \
                         colorize(", or 'q' to quit", Colors.DIM) + ": "
            choice = input(prompt_text).strip()
            
            if choice.lower() == 'q':
                return None
            
            if choice.lower() == 'c':
                # Prompt for custom solution
                return prompt_custom_solution(error_solutions)
            
            choice_num = int(choice)
            if choice_num in id_to_solution:
                return id_to_solution[choice_num]
            elif 1 <= choice_num <= len(error_solutions):
                # Fallback: use index if display_id not found
                return error_solutions[choice_num - 1]
            else:
                print(colorize(f"Please enter a number between 1 and {max_id}, 'c' for custom, or 'q' to quit", Colors.YELLOW))
        except ValueError:
            print(colorize("Please enter a valid number, 'c' for custom solution, or 'q' to quit", Colors.YELLOW))
        except KeyboardInterrupt:
            print("\n" + colorize("Cancelled.", Colors.YELLOW))
            return None


def prompt_custom_solution(solutions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prompt user to enter a custom solution."""
    if not solutions:
        return None
    
    # Get the first error context (they should all be similar if grouped)
    first_sol = solutions[0]
    
    print("\n" + colorize("-"*80, Colors.DIM))
    print(colorize(f"{Emoji.WRENCH} Enter your custom solution:", Colors.BOLD + Colors.MAGENTA))
    kind_name = f"{first_sol['kind']}: {first_sol['name']}"
    print(colorize("Context:", Colors.BOLD) + " " + colorize(kind_name, Colors.YELLOW))
    error_display = first_sol['error'][:150] + "..." if len(first_sol['error']) > 150 else first_sol['error']
    print(colorize("Error:", Colors.BOLD + Colors.RED) + " " + colorize(error_display, Colors.RED))
    print("\n" + colorize("(Enter your solution text. Press Enter on an empty line to finish, or Ctrl+D/Ctrl+Z)", Colors.DIM))
    
    try:
        custom_solution_lines = []
        
        while True:
            try:
                line = input()
                if line.strip() == "":
                    if custom_solution_lines:
                        # Empty line after content - finish
                        break
                    # Empty line before any content - continue
                    continue
                custom_solution_lines.append(line)
            except EOFError:
                # Ctrl+D (Unix) or Ctrl+Z (Windows) pressed
                break
        
        custom_solution = "\n".join(custom_solution_lines).strip()
        
        if not custom_solution:
            print(colorize("No solution entered. Cancelled.", Colors.YELLOW))
            return None
        
        # Create a solution dict with custom solution
        return {
            "kind": first_sol['kind'],
            "name": first_sol['name'],
            "error": first_sol['error'],
            "solution": custom_solution,
            "full_details": f"Custom solution: {custom_solution}",
            "is_custom": True
        }
    except KeyboardInterrupt:
        print("\n" + colorize("Cancelled.", Colors.YELLOW))
        return None


def execute_with_kubectl_ai(solution: Dict[str, Any]) -> bool:
    """Execute the selected solution using kubectl-ai."""
    print(f"\n{colorize(f'{Emoji.ROCKET} Executing solution with kubectl-ai...', Colors.BOLD + Colors.GREEN)}")
    print(colorize("Solution:", Colors.BOLD) + " " + colorize(solution['solution'], Colors.WHITE))
    
    # Construct the prompt for kubectl-ai
    prompt = f"Fix the following Kubernetes issue:\n\n"
    prompt += f"Kind: {solution['kind']}\n"
    prompt += f"Name: {solution['name']}\n"
    prompt += f"Error: {solution['error']}\n\n"
    prompt += f"Apply this solution: {solution['solution']}"
    
    try:
        # Run kubectl-ai interactively and monitor output
        # When kubectl-ai stops producing output (no more prompts/questions), exit automatically
        process = subprocess.Popen(
            ["kubectl", "ai", "--model", "gemini-2.5-flash", prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Stream output and detect when it stops
        last_output_time = time.time()
        no_output_timeout = 3.0  # If no output for 3 seconds, consider it done
        max_wait_time = 300  # Maximum 5 minutes total
        start_time = time.time()
        has_output = False
        
        def read_stream(stream, is_stderr=False):
            """Read from stream and print output."""
            nonlocal last_output_time, has_output
            try:
                for line in stream:
                    has_output = True
                    last_output_time = time.time()
                    if is_stderr:
                        print(line, end='', file=sys.stderr, flush=True)
                    else:
                        print(line, end='', flush=True)
            except (ValueError, OSError):
                pass  # Stream closed
        
        # Start threads to read both streams
        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, False), daemon=True)
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, True), daemon=True)
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Monitor until process exits or no output timeout
        while process.poll() is None:
            # Check max wait time
            if time.time() - start_time > max_wait_time:
                process.terminate()
                break
            
            # Check if no output for timeout period (kubectl-ai stopped prompting)
            if has_output and (time.time() - last_output_time) > no_output_timeout:
                # No output for a while - kubectl-ai is done (no more prompts)
                process.terminate()
                break
            
            time.sleep(0.1)  # Small sleep to avoid busy waiting
        
        # Wait for threads to finish
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        # Wait for process to complete
        try:
            returncode = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            returncode = process.wait()
        
        return returncode == 0
            
    except FileNotFoundError:
        print(colorize(f"{Emoji.CROSS} Error: kubectl-ai command not found.", Colors.BOLD + Colors.RED), file=sys.stderr)
        print(colorize("Install with:", Colors.YELLOW) + " " + 
              colorize("kubectl krew install ai", Colors.BOLD + Colors.CYAN), file=sys.stderr)
        return False
    except Exception as e:
        print(colorize(f"{Emoji.CROSS} Error executing solution: {e}", Colors.BOLD + Colors.RED), file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="k8s2ai - Alias for k8sgpt with kubectl-ai integration",
        add_help=False
    )
    parser.add_argument(
        "--auto-select",
        type=int,
        metavar="N",
        help="Automatically select solution N without prompting (requires --explain)"
    )
    
    # Parse known args and capture remaining args for k8sgpt
    args, k8sgpt_args = parser.parse_known_args()
    
    # If no k8sgpt args provided, default to "analyze"
    if not k8sgpt_args:
        k8sgpt_args = ["analyze"]
    
    # Check if --explain is present
    has_explain = "--explain" in k8sgpt_args
    
    if has_explain:
        # With --explain: run k8sgpt, parse JSON, show solutions, prompt to pick, execute
        # Note: run_k8sgpt already prints output live (excluding JSON), so we don't need to print it again
        result, data = run_k8sgpt(k8sgpt_args, need_json=True)
        
        # Check for errors
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
        
        if not data:
            print(colorize(f"{Emoji.CROSS} Error: Could not parse JSON output from k8sgpt", Colors.BOLD + Colors.RED), file=sys.stderr)
            print(colorize(f"Output: {result.stdout}", Colors.YELLOW), file=sys.stderr)
            sys.exit(1)
        
        # Check if there are any problems
        if data.get("status") == "OK" or data.get("problems", 0) == 0:
            print(colorize(f"{Emoji.CHECK} No problems detected!", Colors.BOLD + Colors.GREEN))
            return
        
        # Extract solutions
        solutions = extract_solutions(data)
        
        if not solutions:
            print(colorize(f"{Emoji.INFO} No solutions found in the analysis results.", Colors.YELLOW))
            return
        
        # Group solutions by error
        grouped = group_solutions_by_error(solutions)
        
        # If only one error, skip error selection
        if len(grouped) == 1:
            error_key, error_solutions = list(grouped.items())[0]
            display_solutions_for_error(error_solutions)
            
            # Select solution
            if args.auto_select:
                if 1 <= args.auto_select <= len(error_solutions):
                    selected = error_solutions[args.auto_select - 1]
                else:
                    print(colorize(f"{Emoji.CROSS} Error: Solution number {args.auto_select} is out of range (1-{len(error_solutions)})", Colors.BOLD + Colors.RED), file=sys.stderr)
                    sys.exit(1)
            else:
                selected = select_solution(error_solutions)
            
            if selected:
                # Execute with kubectl-ai
                success = execute_with_kubectl_ai(selected)
                sys.exit(0 if success else 1)
            else:
                print(colorize("No solution selected. Exiting.", Colors.YELLOW))
        else:
            # Multiple errors: first select error, then solution
            display_errors(grouped)
            
            # Select error
            error_selection = select_error(grouped)
            if not error_selection:
                print(colorize("No error selected. Exiting.", Colors.YELLOW))
                return
            
            error_key, error_solutions = error_selection
            display_solutions_for_error(error_solutions)
            
            # Select solution
            if args.auto_select:
                if 1 <= args.auto_select <= len(error_solutions):
                    selected = error_solutions[args.auto_select - 1]
                else:
                    print(colorize(f"{Emoji.CROSS} Error: Solution number {args.auto_select} is out of range (1-{len(error_solutions)})", Colors.BOLD + Colors.RED), file=sys.stderr)
                    sys.exit(1)
            else:
                selected = select_solution(error_solutions)
            
            if selected:
                # Execute with kubectl-ai
                success = execute_with_kubectl_ai(selected)
                sys.exit(0 if success else 1)
            else:
                print(colorize("No solution selected. Exiting.", Colors.YELLOW))
    else:
        # Without --explain: behave exactly like k8sgpt
        # First try to run normally (without forcing JSON)
        result, _ = run_k8sgpt(k8sgpt_args, need_json=False)
        
        # Print the original k8sgpt output (if captured)
        # Note: When not capturing, output goes directly to terminal, so result.stdout is None
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        # Try to parse JSON from output if available (for showing solutions)
        # result.stdout might be None if output wasn't captured
        output = result.stdout.strip() if result.stdout else ""
        data = None
        if output and output.startswith("{"):
            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                pass
        else:
            # Try to find JSON in the output
            lines = output.split('\n')
            json_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start is not None:
                json_str = '\n'.join(lines[json_start:])
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # If we got JSON and there are problems, also show solutions in a nice format
        if data and result.returncode == 0:
            if data.get("status") != "OK" and data.get("problems", 0) > 0:
                solutions = extract_solutions(data)
                if solutions:
                    # Group and display solutions by error
                    grouped = group_solutions_by_error(solutions)
                    print("\n" + colorize("="*80, Colors.CYAN))
                    print(colorize(f"{Emoji.CLIPBOARD} SOLUTIONS SUMMARY", Colors.BOLD + Colors.CYAN))
                    print(colorize("="*80, Colors.CYAN) + "\n")
                    
                    for error_key, error_solutions in grouped.items():
                        first_sol = error_solutions[0]
                        kind_name = f"{first_sol['kind']}: {first_sol['name']}"
                        print(colorize("Error:", Colors.BOLD + Colors.RED) + " " + 
                              colorize(kind_name, Colors.YELLOW))
                        error_display = first_sol['error'][:150] + "..." if len(first_sol['error']) > 150 else first_sol['error']
                        print("  " + colorize(error_display, Colors.RED))
                        print(f"\n  {colorize('Solutions:', Colors.BOLD + Colors.GREEN)}")
                        for idx, sol in enumerate(error_solutions, 1):
                            print("    " + colorize(f"[{idx}]", Colors.BRIGHT_CYAN) + " " + 
                                  colorize(sol['solution'], Colors.WHITE))
                        print()
                    print(colorize("(Use --explain flag to interactively select and execute solutions)", Colors.DIM))
        
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()

