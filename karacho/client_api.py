#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Karacho Project - Client API
This script provides a client library for interacting with the Karacho blockchain API.
"""

import json
import time
import requests
from typing import Dict, List, Optional, Union, Any

class KarachoClient:
    """Client for the Karacho blockchain API."""
    
    def __init__(self, base_url: str, verify_ssl: bool = True):
        """
        Initialize the Karacho client.
        
        Args:
            base_url: Base URL of the Karacho API
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.token = None
        self.token_expiry = None
        self.random_ip = None
    
    def login(self, username: str, password: str, client_ip: Optional[str] = None) -> Dict:
        """
        Log in to the Karacho API and get an authentication token.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            client_ip: Optional client IP override
            
        Returns:
            Login response data
        """
        url = f"{self.base_url}/api/login"
        data = {
            "username": username,
            "password": password
        }
        
        if client_ip:
            data["client_ip"] = client_ip
        
        response = requests.post(url, json=data, verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Login failed: {response.json().get('error', 'Unknown error')}")
        
        response_data = response.json()
        self.token = response_data["token"]
        self.token_expiry = response_data["expires_at"]
        self.random_ip = response_data["random_ip"]
        
        return response_data
    
    def _get_headers(self) -> Dict:
        """
        Get headers for API requests including authentication token.
        
        Returns:
            Headers dictionary
        """
        if not self.token:
            raise ValueError("Not authenticated. Call login() first")
        
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_random_host(self) -> str:
        """
        Get a random host IP from the MSF database.
        
        Returns:
            Random IP address
        """
        url = f"{self.base_url}/api/hosts/random"
        
        response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get random host: {response.json().get('error', 'Unknown error')}")
        
        return response.json()["ip"]
    
    def reserve_host(self, host_id: int) -> Dict:
        """
        Reserve a host for analysis.
        
        Args:
            host_id: ID of the host to reserve
            
        Returns:
            Reservation status
        """
        url = f"{self.base_url}/api/hosts/{host_id}/reserve"
        
        response = requests.post(url, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to reserve host: {response.json().get('error', 'Unknown error')}")
        
        return response.json()
    
    def update_host_status(self, host_id: int, status: str) -> Dict:
        """
        Update the status of a host.
        
        Args:
            host_id: ID of the host
            status: New status
            
        Returns:
            Update status
        """
        url = f"{self.base_url}/api/hosts/{host_id}/status"
        data = {"status": status}
        
        response = requests.put(url, json=data, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to update host status: {response.json().get('error', 'Unknown error')}")
        
        return response.json()
    
    def get_host_status(self, host_id: int) -> Dict:
        """
        Get the current status of a host.
        
        Args:
            host_id: ID of the host
            
        Returns:
            Host status information
        """
        url = f"{self.base_url}/api/hosts/{host_id}/status"
        
        response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get host status: {response.json().get('error', 'Unknown error')}")
        
        return response.json()
    
    def get_blockchain_blocks(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get blocks from the blockchain.
        
        Args:
            limit: Maximum number of blocks to retrieve
            offset: Number of blocks to skip
            
        Returns:
            List of blocks
        """
        url = f"{self.base_url}/api/blockchain/blocks"
        params = {"limit": limit, "offset": offset}
        
        response = requests.get(url, params=params, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to get blockchain blocks: {response.json().get('error', 'Unknown error')}")
        
        return response.json()
    
    def verify_blockchain(self) -> bool:
        """
        Verify the integrity of the blockchain.
        
        Returns:
            True if blockchain is valid, False otherwise
        """
        url = f"{self.base_url}/api/blockchain/verify"
        
        response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to verify blockchain: {response.json().get('error', 'Unknown error')}")
        
        return response.json()["valid"]
    
    def create_user(self, username: str, password: str) -> Dict:
        """
        Create a new user.
        
        Args:
            username: Username for the new user
            password: Password for the new user
            
        Returns:
            New user information
        """
        url = f"{self.base_url}/api/users"
        data = {"username": username, "password": password}
        
        response = requests.post(url, json=data, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to create user: {response.json().get('error', 'Unknown error')}")
        
        return response.json()
    
    def revoke_token(self, token: str) -> Dict:
        """
        Revoke an authentication token.
        
        Args:
            token: Token to revoke
            
        Returns:
            Revocation status
        """
        url = f"{self.base_url}/api/tokens/revoke"
        data = {"token": token}
        
        response = requests.post(url, json=data, headers=self._get_headers(), verify=self.verify_ssl)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to revoke token: {response.json().get('error', 'Unknown error')}")
        
        return response.json()


# Example usage
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Karacho Client API Example')
    parser.add_argument('--url', type=str, default='http://localhost:5000', help='Karacho API URL')
    parser.add_argument('--username', type=str, default='admin', help='Username')
    parser.add_argument('--password', type=str, required=True, help='Password')
    parser.add_argument('--action', type=str, choices=['random_host', 'reserve', 'status_update', 'get_status',
                                                    'get_blocks', 'verify', 'create_user', 'revoke'],
                        required=True, help='Action to perform')
    parser.add_argument('--host-id', type=int, help='Host ID for host operations')
    parser.add_argument('--status', type=str, help='Status for update operations')
    parser.add_argument('--limit', type=int, default=10, help='Limit for block retrieval')
    parser.add_argument('--offset', type=int, default=0, help='Offset for block retrieval')
    parser.add_argument('--new-username', type=str, help='Username for new user')
    parser.add_argument('--new-password', type=str, help='Password for new user')
    parser.add_argument('--token', type=str, help='Token to revoke')
    
    args = parser.parse_args()
    
    client = KarachoClient(args.url)
    
    try:
        # Login
        login_result = client.login(args.username, args.password)
        print(f"Logged in successfully as {args.username}")
        print(f"Assigned random IP: {client.random_ip}")
        print(f"Token expires at: {client.token_expiry}")
        
        # Perform the requested action
        if args.action == 'random_host':
            random_ip = client.get_random_host()
            print(f"Random host IP: {random_ip}")
            
        elif args.action == 'reserve':
            if not args.host_id:
                parser.error("--host-id is required for reserve action")
            
            result = client.reserve_host(args.host_id)
            print(f"Reserved host {args.host_id}")
            print(json.dumps(result, indent=2))
            
        elif args.action == 'status_update':
            if not args.host_id or not args.status:
                parser.error("--host-id and --status are required for status_update action")
            
            result = client.update_host_status(args.host_id, args.status)
            print(f"Updated host {args.host_id} status to {args.status}")
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get_status':
            if not args.host_id:
                parser.error("--host-id is required for get_status action")
            
            result = client.get_host_status(args.host_id)
            print(f"Status for host {args.host_id}:")
            print(json.dumps(result, indent=2))
            
        elif args.action == 'get_blocks':
            blocks = client.get_blockchain_blocks(args.limit, args.offset)
            print(f"Retrieved {len(blocks)} blocks:")
            print(json.dumps(blocks, indent=2))
            
        elif args.action == 'verify':
            is_valid = client.verify_blockchain()
            print(f"Blockchain is {'valid' if is_valid else 'invalid'}")
            
        elif args.action == 'create_user':
            if not args.new_username or not args.new_password:
                parser.error("--new-username and --new-password are required for create_user action")
            
            result = client.create_user(args.new_username, args.new_password)
            print(f"Created new user {args.new_username}")
            print(json.dumps(result, indent=2))
            
        elif args.action == 'revoke':
            if not args.token:
                parser.error("--token is required for revoke action")
            
            result = client.revoke_token(args.token)
            print(f"Revoked token")
            print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")
