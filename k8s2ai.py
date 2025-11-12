#!/usr/bin/env python3
"""
k8s2ai - CLI tool to analyze Kubernetes issues with k8sgpt and execute solutions via kubectl-ai
"""

import json
import subprocess
import sys
import argparse
import re
from typing import Dict, List, Any, Optional


def run_k8sgpt_analyze(k8sgpt_args: List[str]) -> Dict[str, Any]:
    """Run k8sgpt with provided arguments and return parsed JSON output."""
    try:
        # Build the command
        cmd = ["k8sgpt"] + k8sgpt_args
        
        # Ensure we get JSON output - add --output json if not present
        # Check if --output or -o is already in the args (could be --output json or -o json)
        has_output_flag = False
        for i, arg in enumerate(k8sgpt_args):
            if arg in ["--output", "-o"]:
                has_output_flag = True
                break
        
        if not has_output_flag:
            cmd.extend(["--output", "json"])
        
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        # If command failed and we added --output json, try without it (in case it's not supported)
        if result.returncode != 0 and not has_output_flag:
            # Remove --output json and try again
            cmd_no_output = ["k8sgpt"] + k8sgpt_args
            print(f"Retrying without --output json: {' '.join(cmd_no_output)}")
            result = subprocess.run(
                cmd_no_output,
                capture_output=True,
                text=True,
                check=True
            )
        
        # Try to parse JSON from stdout
        output = result.stdout.strip()
        
        # Sometimes JSON might be mixed with other output, try to extract it
        if output.startswith("{"):
            return json.loads(output)
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
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in output")
                
    except subprocess.CalledProcessError as e:
        print(f"Error running k8sgpt: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}", file=sys.stderr)
        print(f"Output was: {result.stdout}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: k8sgpt command not found. Please install k8sgpt first.", file=sys.stderr)
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


def display_solutions(solutions: List[Dict[str, Any]]):
    """Display solutions in a user-friendly format."""
    if not solutions:
        print("No solutions found.")
        return
    
    print("\n" + "="*80)
    print("DETECTED ISSUES AND SOLUTIONS")
    print("="*80 + "\n")
    
    for sol in solutions:
        print(f"[{sol['id']}] {sol['kind']}: {sol['name']}")
        print(f"    Error: {sol['error'][:100]}..." if len(sol['error']) > 100 else f"    Error: {sol['error']}")
        print(f"    Solution: {sol['solution']}")
        print()


def select_solution(solutions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prompt user to select a solution."""
    if not solutions:
        return None
    
    while True:
        try:
            print("\n" + "-"*80)
            choice = input(f"Select a solution to execute (1-{len(solutions)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(solutions):
                return solutions[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(solutions)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def execute_with_kubectl_ai(solution: Dict[str, Any]) -> bool:
    """Execute the selected solution using kubectl-ai."""
    print(f"\nExecuting solution with kubectl-ai...")
    print(f"Solution: {solution['solution']}")
    
    # Construct the prompt for kubectl-ai
    prompt = f"Fix the following Kubernetes issue:\n\n"
    prompt += f"Kind: {solution['kind']}\n"
    prompt += f"Name: {solution['name']}\n"
    prompt += f"Error: {solution['error']}\n\n"
    prompt += f"Apply this solution: {solution['solution']}"
    
    try:
        # Try different kubectl-ai command formats
        # Format 1: kubectl ai "prompt text" (most common)
        result = subprocess.run(
            ["kubectl", "ai", prompt],
            text=True,
            check=False,
            capture_output=True
        )
        
        # If that fails, try with stdin input
        if result.returncode != 0:
            result = subprocess.run(
                ["kubectl", "ai"],
                input=prompt,
                text=True,
                check=False,
                capture_output=True
            )
        
        if result.returncode == 0:
            print("\n✓ Solution executed successfully!")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"\n✗ Error executing solution (exit code: {result.returncode})", file=sys.stderr)
            if result.stderr:
                print(f"Error output: {result.stderr}", file=sys.stderr)
            if result.stdout:
                print(f"Output: {result.stdout}", file=sys.stderr)
            return False
            
    except FileNotFoundError:
        print("Error: kubectl-ai command not found. Please install kubectl-ai plugin first.", file=sys.stderr)
        print("Install with: kubectl krew install ai", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error executing solution: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Kubernetes issues with k8sgpt and execute solutions via kubectl-ai",
        add_help=False  # We'll handle help separately
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output raw JSON from k8sgpt (for debugging)"
    )
    parser.add_argument(
        "--auto-select",
        type=int,
        metavar="N",
        help="Automatically select solution N without prompting"
    )
    parser.add_argument(
        "--help",
        action="help",
        help="Show this help message and exit"
    )
    
    # Parse known args and capture remaining args for k8sgpt
    args, k8sgpt_args = parser.parse_known_args()
    
    # If no k8sgpt args provided, default to "analyze --explain"
    if not k8sgpt_args:
        k8sgpt_args = ["analyze", "--explain"]
    
    # Run k8sgpt with provided arguments
    data = run_k8sgpt_analyze(k8sgpt_args)
    
    if args.json_output:
        print(json.dumps(data, indent=2))
        return
    
    # Check if there are any problems
    if data.get("status") == "OK" or data.get("problems", 0) == 0:
        print("✓ No problems detected!")
        return
    
    # Extract solutions
    solutions = extract_solutions(data)
    
    if not solutions:
        print("No solutions found in the analysis results.")
        return
    
    # Display solutions
    display_solutions(solutions)
    
    # Only prompt for solution selection if --explain flag is present
    has_explain = "--explain" in k8sgpt_args
    
    if has_explain:
        # Select solution
        if args.auto_select:
            if 1 <= args.auto_select <= len(solutions):
                selected = solutions[args.auto_select - 1]
            else:
                print(f"Error: Solution number {args.auto_select} is out of range (1-{len(solutions)})", file=sys.stderr)
                sys.exit(1)
        else:
            selected = select_solution(solutions)
        
        if selected:
            # Execute with kubectl-ai
            success = execute_with_kubectl_ai(selected)
            sys.exit(0 if success else 1)
        else:
            print("No solution selected. Exiting.")
    else:
        # Without --explain, just show solutions and exit
        if args.auto_select:
            print("Note: --auto-select requires --explain flag to execute solutions.", file=sys.stderr)
        print("\n(Use --explain flag to interactively select and execute solutions)")


if __name__ == "__main__":
    main()

