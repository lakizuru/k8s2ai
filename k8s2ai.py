#!/usr/bin/env python3
"""
k8s2ai - CLI tool to analyze Kubernetes issues with k8sgpt and execute solutions via kubectl-ai
"""

import json
import subprocess
import sys
import argparse
import re
from typing import Dict, List, Any, Optional, Tuple


def run_k8sgpt(k8sgpt_args: List[str], need_json: bool = False) -> Tuple[subprocess.CompletedProcess, Optional[Dict[str, Any]]]:
    """Run k8sgpt with provided arguments and return the result and optionally parsed JSON."""
    try:
        # Build the command
        cmd = ["k8sgpt"] + k8sgpt_args
        
        # If we need JSON output, add --output json if not present
        if need_json:
            has_output_flag = False
            for arg in k8sgpt_args:
                if arg in ["--output", "-o"]:
                    has_output_flag = True
                    break
            
            if not has_output_flag:
                cmd.extend(["--output", "json"])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        # If command failed and we added --output json, try without it (in case it's not supported)
        if result.returncode != 0 and need_json and not has_output_flag:
            cmd_no_output = ["k8sgpt"] + k8sgpt_args
            result = subprocess.run(
                cmd_no_output,
                capture_output=True,
                text=True,
                check=False
            )
        
        # Parse JSON if needed
        parsed_json = None
        if need_json and result.returncode == 0:
            output = result.stdout.strip()
            
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


def display_solutions(solutions: List[Dict[str, Any]]):
    """Display solutions grouped by error in a user-friendly format."""
    if not solutions:
        print("No solutions found.")
        return
    
    # Group solutions by error
    grouped = group_solutions_by_error(solutions)
    
    print("\n" + "="*80)
    print("DETECTED ISSUES AND SOLUTIONS")
    print("="*80 + "\n")
    
    solution_id = 1
    for error_key, error_solutions in grouped.items():
        # All solutions in this group have the same kind, name, and error
        first_sol = error_solutions[0]
        
        print(f"Error: {first_sol['kind']}: {first_sol['name']}")
        error_display = first_sol['error'][:150] + "..." if len(first_sol['error']) > 150 else first_sol['error']
        print(f"  {error_display}")
        print(f"\n  Solutions:")
        
        for sol in error_solutions:
            sol['display_id'] = solution_id
            print(f"    [{solution_id}] {sol['solution']}")
            solution_id += 1
        print()


def select_solution(solutions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prompt user to select a solution or enter a custom one."""
    if not solutions:
        return None
    
    # Create a mapping from display_id to solution
    id_to_solution = {}
    for sol in solutions:
        if 'display_id' in sol:
            id_to_solution[sol['display_id']] = sol
    
    max_id = max(id_to_solution.keys()) if id_to_solution else len(solutions)
    
    while True:
        try:
            print("\n" + "-"*80)
            choice = input(f"Select a solution to execute (1-{max_id}), 'c' for custom solution, or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                return None
            
            if choice.lower() == 'c':
                # Prompt for custom solution
                return prompt_custom_solution(solutions)
            
            choice_num = int(choice)
            if choice_num in id_to_solution:
                return id_to_solution[choice_num]
            elif 1 <= choice_num <= len(solutions):
                # Fallback: use index if display_id not found
                return solutions[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {max_id}, 'c' for custom, or 'q' to quit")
        except ValueError:
            print("Please enter a valid number, 'c' for custom solution, or 'q' to quit")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def prompt_custom_solution(solutions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prompt user to enter a custom solution."""
    if not solutions:
        return None
    
    # Get the first error context (they should all be similar if grouped)
    first_sol = solutions[0]
    
    print("\n" + "-"*80)
    print("Enter your custom solution:")
    print(f"Context: {first_sol['kind']}: {first_sol['name']}")
    error_display = first_sol['error'][:150] + "..." if len(first_sol['error']) > 150 else first_sol['error']
    print(f"Error: {error_display}")
    print("\n(Enter your solution text. Press Enter on an empty line to finish, or Ctrl+D/Ctrl+Z)")
    
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
            print("No solution entered. Cancelled.")
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
        # Run kubectl-ai interactively with --model gemini-2.5-flash and the solution prompt
        # Don't capture output so it runs interactively
        result = subprocess.run(
            ["kubectl", "ai", "--model", "gemini-2.5-flash", prompt],
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return True
        else:
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
        result, data = run_k8sgpt(k8sgpt_args, need_json=True)
        
        # Print any non-JSON output from k8sgpt (if any)
        output = result.stdout.strip()
        if output and not output.startswith("{"):
            # Try to find where JSON starts
            lines = output.split('\n')
            json_start = None
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start is not None and json_start > 0:
                # Print everything before JSON
                print('\n'.join(lines[:json_start]))
        
        # Check for errors
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
        
        if not data:
            print("Error: Could not parse JSON output from k8sgpt", file=sys.stderr)
            print(f"Output: {result.stdout}", file=sys.stderr)
            sys.exit(1)
        
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
        # Without --explain: behave exactly like k8sgpt
        # First try to run normally (without forcing JSON)
        result, _ = run_k8sgpt(k8sgpt_args, need_json=False)
        
        # Print the original k8sgpt output
        print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        # Try to parse JSON from output if available (for showing solutions)
        output = result.stdout.strip()
        data = None
        if output.startswith("{"):
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
                    # Group and display solutions
                    grouped = group_solutions_by_error(solutions)
                    print("\n" + "="*80)
                    print("SOLUTIONS SUMMARY")
                    print("="*80 + "\n")
                    
                    solution_id = 1
                    for error_key, error_solutions in grouped.items():
                        first_sol = error_solutions[0]
                        print(f"Error: {first_sol['kind']}: {first_sol['name']}")
                        error_display = first_sol['error'][:150] + "..." if len(first_sol['error']) > 150 else first_sol['error']
                        print(f"  {error_display}")
                        print(f"\n  Solutions:")
                        for sol in error_solutions:
                            print(f"    [{solution_id}] {sol['solution']}")
                            solution_id += 1
                        print()
                    print("(Use --explain flag to interactively select and execute solutions)")
        
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()

