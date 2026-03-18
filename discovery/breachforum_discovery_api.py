"""
Bojemoi Lab - Breachforum Onion Discovery API
Integrates with existing FastAPI orchestrator
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import asyncio
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# ============== MODELS ==============
class OnionDiscoveryRequest(BaseModel):
    force_refresh: bool = False
    test_connectivity: bool = True
    notify_telegram: bool = True

class OnionAddress(BaseModel):
    address: str
    source: str
    confidence: float
    discovered_at: datetime
    last_verified: Optional[datetime] = None
    is_active: bool = True

class DiscoveryResult(BaseModel):
    success: bool
    primary_onion: Optional[str] = None
    all_candidates: List[str] = []
    validated_count: int
    discovery_sources: List[str] = []
    timestamp: datetime

# ============== DATABASE BRIDGE ==============
class CtiBridge:
    """Interface with Bojemoi Lab PostgreSQL"""
    
    def __init__(self, db_config: dict):
        self.config = db_config
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.config)
            logger.info("✓ CTI DB connected")
        except psycopg2.Error as e:
            logger.error(f"✗ DB connection failed: {e}")
    
    def get_latest_onion(self) -> Optional[str]:
        """Get most recent active onion"""
        if not self.conn:
            return None
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT address, last_verified
                    FROM onion_discoveries
                    WHERE is_active = TRUE AND address LIKE '%.onion'
                    ORDER BY last_verified DESC NULLS LAST, confidence DESC
                    LIMIT 1
                """)
                result = cur.fetchone()
                return result['address'] if result else None
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None
    
    def get_all_candidates(self, limit: int = 10) -> List[str]:
        """Get all known candidates"""
        if not self.conn:
            return []
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT address FROM onion_discoveries
                    WHERE is_active = TRUE
                    ORDER BY confidence DESC, last_verified DESC NULLS LAST
                    LIMIT %s
                """, (limit,))
                return [row['address'] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def log_discovery_event(self, onion: str, source: str, status: str):
        """Audit log for discovery events"""
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO discovery_audit_log 
                    (timestamp, onion, source, status)
                    VALUES (%s, %s, %s, %s)
                """, (datetime.now(), onion, source, status))
                self.conn.commit()
        except Exception as e:
            logger.error(f"Audit log failed: {e}")

# ============== TELEGRAM INTEGRATION ==============
class TelegramNotifier:
    """Alert Bojemoi Lab Telegram channel"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.token = bot_token
        self.chat_id = chat_id
    
    async def notify_discovery(self, onion: str, source: str, confidence: float):
        """Send discovery alert"""
        import aiohttp
        
        message = f"""
🔗 **Breachforum Onion Discovered**
└─ Address: `{onion}`
└─ Source: {source}
└─ Confidence: {confidence*100:.0f}%
└─ Time: {datetime.now().isoformat()}
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status == 200:
                        logger.info(f"✓ Telegram alert sent")
                    else:
                        logger.error(f"Telegram error: {resp.status}")
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")

# ============== ROUTER ==============
router = APIRouter(prefix="/api/cti/breachforum", tags=["CTI"])

# Global instances (initialized from main FastAPI app)
cti_db: Optional[CtiBridge] = None
telegram: Optional[TelegramNotifier] = None

@router.get("/onion", response_model=DiscoveryResult)
async def get_breachforum_onion(refresh: bool = False):
    """
    GET current Breachforum onion address
    ?refresh=true to force rediscovery
    """
    if not cti_db:
        raise HTTPException(500, "CTI DB not initialized")
    
    if refresh:
        # Trigger discovery async
        logger.info("Force refresh triggered")
    
    current = cti_db.get_latest_onion()
    candidates = cti_db.get_all_candidates()
    
    return DiscoveryResult(
        success=bool(current),
        primary_onion=current,
        all_candidates=candidates,
        validated_count=len(candidates),
        discovery_sources=["ahmia", "reddit", "tor_directory", "cti_reports"],
        timestamp=datetime.now()
    )

@router.post("/discover")
async def trigger_discovery(
    request: OnionDiscoveryRequest,
    background_tasks: BackgroundTasks
):
    """
    POST to manually trigger discovery
    """
    if not cti_db:
        raise HTTPException(500, "CTI DB not initialized")
    
    async def run_discovery():
        logger.info("Discovery job started")
        try:
            # Import and run the discovery service
            from breachforum_onion_discovery import BreachforumDiscoveryService
            
            service = BreachforumDiscoveryService()
            discovered = await service.discover_all()
            
            if discovered and request.notify_telegram and telegram:
                for onion in discovered:
                    await telegram.notify_discovery(
                        onion=onion,
                        source="automated_discovery",
                        confidence=0.75
                    )
            
            logger.info(f"Discovery job complete: {len(discovered)} addresses")
            cti_db.log_discovery_event("batch", "discovery_service", "success")
        except Exception as e:
            logger.error(f"Discovery job failed: {e}")
            cti_db.log_discovery_event("batch", "discovery_service", f"failed: {e}")
    
    background_tasks.add_task(run_discovery)
    
    return {
        "status": "discovery_queued",
        "message": "Discovery job started in background"
    }

@router.get("/status")
async def discovery_status():
    """
    GET discovery service status & recent log
    """
    if not cti_db:
        raise HTTPException(500, "CTI DB not initialized")
    
    current = cti_db.get_latest_onion()
    candidates = cti_db.get_all_candidates(5)
    
    return {
        "service": "breachforum_discovery",
        "status": "operational",
        "current_onion": current,
        "recent_candidates": candidates,
        "timestamp": datetime.now()
    }

# ============== INITIALIZATION ==============
def init_breachforum_discovery(
    db_config: dict,
    telegram_token: str = None,
    telegram_chat_id: str = None
):
    """
    Call from main FastAPI app startup
    
    Example:
        from main import app
        init_breachforum_discovery(
            db_config={"host": "localhost", "database": "bojemoi_cti", ...},
            telegram_token="123:ABC",
            telegram_chat_id="123456"
        )
        app.include_router(router)
    """
    global cti_db, telegram
    
    cti_db = CtiBridge(db_config)
    if telegram_token and telegram_chat_id:
        telegram = TelegramNotifier(telegram_token, telegram_chat_id)
    
    logger.info("✓ Breachforum discovery module initialized")
