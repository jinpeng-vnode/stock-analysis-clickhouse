"""
代理池工具类 - 支持多线程代理管理（迁移到 common/utils/）
"""
import os
import time
import threading
import requests
from collections import deque
from loguru import logger


class ProxyBalanceExhausted(Exception):
    """代理余额用尽异常"""
    pass


class ProxyPool:
    """线程安全代理池：每个线程绑定一个代理，失效前复用。"""

    def __init__(self, username: str, password: str, batch_size: int = 20):
        self.username = username
        self.password = password
        self.batch_size = max(1, batch_size)
        self._lock = threading.Lock()
        self._proxies: deque[str] = deque()
        self.balance_exhausted: bool = False
        self.exhaust_message: str = ""
        self._thread_proxies = {}

        self.total_fetched = 0
        self.total_used = 0
        self.total_banned = 0
        self.current_available = 0

    def _fetch_batch(self) -> None:
        try:
            secret_id = os.getenv("KDL_SECRET_ID", "").strip()
            signature = os.getenv("KDL_SIGNATURE", "").strip()
            if not secret_id or not signature:
                logger.warning("未配置 KDL_SECRET_ID / KDL_SIGNATURE，跳过拉取代理")
                return
            url = (
                "https://dps.kdlapi.com/api/getdps/"
                f"?secret_id={secret_id}&signature={signature}"
                f"&num={self.batch_size}&format=text&sep=1"
            )
            text = requests.get(url, timeout=10).text.strip()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if not lines:
                return
            for line in lines:
                if line.startswith("ERROR") or ("余额" in line or "用尽" in line):
                    self.balance_exhausted = True
                    self.exhaust_message = line
                    logger.error(f"代理服务返回错误: {line}")
                    return
            for ip_port in lines:
                self._proxies.append(ip_port)
                self.total_fetched += 1
            self.current_available = len(self._proxies)
            logger.debug(f"获取代理: +{len(lines)}个, 当前可用: {self.current_available}")
        except Exception as e:
            logger.warning(f"拉取代理失败: {e}")

    def get(self) -> dict:
        import threading
        thread_id = threading.get_ident()
        current_time = time.time()
        with self._lock:
            if self.balance_exhausted:
                raise ProxyBalanceExhausted(self.exhaust_message or "代理余额已用尽")
            if thread_id in self._thread_proxies:
                proxy_info = self._thread_proxies[thread_id]
                proxy_info['use_count'] += 1
                self.total_used += 1
                ip_port = proxy_info['proxy']
                auth = f"http://{self.username}:{self.password}@{ip_port}/"
                return {"http": auth, "https": auth}
            if not self._proxies:
                self._fetch_batch()
            if self.balance_exhausted:
                raise ProxyBalanceExhausted(self.exhaust_message or "代理余额已用尽")
            if not self._proxies:
                return {}
            ip_port = self._proxies.popleft()
            self._thread_proxies[thread_id] = {
                'proxy': ip_port,
                'start_time': current_time,
                'use_count': 1,
                'last_success': current_time
            }
            self.total_used += 1
            self.current_available = len(self._proxies)
        auth = f"http://{self.username}:{self.password}@{ip_port}/"
        logger.debug(f"线程 {thread_id} 分配新代理: {ip_port}")
        return {"http": auth, "https": auth}

    def ban_and_rotate(self) -> None:
        import threading
        thread_id = threading.get_ident()
        with self._lock:
            if self.balance_exhausted:
                return
            if thread_id in self._thread_proxies:
                bad_proxy = self._thread_proxies[thread_id]['proxy']
                use_count = self._thread_proxies[thread_id]['use_count']
                del self._thread_proxies[thread_id]
                self.total_banned += 1
                logger.debug(f"代理失效: {bad_proxy} (使用{use_count}次)")
            if len(self._proxies) < max(1, self.batch_size // 2):
                self._fetch_batch()

    def mark_success(self) -> None:
        import threading
        thread_id = threading.get_ident()
        current_time = time.time()
        with self._lock:
            if thread_id in self._thread_proxies:
                self._thread_proxies[thread_id]['last_success'] = current_time

    def get_stats(self) -> dict:
        with self._lock:
            active_threads = len(self._thread_proxies)
            return {
                'total_fetched': self.total_fetched,
                'total_used': self.total_used,
                'total_banned': self.total_banned,
                'current_available': len(self._proxies),
                'active_threads': active_threads,
                'success_rate': round((self.total_used - self.total_banned) / max(1, self.total_used) * 100, 2) if self.total_used > 0 else 0
            }

    def print_stats(self) -> None:
        stats = self.get_stats()
        logger.info(
            f"代理统计: 获取={stats['total_fetched']}个, 使用={stats['total_used']}次, 淘汰={stats['total_banned']}个, 可用={stats['current_available']}个, 活跃线程={stats['active_threads']}个, 成功率={stats['success_rate']}%"
        )


