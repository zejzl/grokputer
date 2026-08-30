"""
Security Hardening System for Grokputer
Comprehensive security with IP logging, rate limiting, authentication, and monitoring
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import json
import logging
import re
import secrets
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Security event record"""
    timestamp: float
    event_type: str
    ip_address: str
    user_id: Optional[str]
    action: str
    result: str
    severity: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'ip_address': self.ip_address,
            'user_id': self.user_id,
            'action': self.action,
            'result': self.result,
            'severity': self.severity,
            'details': self.details
        }


@dataclass
class RateLimitBucket:
    """Rate limiting bucket for tracking requests"""
    max_requests: int
    window_seconds: int
    timestamps: List[float] = field(default_factory=list)

    def is_allowed(self) -> bool:
        """Check if request is allowed within rate limit"""
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old timestamps
        self.timestamps = [ts for ts in self.timestamps if ts > cutoff]

        if len(self.timestamps) < self.max_requests:
            self.timestamps.append(now)
            return True

        return False

    def time_until_reset(self) -> float:
        """Get seconds until rate limit resets"""
        if not self.timestamps:
            return 0.0

        oldest = min(self.timestamps)
        reset_time = oldest + self.window_seconds
        return max(0.0, reset_time - time.time())


class IPLogger:
    """IP address logging and analysis"""

    def __init__(self, db_path: str = "logs/ip_logs.db"):
        self.db_path = db_path
        self._ensure_db()
        self.blocked_ips: Set[str] = set()
        self.suspicious_ips: Set[str] = set()

    def _ensure_db(self):
        """Create IP logging database"""
        Path(self.db_path).parent.mkdir(exist_ok=True, parents=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ip_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                ip_address TEXT NOT NULL,
                action TEXT NOT NULL,
                result TEXT NOT NULL,
                user_agent TEXT,
                endpoint TEXT,
                request_data TEXT,
                response_code INTEGER,
                blocked BOOLEAN DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocked_ips (
                ip_address TEXT PRIMARY KEY,
                blocked_at REAL NOT NULL,
                reason TEXT NOT NULL,
                expires_at REAL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ip_timestamp
            ON ip_logs(ip_address, timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_blocked_ip
            ON blocked_ips(ip_address, expires_at)
        """)

        conn.commit()
        conn.close()

    def log_request(
        self,
        ip_address: str,
        action: str,
        result: str,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        request_data: Optional[Dict] = None,
        response_code: Optional[int] = None
    ):
        """Log IP request"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ip_logs
            (timestamp, ip_address, action, result, user_agent, endpoint, request_data, response_code, blocked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            time.time(),
            ip_address,
            action,
            result,
            user_agent,
            endpoint,
            json.dumps(request_data) if request_data else None,
            response_code,
            ip_address in self.blocked_ips
        ))

        conn.commit()
        conn.close()

        # Check for suspicious activity
        self._analyze_ip_behavior(ip_address)

    def _analyze_ip_behavior(self, ip_address: str):
        """Analyze IP for suspicious patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check request rate in last minute
        cursor.execute("""
            SELECT COUNT(*) FROM ip_logs
            WHERE ip_address = ? AND timestamp > ?
        """, (ip_address, time.time() - 60))

        count = cursor.fetchone()[0]

        # Check failed attempts in last hour
        cursor.execute("""
            SELECT COUNT(*) FROM ip_logs
            WHERE ip_address = ?
            AND timestamp > ?
            AND result IN ('failed', 'unauthorized', 'forbidden')
        """, (ip_address, time.time() - 3600))

        failed_count = cursor.fetchone()[0]

        conn.close()

        # Flag as suspicious
        if count > 100:  # More than 100 requests/minute
            self.suspicious_ips.add(ip_address)
            logger.warning(f"Suspicious high-rate activity from {ip_address}: {count} req/min")

        if failed_count > 10:  # More than 10 failures/hour
            self.suspicious_ips.add(ip_address)
            logger.warning(f"Suspicious failed attempts from {ip_address}: {failed_count} failures/hour")

    def block_ip(self, ip_address: str, reason: str, duration_seconds: Optional[int] = None):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        expires_at = None
        if duration_seconds:
            expires_at = time.time() + duration_seconds

        cursor.execute("""
            INSERT OR REPLACE INTO blocked_ips
            (ip_address, blocked_at, reason, expires_at)
            VALUES (?, ?, ?, ?)
        """, (ip_address, time.time(), reason, expires_at))

        conn.commit()
        conn.close()

        logger.warning(f"BLOCKED IP: {ip_address} - Reason: {reason}")

    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM blocked_ips WHERE ip_address = ?", (ip_address,))

        conn.commit()
        conn.close()

        logger.info(f"UNBLOCKED IP: {ip_address}")

    def is_blocked(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """Check if IP is blocked"""
        # Check in-memory cache
        if ip_address in self.blocked_ips:
            return True, "IP blocked"

        # Check database for expired blocks
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT reason, expires_at FROM blocked_ips
            WHERE ip_address = ?
        """, (ip_address,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return False, None

        reason, expires_at = row

        # Check if block has expired
        if expires_at and expires_at < time.time():
            self.unblock_ip(ip_address)
            return False, None

        return True, reason

    def get_ip_stats(self, ip_address: str) -> Dict[str, Any]:
        """Get statistics for an IP address"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total requests
        cursor.execute("""
            SELECT COUNT(*) FROM ip_logs WHERE ip_address = ?
        """, (ip_address,))
        total_requests = cursor.fetchone()[0]

        # Failed requests
        cursor.execute("""
            SELECT COUNT(*) FROM ip_logs
            WHERE ip_address = ?
            AND result IN ('failed', 'unauthorized', 'forbidden')
        """, (ip_address,))
        failed_requests = cursor.fetchone()[0]

        # Recent activity (last hour)
        cursor.execute("""
            SELECT COUNT(*) FROM ip_logs
            WHERE ip_address = ? AND timestamp > ?
        """, (ip_address, time.time() - 3600))
        recent_requests = cursor.fetchone()[0]

        # Most common endpoints
        cursor.execute("""
            SELECT endpoint, COUNT(*) as count
            FROM ip_logs
            WHERE ip_address = ? AND endpoint IS NOT NULL
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 5
        """, (ip_address,))
        top_endpoints = cursor.fetchall()

        conn.close()

        return {
            'ip_address': ip_address,
            'total_requests': total_requests,
            'failed_requests': failed_requests,
            'recent_requests': recent_requests,
            'failure_rate': failed_requests / max(total_requests, 1),
            'is_suspicious': ip_address in self.suspicious_ips,
            'is_blocked': ip_address in self.blocked_ips,
            'top_endpoints': [{'endpoint': ep, 'count': c} for ep, c in top_endpoints]
        }


class AuthenticationManager:
    """Authentication and authorization"""

    def __init__(self, db_path: str = "logs/auth.db"):
        self.db_path = db_path
        self._ensure_db()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def _ensure_db(self):
        """Create authentication database"""
        Path(self.db_path).parent.mkdir(exist_ok=True, parents=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_login REAL,
                failed_attempts INTEGER DEFAULT 0,
                locked_until REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                name TEXT,
                permissions TEXT,
                created_at REAL NOT NULL,
                expires_at REAL,
                last_used REAL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                last_activity REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "user"
    ) -> str:
        """Create new user"""
        user_id = secrets.token_urlsafe(16)
        salt = secrets.token_hex(32)
        password_hash = self._hash_password(password, salt)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (user_id, username, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, password_hash, salt, role, time.time()))

            conn.commit()
            logger.info(f"Created user: {username} (role: {role})")
            return user_id

        except sqlite3.IntegrityError:
            raise ValueError(f"Username {username} already exists")
        finally:
            conn.close()

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: str
    ) -> Optional[str]:
        """Authenticate user and return session ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get user
        cursor.execute("""
            SELECT user_id, password_hash, salt, failed_attempts, locked_until
            FROM users WHERE username = ?
        """, (username,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            logger.warning(f"Authentication failed: unknown user {username} from {ip_address}")
            return None

        user_id, stored_hash, salt, failed_attempts, locked_until = row

        # Check if account is locked
        if locked_until and locked_until > time.time():
            conn.close()
            logger.warning(f"Authentication failed: account {username} locked until {datetime.fromtimestamp(locked_until)}")
            return None

        # Verify password
        password_hash = self._hash_password(password, salt)

        if password_hash != stored_hash:
            # Increment failed attempts
            failed_attempts += 1
            locked_until = None

            # Lock account after 5 failed attempts
            if failed_attempts >= 5:
                locked_until = time.time() + 900  # 15 minutes
                logger.warning(f"Account {username} locked due to {failed_attempts} failed attempts")

            cursor.execute("""
                UPDATE users
                SET failed_attempts = ?, locked_until = ?
                WHERE user_id = ?
            """, (failed_attempts, locked_until, user_id))

            conn.commit()
            conn.close()

            logger.warning(f"Authentication failed: invalid password for {username} from {ip_address}")
            return None

        # Reset failed attempts
        cursor.execute("""
            UPDATE users
            SET failed_attempts = 0, locked_until = NULL, last_login = ?
            WHERE user_id = ?
        """, (time.time(), user_id))

        # Create session
        session_id = secrets.token_urlsafe(32)
        expires_at = time.time() + 86400  # 24 hours

        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, ip_address, created_at, expires_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, ip_address, time.time(), expires_at, time.time()))

        conn.commit()
        conn.close()

        # Cache session
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'username': username,
            'ip_address': ip_address,
            'expires_at': expires_at
        }

        logger.info(f"Authentication successful: {username} from {ip_address}")
        return session_id

    def validate_session(
        self,
        session_id: str,
        ip_address: str
    ) -> Optional[Dict[str, Any]]:
        """Validate session and return user info"""
        # Check cache first
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]

            # Check expiration
            if session['expires_at'] < time.time():
                del self.active_sessions[session_id]
                return None

            # Check IP match
            if session['ip_address'] != ip_address:
                logger.warning(f"Session IP mismatch: {session_id} expected {session['ip_address']}, got {ip_address}")
                return None

            return session

        # Check database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.user_id, u.username, s.ip_address, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.session_id = ?
        """, (session_id,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        user_id, username, stored_ip, expires_at = row

        # Check expiration
        if expires_at < time.time():
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
            return None

        # Check IP match
        if stored_ip != ip_address:
            conn.close()
            logger.warning(f"Session IP mismatch: {session_id} expected {stored_ip}, got {ip_address}")
            return None

        # Update last activity
        cursor.execute("""
            UPDATE sessions SET last_activity = ? WHERE session_id = ?
        """, (time.time(), session_id))

        conn.commit()
        conn.close()

        # Cache session
        session = {
            'user_id': user_id,
            'username': username,
            'ip_address': ip_address,
            'expires_at': expires_at
        }
        self.active_sessions[session_id] = session

        return session


class RateLimiter:
    """Rate limiting with multiple strategies"""

    def __init__(self):
        self.buckets: Dict[str, RateLimitBucket] = defaultdict(
            lambda: RateLimitBucket(max_requests=100, window_seconds=60)
        )
        self.custom_limits: Dict[str, RateLimitBucket] = {}

    def check_rate_limit(
        self,
        identifier: str,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> Tuple[bool, Optional[float]]:
        """Check if request is within rate limit"""
        # Use custom limits if provided
        if max_requests and window_seconds:
            key = f"{identifier}:{max_requests}:{window_seconds}"

            if key not in self.custom_limits:
                self.custom_limits[key] = RateLimitBucket(max_requests, window_seconds)

            bucket = self.custom_limits[key]
        else:
            bucket = self.buckets[identifier]

        if bucket.is_allowed():
            return True, None
        else:
            retry_after = bucket.time_until_reset()
            return False, retry_after


class SecurityMonitor:
    """Security monitoring and alerting"""

    def __init__(
        self,
        ip_logger: IPLogger,
        auth_manager: AuthenticationManager,
        rate_limiter: RateLimiter
    ):
        self.ip_logger = ip_logger
        self.auth_manager = auth_manager
        self.rate_limiter = rate_limiter
        self.events: List[SecurityEvent] = []
        self.alert_thresholds = {
            'failed_auth_per_hour': 10,
            'rate_limit_violations_per_hour': 50,
            'unique_ips_per_minute': 100,
            'suspicious_patterns_per_hour': 5
        }

    async def log_event(
        self,
        event_type: str,
        ip_address: str,
        action: str,
        result: str,
        severity: str = "info",
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security event"""
        event = SecurityEvent(
            timestamp=time.time(),
            event_type=event_type,
            ip_address=ip_address,
            user_id=user_id,
            action=action,
            result=result,
            severity=severity,
            details=details or {}
        )

        self.events.append(event)

        # Log to file
        log_method = getattr(logger, severity.lower(), logger.info)
        log_method(
            f"SECURITY EVENT [{event_type}] {ip_address} - {action}: {result} | {details}"
        )

        # Check for alerts
        await self._check_alerts()

    async def _check_alerts(self):
        """Check for alert conditions"""
        now = time.time()
        hour_ago = now - 3600
        minute_ago = now - 60

        # Recent events
        recent_events = [e for e in self.events if e.timestamp > hour_ago]

        # Failed authentication attempts
        failed_auths = [
            e for e in recent_events
            if e.event_type == 'authentication' and e.result == 'failed'
        ]

        if len(failed_auths) > self.alert_thresholds['failed_auth_per_hour']:
            logger.critical(
                f"SECURITY ALERT: {len(failed_auths)} failed authentication attempts in last hour"
            )

        # Rate limit violations
        rate_limit_violations = [
            e for e in recent_events
            if e.event_type == 'rate_limit' and e.result == 'blocked'
        ]

        if len(rate_limit_violations) > self.alert_thresholds['rate_limit_violations_per_hour']:
            logger.critical(
                f"SECURITY ALERT: {len(rate_limit_violations)} rate limit violations in last hour"
            )

        # Unique IPs in last minute
        recent_minute = [e for e in self.events if e.timestamp > minute_ago]
        unique_ips = len(set(e.ip_address for e in recent_minute))

        if unique_ips > self.alert_thresholds['unique_ips_per_minute']:
            logger.critical(
                f"SECURITY ALERT: {unique_ips} unique IPs in last minute (possible DDoS)"
            )

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary"""
        now = time.time()
        hour_ago = now - 3600

        recent_events = [e for e in self.events if e.timestamp > hour_ago]

        return {
            'total_events': len(self.events),
            'recent_events': len(recent_events),
            'blocked_ips': len(self.ip_logger.blocked_ips),
            'suspicious_ips': len(self.ip_logger.suspicious_ips),
            'active_sessions': len(self.auth_manager.active_sessions),
            'events_by_type': self._count_by_field(recent_events, 'event_type'),
            'events_by_severity': self._count_by_field(recent_events, 'severity'),
            'top_ips': self._get_top_ips(recent_events, 10)
        }

    def _count_by_field(self, events: List[SecurityEvent], field: str) -> Dict[str, int]:
        """Count events by field"""
        counts = defaultdict(int)
        for event in events:
            value = getattr(event, field)
            counts[value] += 1
        return dict(counts)

    def _get_top_ips(self, events: List[SecurityEvent], limit: int) -> List[Dict[str, Any]]:
        """Get top IP addresses by event count"""
        ip_counts = defaultdict(int)
        for event in events:
            ip_counts[event.ip_address] += 1

        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)

        return [
            {'ip_address': ip, 'event_count': count}
            for ip, count in sorted_ips[:limit]
        ]


class SecurityHardening:
    """Main security hardening coordinator"""

    def __init__(self):
        self.ip_logger = IPLogger()
        self.auth_manager = AuthenticationManager()
        self.rate_limiter = RateLimiter()
        self.monitor = SecurityMonitor(
            self.ip_logger,
            self.auth_manager,
            self.rate_limiter
        )
        self.enabled = True

    async def validate_request(
        self,
        ip_address: str,
        action: str,
        session_id: Optional[str] = None,
        require_auth: bool = False
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate incoming request

        Returns:
            (allowed, error_message, user_info)
        """
        if not self.enabled:
            return True, None, None

        # Check if IP is blocked
        is_blocked, block_reason = self.ip_logger.is_blocked(ip_address)
        if is_blocked:
            await self.monitor.log_event(
                event_type='access_control',
                ip_address=ip_address,
                action=action,
                result='blocked',
                severity='warning',
                details={'reason': block_reason}
            )
            return False, f"Access denied: {block_reason}", None

        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(ip_address)
        if not allowed:
            await self.monitor.log_event(
                event_type='rate_limit',
                ip_address=ip_address,
                action=action,
                result='blocked',
                severity='warning',
                details={'retry_after': retry_after}
            )

            # Auto-block after too many rate limit violations
            self.ip_logger.block_ip(
                ip_address,
                "Too many rate limit violations",
                duration_seconds=3600  # 1 hour
            )

            return False, f"Rate limit exceeded. Retry after {retry_after:.1f}s", None

        # Check authentication if required
        user_info = None
        if require_auth:
            if not session_id:
                await self.monitor.log_event(
                    event_type='authentication',
                    ip_address=ip_address,
                    action=action,
                    result='failed',
                    severity='warning',
                    details={'reason': 'missing_session'}
                )
                return False, "Authentication required", None

            user_info = self.auth_manager.validate_session(session_id, ip_address)
            if not user_info:
                await self.monitor.log_event(
                    event_type='authentication',
                    ip_address=ip_address,
                    action=action,
                    result='failed',
                    severity='warning',
                    details={'reason': 'invalid_session'}
                )
                return False, "Invalid or expired session", None

        # Log successful request
        self.ip_logger.log_request(
            ip_address=ip_address,
            action=action,
            result='allowed',
            endpoint=action
        )

        await self.monitor.log_event(
            event_type='request',
            ip_address=ip_address,
            action=action,
            result='allowed',
            severity='info',
            user_id=user_info['user_id'] if user_info else None
        )

        return True, None, user_info

    def require_auth(self, func):
        """Decorator to require authentication"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract IP and session from kwargs
            ip_address = kwargs.get('ip_address', '127.0.0.1')
            session_id = kwargs.get('session_id')
            action = func.__name__

            # Validate request
            allowed, error, user_info = await self.validate_request(
                ip_address=ip_address,
                action=action,
                session_id=session_id,
                require_auth=True
            )

            if not allowed:
                raise PermissionError(error)

            # Add user_info to kwargs
            kwargs['user_info'] = user_info

            return await func(*args, **kwargs)

        return wrapper


# Global security instance
_security_instance: Optional[SecurityHardening] = None


def get_security() -> SecurityHardening:
    """Get global security instance"""
    global _security_instance
    if _security_instance is None:
        _security_instance = SecurityHardening()
    return _security_instance


# Example usage
if __name__ == "__main__":
    async def demo():
        """Demo security system"""
        security = get_security()

        # Create test user
        try:
            user_id = security.auth_manager.create_user(
                username="admin",
                password="SecurePassword123!",
                role="admin"
            )
            print(f"Created user: {user_id}")
        except ValueError as e:
            print(f"User creation: {e}")

        # Test authentication
        session_id = security.auth_manager.authenticate(
            username="admin",
            password="SecurePassword123!",
            ip_address="192.168.1.100"
        )

        if session_id:
            print(f"Authentication successful: {session_id}")

            # Test request validation
            allowed, error, user_info = await security.validate_request(
                ip_address="192.168.1.100",
                action="test_action",
                session_id=session_id,
                require_auth=True
            )

            print(f"Request validation: allowed={allowed}, user={user_info}")

        # Test rate limiting
        for i in range(105):
            allowed, error, _ = await security.validate_request(
                ip_address="192.168.1.101",
                action="spam_test"
            )
            if not allowed:
                print(f"Rate limited at request {i}: {error}")
                break

        # Get security summary
        summary = security.monitor.get_security_summary()
        print("\nSecurity Summary:")
        print(json.dumps(summary, indent=2))

    asyncio.run(demo())
