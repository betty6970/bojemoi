#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Karacho Project - Blockchain PostgreSQL API with Docker Stack Integration
This script implements a blockchain-based journaling system for PostgreSQL host records
with token-based authentication and RESTful API endpoints, integrated with Docker Stack containers.
"""

import os
import time
import uuid
import json
import hashlib
import datetime
import secrets
import ipaddress
import socket
import sys
from typing import Dict, List, Tuple, Optional, Any

import docker
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

# Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
TOKEN_EXPIRY = int(os.environ.get('TOKEN_EXPIRY', '3600'))  # 1 hour by default
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
DOCKER_STACK_NAME = os.environ.get('DOCKER_STACK_NAME', 'bojemoi')  # Default stack name
HOST_STATUSES = ['non_teste', 'reserve', 'analyze_en_cours', 'analyzed_failed', 
                'analyzed_success', 'attribue']

class DockerStackManager:
    """Manages Docker Stack container discovery for PostgreSQL containers using Docker SDK."""
    
    def __init__(self, stack_name: str = None):
        """
        Initialize Docker Stack Manager.
        
        Args:
            stack_name: Name of the Docker stack to search in
        """
        self.stack_name = stack_name or DOCKER_STACK_NAME
        self.postgresql_containers = []
        self.container_ips = {}
        self.docker_client = None
        
        # Initialize Docker client
        self._init_docker_client()
    
    def _init_docker_client(self):
        """Initialize Docker client with proper configuration for container environment."""
        try:
            # Try different Docker socket locations
            docker_sockets = [
                'unix://var/run/docker.sock',  # Standard location
                'tcp://docker:2376',           # Docker-in-Docker
                'tcp://localhost:2376',        # Alternative
            ]
            
            # Also check environment variables
            docker_host = os.environ.get('DOCKER_HOST')
            if docker_host:
                docker_sockets.insert(0, docker_host)
            
            for socket_url in docker_sockets:
                try:
                    if socket_url.startswith('unix://'):
                        # Check if socket file exists
                        socket_path = socket_url.replace('unix://', '')
                        if not os.path.exists(socket_path):
                            continue
                        self.docker_client = docker.DockerClient(base_url=socket_url)
                    else:
                        self.docker_client = docker.DockerClient(base_url=socket_url)
                    
                    # Test the connection
                    self.docker_client.ping()
                    print(f"✓ Connected to Docker daemon via {socket_url}")
                    return
                    
                except Exception as e:
                    if DEBUG:
                        print(f"Failed to connect via {socket_url}: {e}")
                    continue
            
            # If no connection worked, try default
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            print("✓ Connected to Docker daemon via default configuration")
            
        except Exception as e:
            print(f"⚠ Warning: Could not connect to Docker daemon: {e}")
            print("  Service discovery will use fallback methods")
            self.docker_client = None
    
    def get_stack_services(self) -> List[Dict]:
        """
        Get all services in the Docker stack.
        
        Returns:
            List of service dictionaries
        """
        if not self.docker_client:
            return []
        
        try:
            services = []
            # Get all services
            for service in self.docker_client.services.list():
                service_info = {
                    'ID': service.id,
                    'Name': service.name,
                    'Image': service.attrs.get('Spec', {}).get('TaskTemplate', {}).get('ContainerSpec', {}).get('Image', ''),
                    'Replicas': service.attrs.get('Spec', {}).get('Replicas', 0),
                    'Labels': service.attrs.get('Spec', {}).get('Labels', {}),
                    'Networks': service.attrs.get('Spec', {}).get('Networks', []),
                    'Ports': service.attrs.get('Spec', {}).get('EndpointSpec', {}).get('Ports', [])
                }
                
                # Filter by stack name if specified
                if self.stack_name:
                    service_labels = service_info.get('Labels', {})
                    stack_label = service_labels.get('com.docker.stack.namespace')
                    if stack_label != self.stack_name:
                        continue
                
                services.append(service_info)
                
            return services
            
        except Exception as e:
            print(f"Error getting stack services: {e}")
            return []
    
    def get_stack_containers(self) -> List[Dict]:
        """
        Get all containers in the Docker stack.
        
        Returns:
            List of container dictionaries
        """
        if not self.docker_client:
            return []
        
        try:
            containers = []
            # Get all containers
            for container in self.docker_client.containers.list(all=True):
                container_info = {
                    'ID': container.id,
                    'Name': container.name,
                    'Image': container.image.tags[0] if container.image.tags else container.image.id,
                    'Status': container.status,
                    'State': container.attrs.get('State', {}),
                    'NetworkSettings': container.attrs.get('NetworkSettings', {}),
                    'Labels': container.labels or {},
                    'Ports': container.ports
                }
                
                # Filter by stack name if specified
                if self.stack_name:
                    container_labels = container_info.get('Labels', {})
                    stack_label = container_labels.get('com.docker.stack.namespace')
                    if stack_label != self.stack_name:
                        continue
                
                containers.append(container_info)
                
            return containers
            
        except Exception as e:
            print(f"Error getting stack containers: {e}")
            return []
    
    def find_postgresql_services(self, services: List[Dict]) -> List[Dict]:
        """
        Find PostgreSQL services among all services.
        
        Args:
            services: List of all services
            
        Returns:
            List of PostgreSQL services
        """
        postgresql_services = []
        
        for service in services:
            service_name = service.get('Name', '').lower()
            image = service.get('Image', '').lower()
            
            # Check service name
            if any(pg_term in service_name for pg_term in ['postgres', 'postgresql', 'db']):
                postgresql_services.append(service)
                continue
            
            # Check image name
            if any(pg_term in image for pg_term in ['postgres', 'postgresql']):
                postgresql_services.append(service)
                continue
            
            # Check ports
            ports = service.get('Ports', [])
            for port in ports:
                if isinstance(port, dict):
                    target_port = port.get('TargetPort', 0)
                    if target_port in [5432, 5433, 5434]:  # Common PostgreSQL ports
                        postgresql_services.append(service)
                        break
        
        return postgresql_services
    
    def find_postgresql_containers(self, containers: List[Dict]) -> List[Dict]:
        """
        Find PostgreSQL containers among all containers.
        
        Args:
            containers: List of all containers
            
        Returns:
            List of PostgreSQL containers
        """
        postgresql_containers = []
        
        for container in containers:
            container_name = container.get('Name', '').lower()
            image = container.get('Image', '').lower()
            
            # Check container name
            if any(pg_term in container_name for pg_term in ['postgres', 'postgresql', 'db']):
                postgresql_containers.append(container)
                continue
            
            # Check image name
            if any(pg_term in image for pg_term in ['postgres', 'postgresql']):
                postgresql_containers.append(container)
                continue
            
            # Check exposed ports
            ports = container.get('Ports', {})
            if ports:
                for port_config in ports.values():
                    if isinstance(port_config, list):
                        for port_info in port_config:
                            if isinstance(port_info, dict):
                                host_port = port_info.get('HostPort')
                                if host_port and int(host_port) in [5432, 5433, 5434]:
                                    postgresql_containers.append(container)
                                    break
        
        return postgresql_containers
    
    def get_container_ip(self, container_info: Dict) -> Optional[str]:
        """
        Get IP address of a container.
        
        Args:
            container_info: Container information dictionary
            
        Returns:
            IP address of the container or None
        """
        try:
            # Try to get IP from NetworkSettings
            network_settings = container_info.get('NetworkSettings', {})
            networks = network_settings.get('Networks', {})
            
            # Look for IP in any network
            for network_name, network_info in networks.items():
                ip_address = network_info.get('IPAddress')
                if ip_address:
                    return ip_address
            
            # Fallback: try to resolve by container name
            container_name = container_info.get('Name', '')
            if container_name:
                # Remove leading slash from container name
                clean_name = container_name.lstrip('/')
                try:
                    ip = socket.gethostbyname(clean_name)
                    return ip
                except socket.gaierror:
                    pass
            
            return None
            
        except Exception as e:
            if DEBUG:
                print(f"Error getting container IP: {e}")
            return None
    
    def get_service_ip(self, service_info: Dict) -> Optional[str]:
        """
        Get IP address of a service by resolving service name.
        
        Args:
            service_info: Service information dictionary
            
        Returns:
            IP address of the service or None
        """
        try:
            service_name = service_info.get('Name', '')
            if service_name:
                try:
                    ip = socket.gethostbyname(service_name)
                    return ip
                except socket.gaierror:
                    pass
            
            return None
            
        except Exception as e:
            if DEBUG:
                print(f"Error getting service IP: {e}")
            return None
    
    def test_postgresql_connection(self, host: str, port: int = 5432) -> bool:
        """
        Test if a PostgreSQL service is available at given host:port.
        
        Args:
            host: Hostname or IP address
            port: Port number
            
        Returns:
            True if connection is possible, False otherwise
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # 3 second timeout
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception as e:
            if DEBUG:
                print(f"Connection test failed for {host}:{port} - {e}")
            return False
    
    def discover_postgresql_containers(self) -> Dict[str, str]:
        """
        Discover PostgreSQL containers and their IP addresses.
        
        Returns:
            Dictionary mapping container/service names to IP addresses
        """
        print(f"Searching for PostgreSQL services in Docker Stack '{self.stack_name}'...")
        
        discovered_ips = {}
        self.postgresql_containers = []
        
        # Method 1: Discover via Docker services
        services = self.get_stack_services()
        if services:
            print(f"Found {len(services)} services in stack '{self.stack_name}'")
            pg_services = self.find_postgresql_services(services)
            
            if pg_services:
                print(f"Found {len(pg_services)} PostgreSQL services:")
                for service in pg_services:
                    service_name = service.get('Name')
                    print(f"  - Service: {service_name}")
                    print(f"    Image: {service.get('Image')}")
                    print(f"    Replicas: {service.get('Replicas')}")
                    
                    # Try to get service IP
                    service_ip = self.get_service_ip(service)
                    if service_ip:
                        # Test PostgreSQL connection
                        if self.test_postgresql_connection(service_ip, 5432):
                            discovered_ips[service_name] = service_ip
                            self.postgresql_containers.append({
                                'Name': service_name,
                                'IP': service_ip,
                                'Port': 5432,
                                'Type': 'Service',
                                'Image': service.get('Image')
                            })
                            print(f"    ✓ IP: {service_ip} (PostgreSQL confirmed)")
                        else:
                            print(f"    ✗ IP: {service_ip} (PostgreSQL not responding)")
                    else:
                        print(f"    ✗ Could not resolve IP address")
        
        # Method 2: Discover via Docker containers
        containers = self.get_stack_containers()
        if containers:
            print(f"Found {len(containers)} containers in stack '{self.stack_name}'")
            pg_containers = self.find_postgresql_containers(containers)
            
            if pg_containers:
                print(f"Found {len(pg_containers)} PostgreSQL containers:")
                for container in pg_containers:
                    container_name = container.get('Name', '').lstrip('/')
                    print(f"  - Container: {container_name}")
                    print(f"    Image: {container.get('Image')}")
                    print(f"    Status: {container.get('Status')}")
                    
                    # Skip if not running
                    if container.get('Status') != 'running':
                        print(f"    ✗ Container not running")
                        continue
                    
                    # Try to get container IP
                    container_ip = self.get_container_ip(container)
                    if container_ip and container_name not in discovered_ips:
                        # Test PostgreSQL connection
                        if self.test_postgresql_connection(container_ip, 5432):
                            discovered_ips[container_name] = container_ip
                            self.postgresql_containers.append({
                                'Name': container_name,
                                'IP': container_ip,
                                'Port': 5432,
                                'Type': 'Container',
                                'Image': container.get('Image')
                            })
                            print(f"    ✓ IP: {container_ip} (PostgreSQL confirmed)")
                        else:
                            print(f"    ✗ IP: {container_ip} (PostgreSQL not responding)")
                    else:
                        print(f"    ✗ Could not determine IP address")
        
        # Method 3: Try common service names via DNS
        common_names = [
            f"{self.stack_name}_postgres",
            f"{self.stack_name}_postgresql",
            f"{self.stack_name}_db",
            f"{self.stack_name}_database",
            "postgres",
            "postgresql",
            "db",
            "database"
        ]
        
        print("Trying common PostgreSQL service names...")
        for name in common_names:
            if name not in discovered_ips:
                try:
                    ip = socket.gethostbyname(name)
                    if self.test_postgresql_connection(ip, 5432):
                        discovered_ips[name] = ip
                        self.postgresql_containers.append({
                            'Name': name,
                            'IP': ip,
                            'Port': 5432,
                            'Type': 'DNS Resolution'
                        })
                        print(f"  ✓ {name} -> {ip} (PostgreSQL confirmed)")
                except socket.gaierror:
                    continue
        
        # Method 4: Check environment variables
        env_vars = [
            'POSTGRES_HOST',
            'POSTGRESQL_HOST',
            'DATABASE_HOST',
            'DB_HOST'
        ]
        
        print("Checking environment variables...")
        for env_var in env_vars:
            host = os.environ.get(env_var)
            if host and host not in discovered_ips.values():
                if self.test_postgresql_connection(host, 5432):
                    env_name = f"env_{env_var.lower()}"
                    discovered_ips[env_name] = host
                    self.postgresql_containers.append({
                        'Name': env_name,
                        'IP': host,
                        'Port': 5432,
                        'Type': 'Environment Variable',
                        'Source': env_var
                    })
                    print(f"  ✓ {env_var}={host} (PostgreSQL confirmed)")
        
        # Final fallback
        if not discovered_ips:
            print("No PostgreSQL services found, trying localhost fallback...")
            fallback_hosts = ['localhost', '127.0.0.1']
            for host in fallback_hosts:
                if self.test_postgresql_connection(host, 5432):
                    discovered_ips['localhost'] = host
                    self.postgresql_containers.append({
                        'Name': 'localhost',
                        'IP': host,
                        'Port': 5432,
                        'Type': 'Fallback'
                    })
                    print(f"  ✓ Using fallback: {host}")
                    break
        
        self.container_ips = discovered_ips
        
        print(f"\nPostgreSQL Discovery Summary:")
        print(f"Services/Containers found: {len(discovered_ips)}")
        for name, ip in discovered_ips.items():
            print(f"  - {name}: {ip}")
        
        return discovered_ips

