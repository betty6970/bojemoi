#!/usr/bin/env python3
"""
Breachforum Onion Discovery Service
Multi-source scraping + validation + PostgreSQL logging
Designed for Bojemoi Lab CTI pipeline
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Set, Dict, Optional
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from abc import ABC, abstractmethod
import asyncio
import aiohttp
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

# ============== CONFIG ==============
POSTGRES_HOST = os.getenv("DB_HOST", "localhost")
POSTGRES_DB = os.getenv("DB_NAME", "bojemoi_cti")
POSTGRES_USER = os.getenv("DB_USER", "cti_user")
POSTGRES_PASS = os.getenv("DB_PASS", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Proxy config for scraping (optional Tor/VPN)
PROXY_URL = os.getenv("PROXY_URL")  # e.g., socks5://127.0.0.1:9050
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"

# Onion regex pattern
ONION_PATTERN = re.compile(r'([a-z2-7]{16,56}\.onion)', re.IGNORECASE)
BREACHFORUM_KEYWORDS = ['breachforum', 'breach', 'forum']

# ============== LOGGING ==============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== DATA MODELS ==============
@dataclass
class OnionAddress:
    address: str
    source: str
    confidence: float  # 0.0-1.0
    discovered_at: datetime
    last_verified: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict = None

    def __hash__(self):
        return hash(self.address)

    def __eq__(self, other):
        if isinstance(other, OnionAddress):
            return self.address == other.address
        return False

# ============== DATABASE ==============
class PostgresCtiBridge:
    """PostgreSQL logging for discovered onions"""
    
    def __init__(self):
        self.conn = None
        self.connect()
        self.init_tables()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=POSTGRES_HOST,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASS,
                connect_timeout=5
            )
            logger.info("✓ PostgreSQL connected")
        except psycopg2.Error as e:
            logger.error(f"✗ PostgreSQL connection failed: {e}")
            self.conn = None
    
    def init_tables(self):
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS onion_discoveries (
                        id SERIAL PRIMARY KEY,
                        address VARCHAR(100) UNIQUE NOT NULL,
                        source VARCHAR(50),
                        confidence FLOAT,
                        discovered_at TIMESTAMP,
                        last_verified TIMESTAMP,
                        is_active BOOLEAN,
                        metadata JSONB,
                        verified_hash VARCHAR(64)
                    );
                    CREATE INDEX IF NOT EXISTS idx_onion_address ON onion_discoveries(address);
                    CREATE INDEX IF NOT EXISTS idx_onion_source ON onion_discoveries(source);
                """)
                self.conn.commit()
                logger.info("✓ Tables initialized")
        except psycopg2.Error as e:
            logger.error(f"✗ Table init failed: {e}")
    
    def log_discovery(self, onion: OnionAddress):
        if not self.conn:
            return
        try:
            addr_hash = hashlib.sha256(onion.address.encode()).hexdigest()
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO onion_discoveries 
                    (address, source, confidence, discovered_at, last_verified, is_active, metadata, verified_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (address) DO UPDATE
                    SET last_verified = EXCLUDED.last_verified,
                        confidence = GREATEST(onion_discoveries.confidence, EXCLUDED.confidence)
                """, (
                    onion.address,
                    onion.source,
                    onion.confidence,
                    onion.discovered_at,
                    onion.last_verified,
                    onion.is_active,
                    json.dumps(onion.metadata or {}),
                    addr_hash
                ))
                self.conn.commit()
                logger.info(f"✓ Logged {onion.address} from {onion.source}")
        except psycopg2.Error as e:
            logger.error(f"✗ Log failed: {e}")
    
    def get_latest(self) -> Optional[str]:
        """Get most recent verified onion"""
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT address FROM onion_discoveries
                    WHERE is_active = TRUE
                    ORDER BY last_verified DESC NULLS LAST
                    LIMIT 1
                """)
                result = cur.fetchone()
                return result['address'] if result else None
        except psycopg2.Error as e:
            logger.error(f"✗ Query failed: {e}")
            return None

# ============== DISCOVERY SOURCES ==============
class DiscoverySource(ABC):
    """Abstract base for discovery sources"""
    
    def __init__(self):
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": USER_AGENT})
        
        if PROXY_URL:
            session.proxies = {"http": PROXY_URL, "https": PROXY_URL}
        
        return session
    
    @abstractmethod
    def discover(self) -> Set[OnionAddress]:
        pass

