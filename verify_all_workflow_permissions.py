#!/usr/bin/env python3
"""
Comprehensive GitHub Workflow Permissions Verification Script

This script verifies that all GitHub workflow files have proper root-level permissions
defined according to OpenSSF Scorecard recommendations.

Requirements:
- PyYAML library: pip install PyYAML

Usage:
    python verify_all_workflow_permissions.py [directory]
    
If no directory is provided, it will scan the current directory recursively.
"""

import os
import sys
import yaml
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

class WorkflowPermissionsVerifier:
    """Verifies GitHub workflow permissions compliance."""
    
    def __init__(self):
        self.valid_root_permissions = {
            'read-all',
            'write-all',  # Not recommended but valid
            'contents: read'
        }
        
        # Statistics
        self.total_files = 0
        self.files_with_errors = 0
        self.files_with_warnings = 0
        self.files_passed = 0
        
    def find_workflow_files(self, directory: str = '.') -> List[str]:
        """Find all GitHub workflow files in the given directory."""
        workflow_patterns = [
            '**/.github/workflows/*.yml',
            '**/.github/workflows/*.yaml'
        ]
        
        workflow_files = []
        for pattern in workflow_patterns:
            workflow_files.extend(glob.glob(os.path.join(directory, pattern), recursive=True))
        
        return sorted(workflow_files)
    
    def load_yaml_file(self, file_path: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Load and parse a YAML file safely."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                return content, None
        except yaml.YAMLError as e:
            return None, f"YAML parsing error: {e}"
        except Exception as e:
            return None, f"File reading error: {e}"
    
    def check_root_permissions(self, workflow_data: Dict, file_path: str) -> Tuple[bool, List[str], List[str]]:
        """
        Check if the workflow has proper root-level permissions.
        
        Returns:
            (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check if permissions key exists at root level
        if 'permissions' not in workflow_data:
            errors.append("Missing root-level 'permissions' block")
            return False, errors, warnings
        
        permissions = workflow_data['permissions']
        
        # Handle different permission formats
        if permissions is None:
            errors.append("Root-level 'permissions' block is empty")
            return False, errors, warnings
        
        if isinstance(permissions, str):
            # Single string permission like 'read-all'
            if permissions == 'read-all':
                return True, errors, warnings
            elif permissions == 'write-all':
                warnings.append("Root-level 'write-all' permission is overly permissive - consider using 'read-all' or 'contents: read'")
                return True, errors, warnings
            else:
                errors.append(f"Invalid root-level permissions string: '{permissions}'")
                return False, errors, warnings
        
        elif isinstance(permissions, dict):
            # Dictionary permissions like {'contents': 'read'}
            if len(permissions) == 1 and permissions.get('contents') == 'read':
                return True, errors, warnings
            elif len(permissions) == 0:
                errors.append("Root-level permissions block is empty")
                return False, errors, warnings
            else:
                # Check if it has more than just contents: read
                perm_items = list(permissions.items())
                if len(perm_items) > 1 or (len(perm_items) == 1 and perm_items[0] != ('contents', 'read')):
                    # Special handling for auto-generated files
                    if self.is_auto_generated_file(file_path):
                        warnings.append(f"Auto-generated file with root-level permissions: {permissions}")
                        warnings.append("Consider configuring the generation tool for minimal permissions if possible")
                        return True, errors, warnings
                    else:
                        warnings.append(f"Root-level permissions should be limited to 'contents: read' or 'read-all'. Found: {permissions}")
                        warnings.append("Consider moving specific permissions to job level if needed")
                        return True, errors, warnings
                else:
                    return True, errors, warnings
        
        else:
            errors.append(f"Invalid root-level permissions format: {type(permissions)}")
            return False, errors, warnings
    
    def is_auto_generated_file(self, file_path: str) -> bool:
        """Check if a file appears to be auto-generated."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = ''.join(f.readlines()[:10])
                auto_gen_indicators = [
                    'autogenerated',
                    'auto-generated', 
                    'automatically generated',
                    'cargo-dist',
                    'DO NOT EDIT'
                ]
                return any(indicator.lower() in first_lines.lower() for indicator in auto_gen_indicators)
        except:
            return False
    
    def analyze_job_permissions(self, workflow_data: Dict) -> Dict[str, Any]:
        """Analyze job-level permissions for informational purposes."""
        job_analysis = {}
        
        if 'jobs' not in workflow_data:
            return job_analysis
        
        jobs = workflow_data['jobs']
        if not isinstance(jobs, dict):
            return job_analysis
        
        for job_name, job_data in jobs.items():
            if not isinstance(job_data, dict):
                continue
                
            analysis = {
                'has_permissions': False,
                'permissions': None,
                'is_reusable_workflow': False,
                'has_steps': False
            }
            
            # Check if job has permissions
            if 'permissions' in job_data:
                analysis['has_permissions'] = True
                analysis['permissions'] = job_data['permissions']
            
            # Check if it's a reusable workflow call
            if 'uses' in job_data and 'steps' not in job_data:
                analysis['is_reusable_workflow'] = True
            
            # Check if it has steps
            if 'steps' in job_data:
                analysis['has_steps'] = True
            
            job_analysis[job_name] = analysis
        
        return job_analysis
    
    def verify_workflow_file(self, file_path: str) -> Dict[str, Any]:
        """Verify a single workflow file."""
        result = {
            'file_path': file_path,
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'job_analysis': {},
            'is_auto_generated': False
        }
        
        # Check if file is auto-generated
        result['is_auto_generated'] = self.is_auto_generated_file(file_path)
        
        # Load the YAML file
        workflow_data, load_error = self.load_yaml_file(file_path)
        if load_error:
            result['errors'].append(load_error)
            return result
        
        if not isinstance(workflow_data, dict):
            result['errors'].append("Workflow file is not a valid YAML dictionary")
            return result
        
        # Check root-level permissions
        is_valid, errors, warnings = self.check_root_permissions(workflow_data, file_path)
        result['is_valid'] = is_valid
        result['errors'].extend(errors)
        result['warnings'].extend(warnings)
        
        # Analyze job-level permissions
        result['job_analysis'] = self.analyze_job_permissions(workflow_data)
        
        return result
    
    def print_file_result(self, result: Dict[str, Any]) -> None:
        """Print the verification result for a single file."""
        file_path = result['file_path']
        relative_path = os.path.relpath(file_path)
        
        # Update statistics regardless of whether we print
        if result['is_valid']:
            if result['warnings']:
                self.files_with_warnings += 1
            else:
                self.files_passed += 1
        else:
            self.files_with_errors += 1
        
        # Only print if this method is not suppressed
        if not hasattr(self, '_suppress_output'):
            status_icon = ""
            if result['is_valid']:
                if result['warnings']:
                    status_icon = "⚠️ "
                else:
                    status_icon = "✅"
            else:
                status_icon = "❌"
            
            auto_gen_indicator = " (auto-generated)" if result['is_auto_generated'] else ""
            print(f"{status_icon} {relative_path}{auto_gen_indicator}")
            
            # Print errors
            for error in result['errors']:
                print(f"   ERROR: {error}")
            
            # Print warnings
            for warning in result['warnings']:
                print(f"   WARNING: {warning}")
            
            # Print job analysis if there are jobs with permissions
            job_analysis = result['job_analysis']
            jobs_with_permissions = [name for name, analysis in job_analysis.items() if analysis['has_permissions']]
            
            if jobs_with_permissions:
                print(f"   📝 Jobs with permissions: {', '.join(jobs_with_permissions)}")
            
            print()  # Empty line for readability
    
    def verify_all_workflows(self, directory: str = '.') -> Dict[str, Any]:
        """Verify all workflow files in the given directory."""
        workflow_files = self.find_workflow_files(directory)
        
        if not workflow_files:
            print(f"No GitHub workflow files found in {directory}")
            return {'summary': 'No workflows found'}
        
        print(f"Found {len(workflow_files)} workflow file(s) to verify:\n")
        
        results = []
        for file_path in workflow_files:
            self.total_files += 1
            result = self.verify_workflow_file(file_path)
            results.append(result)
            self.print_file_result(result)
        
        # Print summary
        print("=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Total files checked: {self.total_files}")
        print(f"✅ Passed: {self.files_passed}")
        print(f"⚠️  Warnings: {self.files_with_warnings}")
        print(f"❌ Errors: {self.files_with_errors}")
        
        if self.files_with_errors > 0:
            print(f"\n❌ {self.files_with_errors} file(s) have errors that need to be fixed")
            sys.exit(1)
        elif self.files_with_warnings > 0:
            print(f"\n⚠️  {self.files_with_warnings} file(s) have warnings - review recommended")
        else:
            print(f"\n🎉 All workflow files have proper root-level permissions!")
        
        return {
            'total_files': self.total_files,
            'files_passed': self.files_passed,
            'files_with_warnings': self.files_with_warnings,
            'files_with_errors': self.files_with_errors,
            'results': results
        }

def main():
    """Main function to run the verification."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Verify GitHub workflow permissions compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python verify_all_workflow_permissions.py
    python verify_all_workflow_permissions.py /path/to/repo
    python verify_all_workflow_permissions.py --help
        """
    )
    
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Directory to scan for workflow files (default: current directory)'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Only show summary (suppress individual file results)'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        sys.exit(1)
    
    print("GitHub Workflow Permissions Verification")
    print("=" * 60)
    print(f"Scanning directory: {os.path.abspath(args.directory)}")
    print()
    
    verifier = WorkflowPermissionsVerifier()
    
    # Temporarily suppress individual file output if quiet mode
    if args.quiet:
        verifier._suppress_output = True
    
    try:
        summary = verifier.verify_all_workflows(args.directory)
    
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()