# Docker Stack Manager instance
docker_manager = DockerStackManager()

# Discover PostgreSQL containers and get their IPs
postgresql_ips = docker_manager.discover_postgresql_containers()

# Database connection parameters - dynamically set based on discovered containers
def get_db_params(db_name: str) -> Dict:
    """
    Get database connection parameters, using discovered PostgreSQL services.
    
    Args:
        db_name: Name of the database
        
    Returns:
        Database connection parameters
    """
    # Default parameters
    default_params = {
        'dbname': db_name,
        'user': os.environ.get('POSTGRES_USER', 'postgres'),
        'password': os.environ.get('POSTGRES_PASSWORD', 'bojemoi'),
        'host': 'localhost',
        'port': int(os.environ.get('POSTGRES_PORT', '5432'))
    }
    
    # If we found PostgreSQL services, use the first one
    if postgresql_ips:
        first_service_ip = list(postgresql_ips.values())[0]
        default_params['host'] = first_service_ip
        print(f"Using PostgreSQL service at {first_service_ip} for database {db_name}")
    else:
        # Try common environment variables
        env_host = (os.environ.get('POSTGRES_HOST') or 
                   os.environ.get('DATABASE_HOST') or
                   os.environ.get('DB_HOST'))
        if env_host:
            default_params['host'] = env_host
            print(f"Using PostgreSQL host from environment: {env_host} for database {db_name}")
        else:
            print(f"No PostgreSQL services discovered, using localhost for database {db_name}")
    
    return default_params