class AhmiaSource(DiscoverySource):
    """Ahmia onion search engine"""
    
    def discover(self) -> Set[OnionAddress]:
        results = set()
        try:
            # Ahmia returns HTML search results — extract onion addresses via regex
            url = "https://ahmia.fi/search/?q=breachforum"
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 200:
                matches = ONION_PATTERN.findall(resp.text)
                for addr in matches:
                    results.add(OnionAddress(
                        address=addr,
                        source="ahmia",
                        confidence=0.7,
                        discovered_at=datetime.now(),
                        metadata={"search_query": "breachforum"}
                    ))
                logger.info(f"✓ Ahmia: found {len(results)} candidates")
            else:
                logger.warning(f"✗ Ahmia: HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"✗ Ahmia source failed: {e}")
        return results

class RedditSource(DiscoverySource):
    """Reddit r/darknet & r/Tor discussions"""
    
    def discover(self) -> Set[OnionAddress]:
        results = set()
        subreddits = ['darknet', 'Tor']
        
        for subreddit in subreddits:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/search.json?q=breachforum&restrict_sr=on&sort=new&t=month&limit=100"
                resp = self.session.get(url, timeout=20, headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json"
                })

                if resp.status_code == 429:
                    logger.warning(f"✗ Reddit r/{subreddit}: rate limited (429), skipping")
                    continue
                if resp.status_code == 200:
                    matches = ONION_PATTERN.findall(resp.text)
                    for match in matches:
                        results.add(OnionAddress(
                            address=match,
                            source=f"reddit_r{subreddit}",
                            confidence=0.6,
                            discovered_at=datetime.now(),
                            metadata={"subreddit": subreddit}
                        ))
                    logger.info(f"✓ Reddit r/{subreddit}: found {len(matches)} candidates")
                else:
                    logger.warning(f"✗ Reddit r/{subreddit}: HTTP {resp.status_code}")
            except Exception as e:
                logger.error(f"✗ Reddit r/{subreddit} failed: {e}")
        
        return results

class TorProjectListSource(DiscoverySource):
    """Directory listings from known .onion hubs"""
    
    def discover(self) -> Set[OnionAddress]:
        results = set()
        # These are clearnet mirrors/archives that document .onion addresses
        sources = [
            "https://thehiddenwiki.com/index.php/Breachforum",
            "https://www.deepweblinks.net/",
        ]
        
        for url in sources:
            try:
                resp = self.session.get(url, timeout=30)
                if resp.status_code == 200:
                    matches = ONION_PATTERN.findall(resp.text)
                    count = 0
                    for match in matches:
                        if any(kw in resp.text.lower() for kw in BREACHFORUM_KEYWORDS):
                            results.add(OnionAddress(
                                address=match,
                                source="tor_directory",
                                confidence=0.65,
                                discovered_at=datetime.now(),
                                metadata={"source_url": url}
                            ))
                            count += 1
                    logger.info(f"✓ Directory {url}: found {count} candidates")
                else:
                    logger.warning(f"✗ Directory {url}: HTTP {resp.status_code}")
            except Exception as e:
                logger.error(f"✗ Directory {url} failed: {e}")
        
        return results

class TelegramBotApiSource(DiscoverySource):
    """Monitor a Telegram channel via Bot API getUpdates.
    Requires the bot to be added as admin to the channel.
    Stores last update_id in DB to avoid reprocessing.
    """

    OFFSET_FILE = "/tmp/tg_offset.txt"

    def __init__(self, channel: str = "BreachForumHub"):
        super().__init__()
        self.channel = channel.lower()
        self.token = TELEGRAM_BOT_TOKEN

    def _get_offset(self) -> int:
        try:
            with open(self.OFFSET_FILE) as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def _save_offset(self, offset: int):
        try:
            with open(self.OFFSET_FILE, "w") as f:
                f.write(str(offset))
        except Exception:
            pass

    def discover(self) -> Set[OnionAddress]:
        results = set()
        if not self.token:
            logger.warning("✗ Telegram Bot API: no token configured")
            return results

        offset = self._get_offset()
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {
            "offset": offset,
            "limit": 100,
            "allowed_updates": ["channel_post"],
            "timeout": 5
        }

        try:
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"✗ Telegram Bot API: HTTP {resp.status_code}")
                return results

            data = resp.json()
            if not data.get("ok"):
                logger.warning(f"✗ Telegram Bot API error: {data.get('description')}")
                return results

            updates = data.get("result", [])
            max_update_id = offset

            for update in updates:
                update_id = update.get("update_id", 0)
                if update_id >= max_update_id:
                    max_update_id = update_id + 1

                post = update.get("channel_post", {})
                chat = post.get("chat", {})
                username = (chat.get("username") or "").lower()

                if username != self.channel:
                    continue

                text = post.get("text", "") + " " + post.get("caption", "")
                matches = ONION_PATTERN.findall(text)
                for addr in matches:
                    results.add(OnionAddress(
                        address=addr,
                        source=f"telegram_bot_{self.channel}",
                        confidence=0.9,
                        discovered_at=datetime.now(),
                        metadata={
                            "channel": self.channel,
                            "message_id": post.get("message_id"),
                            "date": post.get("date")
                        }
                    ))

            if max_update_id > offset:
                self._save_offset(max_update_id)

            logger.info(f"✓ Telegram @{self.channel}: {len(updates)} updates, {len(results)} onions found")

        except Exception as e:
            logger.error(f"✗ Telegram Bot API failed: {e}")

        return results


