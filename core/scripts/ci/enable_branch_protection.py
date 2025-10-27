#!/usr/bin/env python3
"""
Automated Branch Protection Setup Script
Monitors GitHub Actions workflows and enables branch protection when all workflows complete successfully.
"""

import os
import sys
import time
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

class BranchProtectionManager:
    """Manages GitHub branch protection setup and monitoring"""
    
    def __init__(self):
        self.github_pat = os.getenv('GITHUB_PAT')
        self.repo_owner = 'proektor1001'
        self.repo_name = 'BZ-BrokerCursor'
        self.branch = 'main'
        
        if not self.github_pat:
            raise ValueError("GITHUB_PAT not found in environment variables")
        
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.github_pat}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'BrokerCursor-CI-Setup'
        }
        
        # Required workflows for branch protection
        self.required_workflows = [
            'code-quality.yml',
            'security.yml', 
            'unit-tests.yml',
            'docs-validation.yml',
            'dependency-check.yml'
        ]
        
        # Status check contexts (must match workflow job names)
        self.status_check_contexts = [
            'code-quality',
            'security-scan',
            'unit-tests', 
            'docs-validation',
            'dependency-check'
        ]
    
    def get_workflows(self) -> List[Dict]:
        """Get all workflows for the repository"""
        url = f'{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/workflows'
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch workflows: {response.status_code} - {response.text}")
        
        return response.json()['workflows']
    
    def get_workflow_runs(self, workflow_name: str, limit: int = 5) -> List[Dict]:
        """Get recent runs for a specific workflow"""
        url = f'{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/workflows/{workflow_name}/runs'
        params = {'per_page': limit}
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch runs for {workflow_name}: {response.status_code}")
        
        return response.json()['workflow_runs']
    
    def check_workflow_status(self) -> Dict[str, str]:
        """Check the status of all required workflows"""
        print("🔍 Checking workflow status...")
        
        workflows = self.get_workflows()
        workflow_status = {}
        
        for required_workflow in self.required_workflows:
            # Find workflow by name
            workflow = next(
                (w for w in workflows if w['name'].endswith(required_workflow)), 
                None
            )
            
            if not workflow:
                print(f"❌ Workflow {required_workflow} not found")
                workflow_status[required_workflow] = 'not_found'
                continue
            
            # Get latest runs
            runs = self.get_workflow_runs(required_workflow, limit=1)
            
            if not runs:
                print(f"❌ No runs found for {required_workflow}")
                workflow_status[required_workflow] = 'no_runs'
                continue
            
            latest_run = runs[0]
            status = latest_run['conclusion']
            state = latest_run['status']
            
            print(f"📋 {required_workflow}: {state} -> {status}")
            workflow_status[required_workflow] = status
        
        return workflow_status
    
    def wait_for_workflows_completion(self, max_wait_minutes: int = 30) -> bool:
        """Wait for all workflows to complete successfully"""
        print(f"⏳ Waiting for workflows to complete (max {max_wait_minutes} minutes)...")
        
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while time.time() - start_time < max_wait_seconds:
            status = self.check_workflow_status()
            
            # Check if all workflows are successful
            all_successful = all(
                status.get(workflow) == 'success' 
                for workflow in self.required_workflows
            )
            
            if all_successful:
                print("✅ All workflows completed successfully!")
                return True
            
            # Check if any workflow failed
            any_failed = any(
                status.get(workflow) in ['failure', 'cancelled', 'timed_out']
                for workflow in self.required_workflows
            )
            
            if any_failed:
                print("❌ Some workflows failed. Cannot enable branch protection.")
                return False
            
            # Wait before next check
            print("⏳ Workflows still running, waiting 30 seconds...")
            time.sleep(30)
        
        print(f"⏰ Timeout reached ({max_wait_minutes} minutes). Workflows may still be running.")
        return False
    
    def enable_branch_protection(self) -> bool:
        """Enable branch protection with required status checks"""
        print("🔒 Enabling branch protection...")
        
        protection_data = {
            'required_status_checks': {
                'strict': True,
                'contexts': self.status_check_contexts
            },
            'enforce_admins': False,
            'required_pull_request_reviews': {
                'required_approving_review_count': 1,
                'dismiss_stale_reviews': True,
                'require_code_owner_reviews': False
            },
            'restrictions': None
        }
        
        url = f'{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/branches/{self.branch}/protection'
        response = requests.put(url, headers=self.headers, json=protection_data)
        
        if response.status_code == 200:
            print("✅ Branch protection enabled successfully!")
            return True
        else:
            print(f"❌ Error enabling branch protection: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    def verify_branch_protection(self) -> bool:
        """Verify branch protection is active and properly configured"""
        print("🔍 Verifying branch protection...")
        
        url = f'{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/branches/{self.branch}/protection'
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ Error verifying protection: {response.status_code}")
            return False
        
        protection = response.json()
        
        if 'required_status_checks' not in protection:
            print("❌ Branch protection not properly configured")
            return False
        
        contexts = protection['required_status_checks']['contexts']
        strict = protection['required_status_checks']['strict']
        
        print(f"✅ Branch protection active:")
        print(f"   - Strict mode: {strict}")
        print(f"   - Required contexts: {contexts}")
        
        # Verify all required contexts are present
        missing_contexts = set(self.status_check_contexts) - set(contexts)
        if missing_contexts:
            print(f"⚠️  Missing contexts: {missing_contexts}")
            return False
        
        return True
    
    def run(self) -> bool:
        """Main execution method"""
        print("=== GitHub Branch Protection Setup ===")
        print(f"Repository: {self.repo_owner}/{self.repo_name}")
        print(f"Branch: {self.branch}")
        print(f"Required workflows: {len(self.required_workflows)}")
        print()
        
        try:
            # Wait for workflows to complete
            if not self.wait_for_workflows_completion():
                print("❌ Workflows not ready. Please wait and run this script again.")
                return False
            
            # Enable branch protection
            if not self.enable_branch_protection():
                print("❌ Failed to enable branch protection")
                return False
            
            # Verify protection
            if not self.verify_branch_protection():
                print("❌ Branch protection verification failed")
                return False
            
            print("\n🎉 Branch protection setup completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during setup: {e}")
            return False

def main():
    """Main entry point"""
    try:
        manager = BranchProtectionManager()
        success = manager.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