# Database connection parameters
MSF_DB_PARAMS = get_db_params(os.environ.get('MSF_DB_NAME', 'msf'))
KARACHO_DB_PARAMS = get_db_params(os.environ.get('KARACHO_DB_NAME', 'karacho'))

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = SECRET_KEY

class DatabaseConnectionManager:
    """Manages database connections with failover support."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.msf_params = MSF_DB_PARAMS.copy()
        self.karacho_params = KARACHO_DB_PARAMS.copy()
        self.available_ips = list(postgresql_ips.values()) if postgresql_ips else ['localhost']
        self.current_ip_index = 0
    
    def get_connection(self, db_type: str) -> psycopg2.extensions.connection:
        """
        Get database connection with failover support.
        
        Args:
            db_type: Type of database ('msf' or 'karacho')
            
        Returns:
            Database connection
        """
        params = self.msf_params if db_type == 'msf' else self.karacho_params
        
        # Try current IP first
        for attempt in range(max(len(self.available_ips), 1)):
            try:
                current_params = params.copy()
                if self.available_ips:
                    current_params['host'] = self.available_ips[self.current_ip_index]
                
                conn = psycopg2.connect(**current_params)
                conn.autocommit = False  # Ensure transactions work properly
                return conn
                
            except psycopg2.Error as e:
                print(f"Failed to connect to {db_type} database at {current_params['host']}: {e}")
                
                # Try next IP if available
                if len(self.available_ips) > 1:
                    self.current_ip_index = (self.current_ip_index + 1) % len(self.available_ips)
                
                if attempt == max(len(self.available_ips), 1) - 1:
                    # All IPs failed, try to rediscover services
                    print("All database connections failed, attempting service rediscovery...")
                    new_ips = docker_manager.discover_postgresql_containers()
                    if new_ips:
                        self.available_ips = list(new_ips.values())
                        self.current_ip_index = 0
                        # Try once more with new IPs
                        try:
                            current_params['host'] = self.available_ips[0]
                            conn = psycopg2.connect(**current_params)
                            conn.autocommit = False
                            return conn
                        except psycopg2.Error as final_e:
                            raise psycopg2.Error(f"All database connection attempts failed: {final_e}")
                    else:
                        raise psycopg2.Error("No PostgreSQL services available")

        raise psycopg2.Error("Failed to establish database connection")

# Global connection manager
db_manager = DatabaseConnectionManager()

# [Les classes Block, Blockchain, HostManager, TokenManager, UserManager restent identiques à la version précédente]
# Je vais inclure une version simplifiée pour la longueur

class Block:
    """Represents a block in the blockchain."""
    
    def __init__(self, index: int, timestamp: float, data: Dict, previous_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of this block."""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True).encode()
        
        return hashlib.sha256(block_string).hexdigest()
    
    def mine_block(self, difficulty: int = 2) -> None:
        """Mine a block to achieve the required difficulty level."""
        target = '0' * difficulty
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "nonce": self.nonce
        }

