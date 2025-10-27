#!/usr/bin/env python3
"""
GitHub Secrets Setup Script
Syncs GITHUB_PAT from .env to GitHub Secrets for CI/CD workflows.
"""

import os
import sys
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

class GitHubSecretsManager:
    """Manages GitHub repository secrets"""
    
    def __init__(self):
        self.github_pat = os.getenv('GITHUB_PAT')
        self.repo_owner = 'proektor1001'
        self.repo_name = 'BZ-BrokerCursor'
        
        if not self.github_pat:
            raise ValueError("GITHUB_PAT not found in environment variables")
        
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.github_pat}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'BrokerCursor-Secrets-Setup'
        }
        
        # Secrets to sync from .env
        self.secrets_to_sync = {
            'GITHUB_PAT': self.github_pat,
            'DB_HOST': os.getenv('DB_HOST', ''),
            'DB_PORT': os.getenv('DB_PORT', ''),
            'DB_NAME': os.getenv('DB_NAME', ''),
            'DB_USER': os.getenv('DB_USER', ''),
            'DB_PASSWORD': os.getenv('DB_PASSWORD', ''),
        }
    
    def get_public_key(self) -> Dict[str, str]:
        """Get repository's public key for encrypting secrets"""
        url = f'{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/secrets/public-key'
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get public key: {response.status_code} - {response.text}")
        
        return response.json()
    
    def encrypt_secret(self, secret_value: str, public_key: str) -> str:
        """Encrypt secret value using repository's public key"""
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            import base64
            
            # Load public key
            public_key_obj = load_pem_public_key(public_key.encode())
            
            # Encrypt the secret
            encrypted = public_key_obj.encrypt(
                secret_value.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Return base64 encoded encrypted value
            return base64.b64encode(encrypted).decode()
            
        except ImportError:
            print("❌ cryptography library not available. Installing...")
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cryptography'])
            # Retry after installation
            return self.encrypt_secret(secret_value, public_key)
    
    def create_or_update_secret(self, secret_name: str, secret_value: str) -> bool:
        """Create or update a repository secret"""
        if not secret_value:
            print(f"⚠️  Skipping {secret_name} (empty value)")
            return True
        
        try:
            # Get public key
            public_key_info = self.get_public_key()
            public_key = public_key_info['key']
            key_id = public_key_info['key_id']
            
            # Encrypt secret
            encrypted_value = self.encrypt_secret(secret_value, public_key)
            
            # Create/update secret
            url = f'{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/secrets/{secret_name}'
            data = {
                'encrypted_value': encrypted_value,
                'key_id': key_id
            }
            
            response = requests.put(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                print(f"✅ Secret {secret_name} updated successfully")
                return True
            else:
                print(f"❌ Failed to update secret {secret_name}: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating secret {secret_name}: {e}")
            return False
    
    def list_existing_secrets(self) -> List[str]:
        """List existing repository secrets"""
        url = f'{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/actions/secrets'
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to list secrets: {response.status_code}")
            return []
        
        secrets = response.json()['secrets']
        return [secret['name'] for secret in secrets]
    
    def sync_secrets(self) -> bool:
        """Sync all configured secrets to GitHub"""
        print("🔐 Syncing secrets to GitHub...")
        
        # List existing secrets
        existing_secrets = self.list_existing_secrets()
        print(f"📋 Existing secrets: {existing_secrets}")
        
        success_count = 0
        total_count = len(self.secrets_to_sync)
        
        for secret_name, secret_value in self.secrets_to_sync.items():
            if self.create_or_update_secret(secret_name, secret_value):
                success_count += 1
        
        print(f"\n📊 Secrets sync summary:")
        print(f"   - Total: {total_count}")
        print(f"   - Success: {success_count}")
        print(f"   - Failed: {total_count - success_count}")
        
        return success_count == total_count
    
    def verify_secrets(self) -> bool:
        """Verify that secrets are accessible (basic check)"""
        print("🔍 Verifying secrets...")
        
        existing_secrets = self.list_existing_secrets()
        required_secrets = ['GITHUB_PAT']
        
        for secret_name in required_secrets:
            if secret_name in existing_secrets:
                print(f"✅ Secret {secret_name} is available")
            else:
                print(f"❌ Secret {secret_name} is missing")
                return False
        
        return True
    
    def run(self) -> bool:
        """Main execution method"""
        print("=== GitHub Secrets Setup ===")
        print(f"Repository: {self.repo_owner}/{self.repo_name}")
        print(f"Secrets to sync: {len(self.secrets_to_sync)}")
        print()
        
        try:
            # Sync secrets
            if not self.sync_secrets():
                print("❌ Failed to sync all secrets")
                return False
            
            # Verify secrets
            if not self.verify_secrets():
                print("❌ Secret verification failed")
                return False
            
            print("\n🎉 GitHub secrets setup completed successfully!")
            print("💡 Note: GITHUB_PAT remains in .env for local development")
            return True
            
        except Exception as e:
            print(f"❌ Error during setup: {e}")
            return False

def main():
    """Main entry point"""
    try:
        manager = GitHubSecretsManager()
        success = manager.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