class CtiReportSource(DiscoverySource):
    """CTI feeds and threat intelligence summaries"""
    
    def discover(self) -> Set[OnionAddress]:
        results = set()
        # PublicCTI, Shadowserver, etc. often publish onion addresses
        # This is a template - add your own feed subscriptions
        try:
            # Example: querying a local CTI aggregator
            # or public Shodan/Censys APIs if configured
            logger.info("✓ CTI reports: placeholder (add proprietary feeds)")
        except Exception as e:
            logger.error(f"✗ CTI report source failed: {e}")
        return results

# ============== VALIDATION ==============
class OnionValidator:
    """Validate discovered onion addresses"""
    
    @staticmethod
    def validate_format(address: str) -> bool:
        """Check v2/v3 onion format"""
        return bool(ONION_PATTERN.match(address))
    
    @staticmethod
    async def test_connectivity(address: str, timeout: int = 10) -> bool:
        """Test if onion is reachable (requires Tor SOCKS proxy)"""
        if not PROXY_URL or "socks" not in PROXY_URL:
            logger.debug(f"Skipping connectivity test (no Tor proxy configured)")
            return True
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{address}",
                    timeout=aiohttp.ClientTimeout(total=timeout),
                    proxy=PROXY_URL,
                    ssl=False
                ) as resp:
                    return resp.status < 500
        except Exception as e:
            logger.debug(f"Connectivity test failed for {address}: {e}")
            return False

# ============== TELEGRAM ALERTING ==============
def send_telegram_alert(message: str):
    """Alert Telegram channel on new discovery"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"🔗 **CTI Alert**\n{message}",
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
        logger.info(f"✓ Telegram alert sent")
    except Exception as e:
        logger.error(f"✗ Telegram alert failed: {e}")

# ============== ORCHESTRATION ==============
class BreachforumDiscoveryService:
    """Main orchestration service"""
    
    def __init__(self):
        self.db = PostgresCtiBridge()
        self.sources = [
            AhmiaSource(),
            RedditSource(),
            TorProjectListSource(),
            TelegramBotApiSource("BreachForumHub"),
            CtiReportSource()
        ]
        self.validator = OnionValidator()
        self.discovered_addresses: Set[OnionAddress] = set()
    
    async def discover_all(self) -> Set[str]:
        """Run all discovery sources and validate"""
        logger.info("Starting Breachforum discovery sweep...")
        
        for source in self.sources:
            try:
                addresses = source.discover()
                self.discovered_addresses.update(addresses)
            except Exception as e:
                logger.error(f"Source failed: {e}")
        
        # Validate and deduplicate
        validated = set()
        for onion in self.discovered_addresses:
            if self.validator.validate_format(onion.address):
                validated.add(onion.address)
                self.db.log_discovery(onion)
                logger.info(f"✓ Validated & logged: {onion.address} (source: {onion.source})")
        
        logger.info(f"Discovery complete: {len(validated)} unique validated addresses")
        return validated
    
    async def test_connectivity_batch(self, addresses: Set[str]):
        """Test which onions are currently reachable"""
        tasks = [self.validator.test_connectivity(addr) for addr in addresses]
        results = await asyncio.gather(*tasks)
        
        active = [addr for addr, active in zip(addresses, results) if active]
        logger.info(f"Reachable: {len(active)}/{len(addresses)}")
        
        if active:
            latest = self.db.get_latest()
            if latest and latest != active[0]:
                msg = f"New Breachforum onion detected:\n`{active[0]}`\n(Previous: `{latest}`)"
                send_telegram_alert(msg)
        
        return active
    
    async def run(self):
        """Full discovery pipeline"""
        discovered = await self.discover_all()
        
        if discovered and PROXY_URL:
            logger.info("Testing connectivity...")
            active = await self.test_connectivity_batch(discovered)
            if active:
                logger.info(f"Primary: {active[0]}")
                return active[0]
        elif discovered:
            latest = self.db.get_latest()
            logger.info(f"Latest from DB: {latest}")
            return latest
        
        return None

# ============== CLI ==============
if __name__ == "__main__":
    import sys
    
    async def main():
        service = BreachforumDiscoveryService()
        result = await service.run()
        
        if result:
            print(f"ONION={result}")
            sys.exit(0)
        else:
            print("ONION=NOT_FOUND")
            sys.exit(1)
    
    asyncio.run(main())