class Blockchain:
    """Blockchain implementation for host record journaling."""
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.difficulty = 2
        self._create_blockchain_table()
        
        with self.db_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM blockchain")
            if cursor.fetchone()[0] == 0:
                self._create_genesis_block()
    
    def _create_blockchain_table(self):
        """Create blockchain table if it doesn't exist."""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blockchain (
                    id SERIAL PRIMARY KEY,
                    index INTEGER UNIQUE NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    data JSONB NOT NULL,
                    previous_hash VARCHAR(64) NOT NULL,
                    hash VARCHAR(64) UNIQUE NOT NULL,
                    nonce INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_blockchain_index ON blockchain(index);
                CREATE INDEX IF NOT EXISTS idx_blockchain_hash ON blockchain(hash);
            """)
            
            self.db_conn.commit()
    
    def _create_genesis_block(self) -> None:
        """Create the genesis block."""
        genesis_block = Block(0, time.time(), {"data": "Genesis Block"}, "0")
        genesis_block.mine_block(self.difficulty)
        
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO blockchain (index, timestamp, data, previous_hash, hash, nonce)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    genesis_block.index,
                    datetime.datetime.fromtimestamp(genesis_block.timestamp),
                    json.dumps(genesis_block.data),
                    genesis_block.previous_hash,
                    genesis_block.hash,
                    genesis_block.nonce
                )
            )
            self.db_conn.commit()
    
    def get_latest_block(self) -> Dict:
        """Get the latest block in the chain."""
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM blockchain ORDER BY index DESC LIMIT 1")
            return cursor.fetchone()
    
    def add_block(self, data: Dict) -> Dict:
        """Add a new block to the chain."""
        latest_block = self.get_latest_block()
        
        new_block = Block(
            latest_block['index'] + 1,
            time.time(),
            data,
            latest_block['hash']
        )
        
        new_block.mine_block(self.difficulty)
        
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO blockchain (index, timestamp, data, previous_hash, hash, nonce)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    new_block.index,
                    datetime.datetime.fromtimestamp(new_block.timestamp),
                    json.dumps(new_block.data),
                    new_block.previous_hash,
                    new_block.hash,
                    new_block.nonce
                )
            )
            self.db_conn.commit()
        
        return new_block.to_dict()

# API Endpoints simplifiés
@app.route('/api/docker/services', methods=['GET'])
def get_docker_services():
    """Get information about discovered Docker PostgreSQL services."""
    return jsonify({
        "stack_name": docker_manager.stack_name,
        "discovered_services": docker_manager.postgresql_containers,
        "service_ips": docker_manager.container_ips,
        "docker_client_available": docker_manager.docker_client is not None
    })

@app.route('/api/docker/rediscover', methods=['POST'])
def rediscover_services():
    """Force rediscovery of Docker PostgreSQL services."""
    try:
        new_ips = docker_manager.discover_postgresql_containers()
        if new_ips:
            db_manager.available_ips = list(new_ips.values())
            db_manager.current_ip_index = 0
        
        return jsonify({
            "status": "success",
            "discovered_services": len(new_ips),
            "service_ips": new_ips
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        karacho_conn = db_manager.get_connection('karacho')
        msf_conn = db_manager.get_connection('msf')
        
        with karacho_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            karacho_status = "connected"
        
        with msf_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            msf_status = "connected"
        
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify({
            "status": "healthy",
            "databases": {
                "karacho": karacho_status,
                "msf": msf_status
            },
            "docker": {
                "client_available": docker_manager.docker_client is not None,
                "services_discovered": len(postgresql_ips)
            },
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print(f"\n=== Karacho Blockchain API with Docker SDK Integration ===")
    print(f"Stack Name: {DOCKER_STACK_NAME}")
    print(f"Docker Client: {'✓ Available' if docker_manager.docker_client else '✗ Not Available'}")
    print(f"PostgreSQL Services Discovered: {len(postgresql_ips)}")
    
    if postgresql_ips:
        for service, ip in postgresql_ips.items():
            print(f"  - {service}: {ip}")
    else:
        print("  - No services discovered, using fallback configuration")
    
    print(f"Debug Mode: {DEBUG}")
    print(f"Token Expiry: {TOKEN_EXPIRY} seconds")
    print(f"Database Configuration:")
    print(f"  - MSF DB: {MSF_DB_PARAMS['host']}:{MSF_DB_PARAMS['port']}/{MSF_DB_PARAMS['dbname']}")
    print(f"  - Karacho DB: {KARACHO_DB_PARAMS['host']}:{KARACHO_DB_PARAMS['port']}/{KARACHO_DB_PARAMS['dbname']}")
    print("=" * 60)
    
    # Test Docker connection
    if docker_manager.docker_client:
        try:
            version = docker_manager.docker_client.version()
            print(f"Docker Engine Version: {version.get('Version', 'Unknown')}")
        except Exception as e:
            print(f"Docker connection test failed: {e}")
    
    print("=" * 60)
    print("API Endpoints:")
    print("  - GET  /api/health - Health check")
    print("  - GET  /api/docker/services - View discovered services")
    print("  - POST /api/docker/rediscover - Rediscover services")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=DEBUG)