import requests
import json
import os
import sys
from packaging import version
from pathlib import Path
from tkinter import messagebox
import winreg
import subprocess
from utils import get_logger

logger = get_logger()

class Updater:
    def __init__(self, current_version, repo_owner, repo_name):
        self.current_version = current_version
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        self.update_dir = Path(os.getenv('LOCALAPPDATA')) / "Matchio" / "Updates"
        self.update_dir.mkdir(parents=True, exist_ok=True)

    def check_for_updates(self):
        """Check if a new version is available"""
        try:
            response = requests.get(self.github_api_url, timeout=5)
            response.raise_for_status()
            
            latest_release = response.json()
            latest_version = latest_release['tag_name'].lstrip('v')
            
            if version.parse(latest_version) > version.parse(self.current_version):
                return {
                    'version': latest_version,
                    'url': self._get_windows_asset_url(latest_release['assets']),
                    'notes': latest_release['body']
                }
            return None
            
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None

    def _get_windows_asset_url(self, assets):
        """Get download URL for Windows executable"""
        for asset in assets:
            if asset['name'].endswith('.exe'):
                return asset['browser_download_url']
        return None

    def download_update(self, url, version):
        """Download the update file"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            update_file = self.update_dir / f"Matchio-{version}.exe"
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return update_file
            
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            return None

    def install_update(self, update_file):
        """Install the update"""
        try:
            # Run the new installer with admin privileges
            subprocess.run(['runas', '/user:Administrator', str(update_file)], 
                         check=True, capture_output=True)
            return True
            
        except Exception as e:
            logger.error(f"Error installing update: {e}")
            return False