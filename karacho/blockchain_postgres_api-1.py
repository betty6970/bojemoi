#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Karacho Project - Blockchain PostgreSQL API
This script implements a blockchain-based journaling system for PostgreSQL host records
with token-based authentication and RESTful API endpoints.
"""

import os
import time
import uuid
import json
import subprocess
import sys
import hashlib
import datetime
import secrets
import ipaddress
from typing import Dict, List, Tuple, Optional, Any

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
HOST_STATUSES = ['non_teste', 'reserve', 'analyze_en_cours', 'analyzed_failed', 
                'analyzed_success', 'attribue']

# Database connection parameters
MSF_DB_PARAMS = {
    'dbname': 'msf',
    'user': 'postgres',
    'password': 'bojemoi',
    'host': 'postgres',
    'port': '5432'
}

KARACHO_DB_PARAMS = {
    'dbname': 'karacho', 
    'user': 'postgres',
    'password': 'bojemoi',
    'host': 'postgres',
    'port': '5432'
}

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = SECRET_KEY



class Block:
    """Represents a block in the blockchain."""
    
    def __init__(self, index: int, timestamp: float, data: Dict, previous_hash: str):
        """
        Initialize a new block.
        
        Args:
            index: Block index in the chain
            timestamp: Block creation time
            data: Data to be stored in the block
            previous_hash: Hash of the previous block
        """
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
        """
        Mine a block to achieve the required difficulty level.
        
        Args:
            difficulty: Number of leading zeros required in hash
        """
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
        """
        Initialize the blockchain.
        
        Args:
            db_conn: Database connection
        """
        self.db_conn = db_conn
        self.difficulty = 2
        
        # Check if we need to create the genesis block
        with self.db_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM blockchain")
            if cursor.fetchone()[0] == 0:
                self._create_genesis_block()
    
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
        """
        Get the latest block in the chain.
        
        Returns:
            Dictionary representation of the latest block
        """
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT * FROM blockchain
                ORDER BY index DESC
                LIMIT 1
                """
            )
            return cursor.fetchone()
    
    def add_block(self, data: Dict) -> Dict:
        """
        Add a new block to the chain.
        
        Args:
            data: Data to store in the block
            
        Returns:
            The newly created block as a dictionary
        """
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
    
    def verify_chain(self) -> bool:
        """
        Verify the integrity of the blockchain.
        
        Returns:
            True if valid, False otherwise
        """
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM blockchain ORDER BY index ASC")
            blocks = cursor.fetchall()
            
            for i in range(1, len(blocks)):
                current_block = blocks[i]
                previous_block = blocks[i-1]
                
                # Check hash integrity
                block_data = {
                    "index": current_block['index'],
                    "timestamp": current_block['timestamp'].timestamp(),
                    "data": json.loads(current_block['data']),
                    "previous_hash": current_block['previous_hash'],
                    "nonce": current_block['nonce']
                }
                
                block_string = json.dumps(block_data, sort_keys=True).encode()
                calculated_hash = hashlib.sha256(block_string).hexdigest()
                
                if current_block['hash'] != calculated_hash:
                    return False
                
                # Check link to previous block
                if current_block['previous_hash'] != previous_block['hash']:
                    return False
                
        return True
    
    def get_blocks(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get blocks from the chain.
        
        Args:
            limit: Maximum number of blocks to retrieve
            offset: Number of blocks to skip
            
        Returns:
            List of blocks as dictionaries
        """
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT * FROM blockchain
                ORDER BY index DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            return cursor.fetchall()


class HostManager:
    """Manages host records and their lifecycle."""
    
    def __init__(self, msf_conn, karacho_conn, blockchain: Blockchain):
        """
        Initialize host manager.
        
        Args:
            msf_conn: Connection to MSF database
            karacho_conn: Connection to Karacho database
            blockchain: Blockchain instance
        """
        self.msf_conn = msf_conn
        self.karacho_conn = karacho_conn
        self.blockchain = blockchain
    
    def get_random_host_ip(self) -> str:
        """
        Get a random host IP from the MSF hosts table.
        
        Returns:
            Random IP address as string
        """
        with self.msf_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT address FROM hosts
                ORDER BY RANDOM()
                LIMIT 1
                """
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def reserve_host(self, host_id: int, user_id: int) -> Dict:
        """
        Reserve a host for analysis.
        
        Args:
            host_id: ID of the host to reserve
            user_id: ID of the user making the reservation
            
        Returns:
            Updated host record
        """
        # First check if host exists and is available
        with self.msf_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT * FROM hosts
                WHERE id = %s
                """,
                (host_id,)
            )
            host = cursor.fetchone()
            
            if not host:
                raise ValueError(f"Host with ID {host_id} not found")
        
        # Check current status in karacho
        with self.karacho_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT status FROM host_status
                WHERE host_id = %s
                """,
                (host_id,)
            )
            status_record = cursor.fetchone()
            
            if status_record and status_record[0] != 'non_teste':
                raise ValueError(f"Host with ID {host_id} is already reserved or in use")
        
        # Update status to 'reserve'
        with self.karacho_conn.cursor() as cursor:
            if status_record:
                cursor.execute(
                    """
                    UPDATE host_status
                    SET status = 'reserve', updated_at = NOW(), updated_by = %s
                    WHERE host_id = %s
                    RETURNING id, host_id, status, created_at, updated_at
                    """,
                    (user_id, host_id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO host_status (host_id, status, created_at, updated_at, created_by, updated_by)
                    VALUES (%s, 'reserve', NOW(), NOW(), %s, %s)
                    RETURNING id, host_id, status, created_at, updated_at
                    """,
                    (host_id, user_id, user_id)
                )
            
            result = cursor.fetchone()
            self.karacho_conn.commit()
        
        # Record the action in blockchain
        blockchain_data = {
            "action": "reserve_host",
            "host_id": host_id,
            "user_id": user_id,
            "status": "reserve",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.blockchain.add_block(blockchain_data)
        
        return {
            "host_id": host_id,
            "status": "reserve",
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    def update_host_status(self, host_id: int, status: str, user_id: int) -> Dict:
        """
        Update the status of a host.
        
        Args:
            host_id: ID of the host
            status: New status
            user_id: ID of the user updating the status
            
        Returns:
            Updated host record
        """
        if status not in HOST_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        
        # Check if host exists
        with self.msf_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM hosts
                WHERE id = %s
                """,
                (host_id,)
            )
            if not cursor.fetchone():
                raise ValueError(f"Host with ID {host_id} not found")
        
        # Update status
        with self.karacho_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, status FROM host_status
                WHERE host_id = %s
                """,
                (host_id,)
            )
            status_record = cursor.fetchone()
            
            if not status_record:
                cursor.execute(
                    """
                    INSERT INTO host_status (host_id, status, created_at, updated_at, created_by, updated_by)
                    VALUES (%s, %s, NOW(), NOW(), %s, %s)
                    RETURNING id
                    """,
                    (host_id, status, user_id, user_id)
                )
            else:
                # Check for valid status transition
                current_status = status_record[1]
                status_idx = HOST_STATUSES.index
                
                # Simplified validation logic - could be expanded with more complex rules
                if status_idx(status) < status_idx(current_status) and status != 'non_teste':
                    raise ValueError(f"Invalid status transition: {current_status} -> {status}")
                
                cursor.execute(
                    """
                    UPDATE host_status
                    SET status = %s, updated_at = NOW(), updated_by = %s
                    WHERE host_id = %s
                    """,
                    (status, user_id, host_id)
                )
            
            self.karacho_conn.commit()
        
        # Record the action in blockchain
        blockchain_data = {
            "action": "update_host_status",
            "host_id": host_id,
            "user_id": user_id,
            "old_status": status_record[1] if status_record else None,
            "new_status": status,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.blockchain.add_block(blockchain_data)
        
        return {
            "host_id": host_id,
            "status": status,
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    def get_host_status(self, host_id: int) -> Dict:
        """
        Get the current status of a host.
        
        Args:
            host_id: ID of the host
            
        Returns:
            Host status information
        """
        with self.karacho_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT host_id, status, created_at, updated_at
                FROM host_status
                WHERE host_id = %s
                """,
                (host_id,)
            )
            status = cursor.fetchone()
            
            if not status:
                # If no status in karacho, check if host exists in MSF
                with self.msf_conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id FROM hosts
                        WHERE id = %s
                        """,
                        (host_id,)
                    )
                    if not cursor.fetchone():
                        return {"error": f"Host with ID {host_id} not found"}
                
                return {
                    "host_id": host_id,
                    "status": "non_teste",  # Default status
                    "created_at": None,
                    "updated_at": None
                }
            
            return status


class TokenManager:
    """Manages authentication tokens."""
    
    def __init__(self, karacho_conn, msf_conn, blockchain: Blockchain):
        """
        Initialize token manager.
        
        Args:
            karacho_conn: Connection to Karacho database
            msf_conn: Connection to MSF database
            blockchain: Blockchain instance
        """
        self.karacho_conn = karacho_conn
        self.msf_conn = msf_conn
        self.blockchain = blockchain
    
    def generate_token(self, username: str, client_ip: str) -> Dict:
        """
        Generate a new authentication token.
        
        Args:
            username: Username for authentication
            client_ip: IP address of the client
            
        Returns:
            Token information including the associated random IP
        """
        # Get user
        with self.karacho_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, password_hash FROM users
                WHERE username = %s
                """,
                (username,)
            )
            user = cursor.fetchone()
            
            if not user:
                raise ValueError(f"User {username} not found")
            
            user_id = user[0]
        
        # Get a random IP address
        with self.msf_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, address FROM hosts
                ORDER BY RANDOM()
                LIMIT 1
                """
            )
            host = cursor.fetchone()
            
            if not host:
                raise ValueError("No host addresses available")
            
            random_ip = str(host[1])
            host_id = host[0]
        
        # Generate token
        expiry = datetime.datetime.now() + datetime.timedelta(seconds=TOKEN_EXPIRY)
        token_payload = {
            "sub": user_id,
            "username": username,
            "client_ip": client_ip,
            "random_ip": random_ip,
            "host_id": host_id,
            "exp": expiry.timestamp()
        }
        
        token = jwt.encode(token_payload, SECRET_KEY, algorithm="HS256")
        
        # Store token in database
        with self.karacho_conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tokens (user_id, token, client_ip, random_ip, host_id, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, token, client_ip, random_ip, host_id, expiry)
            )
            token_id = cursor.fetchone()[0]
            self.karacho_conn.commit()
        
        # Record in blockchain
        blockchain_data = {
            "action": "generate_token",
            "token_id": token_id,
            "user_id": user_id,
            "client_ip": client_ip,
            "random_ip": random_ip,
            "host_id": host_id,
            "expires_at": expiry.isoformat(),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.blockchain.add_block(blockchain_data)
        
        return {
            "token": token,
            "expires_at": expiry.isoformat(),
            "random_ip": random_ip
        }
    
    def validate_token(self, token: str, client_ip: str) -> Dict:
        """
        Validate an authentication token.
        
        Args:
            token: The token to validate
            client_ip: IP address of the client
            
        Returns:
            Token payload if valid
        """
        try:
            # First decode token to check expiry
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            
            # Check if client IP matches
            if payload["client_ip"] != client_ip:
                raise ValueError("Client IP mismatch")
            
            # Check if token is in database and not revoked
            with self.karacho_conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, revoked FROM tokens
                    WHERE token = %s
                    """,
                    (token,)
                )
                token_record = cursor.fetchone()
                
                if not token_record:
                    raise ValueError("Token not found in database")
                
                if token_record[1]:
                    raise ValueError("Token has been revoked")
            
            return payload
        
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    def revoke_token(self, token: str, user_id: int) -> Dict:
        """
        Revoke an authentication token.
        
        Args:
            token: Token to revoke
            user_id: ID of the user revoking the token
            
        Returns:
            Revocation status
        """
        with self.karacho_conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE tokens
                SET revoked = TRUE, revoked_at = NOW(), revoked_by = %s
                WHERE token = %s
                RETURNING id
                """,
                (user_id, token)
            )
            result = cursor.fetchone()
            
            if not result:
                raise ValueError("Token not found")
            
            token_id = result[0]
            self.karacho_conn.commit()
        
        # Record in blockchain
        blockchain_data = {
            "action": "revoke_token",
            "token_id": token_id,
            "revoked_by": user_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.blockchain.add_block(blockchain_data)
        
        return {"status": "revoked", "token_id": token_id}


class UserManager:
    """Manages user accounts."""
    
    def __init__(self, karacho_conn, blockchain: Blockchain):
        """
        Initialize user manager.
        
        Args:
            karacho_conn: Connection to Karacho database
            blockchain: Blockchain instance
        """
        self.karacho_conn = karacho_conn
        self.blockchain = blockchain
    
    def create_user(self, username: str, password: str, creator_id: Optional[int] = None) -> Dict:
        """
        Create a new user.
        
        Args:
            username: Username for the new user
            password: Password for the new user
            creator_id: ID of the user creating this account
            
        Returns:
            New user information
        """
        password_hash = generate_password_hash(password)
        
        with self.karacho_conn.cursor() as cursor:
            # Check if username already exists
            cursor.execute(
                """
                SELECT id FROM users
                WHERE username = %s
                """,
                (username,)
            )
            
            if cursor.fetchone():
                raise ValueError(f"Username {username} already exists")
            
            # Create new user
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                RETURNING id
                """,
                (username, password_hash)
            )
            
            user_id = cursor.fetchone()[0]
            self.karacho_conn.commit()
        
        # Record in blockchain (omit password)
        blockchain_data = {
            "action": "create_user",
            "user_id": user_id,
            "username": username,
            "created_by": creator_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        self.blockchain.add_block(blockchain_data)
        
        return {
            "id": user_id,
            "username": username,
            "created_at": datetime.datetime.now().isoformat()
        }
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """
        Authenticate a user.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            
        Returns:
            User information if authentication succeeds
        """
        with self.karacho_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT id, username, password_hash
                FROM users
                WHERE username = %s
                """,
                (username,)
            )
            
            user = cursor.fetchone()
            
            if not user or not check_password_hash(user["password_hash"], password):
                raise ValueError("Invalid username or password")
            
            # Remove password hash before returning
            del user["password_hash"]
            
            return user


# API endpoints

@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint to get an authentication token."""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Missing username or password"}), 400
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        user_manager = UserManager(karacho_conn, blockchain)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        
        # Authenticate user
        user = user_manager.authenticate_user(data['username'], data['password'])
        
        # Generate token
        client_ip = request.remote_addr
        if 'client_ip' in data:  # Allow override for testing
            client_ip = data['client_ip']
            
        token_data = token_manager.generate_token(data['username'], client_ip)
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify({
            "user": user,
            "token": token_data["token"],
            "expires_at": token_data["expires_at"],
            "random_ip": token_data["random_ip"]
        })
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred during login"}), 500


@app.route('/api/hosts/random', methods=['GET'])
def get_random_host():
    """Get a random host IP from the MSF database."""
    # Verify token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    token = token.split(' ')[1]
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        host_manager = HostManager(msf_conn, karacho_conn, blockchain)
        
        # Validate token
        token_data = token_manager.validate_token(token, request.remote_addr)
        
        # Get random host IP
        random_ip = host_manager.get_random_host_ip()
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify({"ip": random_ip})
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred retrieving a random host"}), 500


@app.route('/api/hosts/<int:host_id>/reserve', methods=['POST'])
def reserve_host(host_id):
    """Reserve a host for analysis."""
    # Verify token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    token = token.split(' ')[1]
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        host_manager = HostManager(msf_conn, karacho_conn, blockchain)
        
        # Validate token
        token_data = token_manager.validate_token(token, request.remote_addr)
        user_id = token_data["sub"]
        
        # Reserve host
        result = host_manager.reserve_host(host_id, user_id)
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred reserving the host"}), 500


@app.route('/api/hosts/<int:host_id>/status', methods=['PUT'])
def update_host_status(host_id):
    """Update the status of a host."""
    # Verify token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    token = token.split(' ')[1]
    
    # Get status from request
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({"error": "Missing status parameter"}), 400
    
    status = data['status']
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        host_manager = HostManager(msf_conn, karacho_conn, blockchain)
        
        # Validate token
        token_data = token_manager.validate_token(token, request.remote_addr)
        user_id = token_data["sub"]
        
        # Update host status
        result = host_manager.update_host_status(host_id, status, user_id)
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred updating the host status"}), 500


@app.route('/api/hosts/<int:host_id>/status', methods=['GET'])
def get_host_status(host_id):
    """Get the current status of a host."""
    # Verify token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    token = token.split(' ')[1]
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        host_manager = HostManager(msf_conn, karacho_conn, blockchain)
        
        # Validate token
        token_data = token_manager.validate_token(token, request.remote_addr)
        
        # Get host status
        result = host_manager.get_host_status(host_id)
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred retrieving the host status"}), 500


@app.route('/api/blockchain/blocks', methods=['GET'])
def get_blockchain_blocks():
    """Get blocks from the blockchain."""
    # Verify token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    token = token.split(' ')[1]
    
    # Parse query parameters
    limit = request.args.get('limit', default=100, type=int)
    offset = request.args.get('offset', default=0, type=int)
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        
        # Validate token
        token_data = token_manager.validate_token(token, request.remote_addr)
        
        # Get blocks
        blocks = blockchain.get_blocks(limit, offset)
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify(blocks)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred retrieving blockchain blocks"}), 500


@app.route('/api/blockchain/verify', methods=['GET'])
def verify_blockchain():
    """Verify the integrity of the blockchain."""
    # Verify token
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    token = token.split(' ')[1]
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        
        # Validate token
        token_data = token_manager.validate_token(token, request.remote_addr)
        
        # Verify blockchain
        is_valid = blockchain.verify_chain()
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify({"valid": is_valid})
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred verifying the blockchain"}), 500


@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user."""
    # Verify token for admin
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    token = token.split(' ')[1]
    
    # Get user data from request
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Missing username or password"}), 400
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        user_manager = UserManager(karacho_conn, blockchain)
        
        # Validate token
        token_data = token_manager.validate_token(token, request.remote_addr)
        admin_id = token_data["sub"]
        
        # Create user
        result = user_manager.create_user(data['username'], data['password'], admin_id)
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred creating the user"}), 500


@app.route('/api/tokens/revoke', methods=['POST'])
def revoke_token():
    """Revoke an authentication token."""
    # Verify current token
    current_token = request.headers.get('Authorization')
    if not current_token or not current_token.startswith('Bearer '):
        return jsonify({"error": "Missing or invalid authorization token"}), 401
    
    current_token = current_token.split(' ')[1]
    
    # Get token to revoke from request
    data = request.get_json()
    if not data or 'token' not in data:
        return jsonify({"error": "Missing token parameter"}), 400
    
    token_to_revoke = data['token']
    
    try:
        # Get database connections
        karacho_conn = psycopg2.connect(**KARACHO_DB_PARAMS)
        msf_conn = psycopg2.connect(**MSF_DB_PARAMS)
        
        # Initialize managers
        blockchain = Blockchain(karacho_conn)
        token_manager = TokenManager(karacho_conn, msf_conn, blockchain)
        
        # Validate current token
        token_data = token_manager.validate_token(current_token, request.remote_addr)
        user_id = token_data["sub"]
        
        # Revoke token
        result = token_manager.revoke_token(token_to_revoke, user_id)
        
        # Close connections
        karacho_conn.close()
        msf_conn.close()
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        if DEBUG:
            return jsonify({"error": str(e)}), 500
        return jsonify({"error": "An error occurred revoking the token"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
        