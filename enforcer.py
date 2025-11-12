"""
AVIS Enforcer - 资源执行和流量整形模块
负责维持分配的码率稳定性
"""
import numpy as np
from typing import Dict, List
from models import User
from config import CHUNK_DURATION


class Enforcer:
    """
    执行器 - 按照Allocator的分配结果执行调度
    
    功能:
    1. Token bucket流量整形 - 确保每个流的发送速率与分配的码率一致
    2. Per-flow shaping - 为每个用户维持独立的队列和整形器
    """
    
    def __init__(self, allocation_interval: float = 1.0):
        """
        初始化Enforcer
        
        Args:
            allocation_interval: 分配更新间隔（秒）
        """
        self.allocation_interval = allocation_interval
        self.token_buckets: Dict[int, 'TokenBucket'] = {}  # user_id -> TokenBucket
        self.per_flow_queues: Dict[int, float] = {}  # user_id -> 队列长度(比特)
    
    def init_for_users(self, users: List[User]):
        """为所有用户初始化Token Bucket"""
        for user in users:
            # 初始化token bucket：容量设置为2倍块大小，以吸收短期突发
            self.token_buckets[user.user_id] = TokenBucket(
                rate=user.current_bitrate,  # 码率(kbps)
                capacity=user.current_bitrate * 4  # 容量为4秒的数据
            )
            self.per_flow_queues[user.user_id] = 0
    
    def update_allocation(self, allocations: Dict[int, int]):
        """
        更新每个用户的token bucket速率
        
        Args:
            allocations: user_id -> 分配的码率(kbps)
        """
        for user_id, bitrate in allocations.items():
            if user_id in self.token_buckets:
                self.token_buckets[user_id].update_rate(bitrate)
    
    def schedule_packet(self, user_id: int, packet_size: int, 
                       current_time: float) -> bool:
        """
        对一个数据包进行调度决策
        
        Args:
            user_id: 用户ID
            packet_size: 数据包大小(比特)
            current_time: 当前时间(秒)
        
        Returns:
            True 如果数据包可以立即发送，False 否则
        """
        if user_id not in self.token_buckets:
            return False
        
        bucket = self.token_buckets[user_id]
        return bucket.can_send(packet_size, current_time)
    
    def send_packet(self, user_id: int, packet_size: int, 
                   current_time: float):
        """
        发送一个数据包（消耗tokens）
        
        Args:
            user_id: 用户ID
            packet_size: 数据包大小(比特)
            current_time: 当前时间(秒)
        """
        if user_id in self.token_buckets:
            self.token_buckets[user_id].send(packet_size, current_time)
    
    def advance_time(self, delta_t: float):
        """
        时间推进，为所有流添加tokens
        
        Args:
            delta_t: 时间增量(秒)
        """
        for bucket in self.token_buckets.values():
            bucket.add_tokens(delta_t)


class TokenBucket:
    """
    Token Bucket流量整形器
    
    工作原理:
    - 以固定速率生成tokens (速率 = bitrate)
    - 每个数据包需要消耗相应数量的tokens
    - 只有当有足够tokens时，才能发送数据包
    """
    
    def __init__(self, rate: float, capacity: float):
        """
        初始化Token Bucket
        
        Args:
            rate: 生成速率(kbps)
            capacity: 桶容量(kbps的数据量)
        """
        self.rate = rate  # kbps
        self.capacity = capacity  # kbps * seconds = 比特数
        self.tokens = capacity  # 初始装满
        self.last_update_time = 0.0
    
    def update_rate(self, new_rate: float):
        """更新生成速率"""
        self.rate = new_rate
    
    def add_tokens(self, delta_t: float):
        """
        添加tokens（时间流逝）
        
        Args:
            delta_t: 时间增量(秒)
        """
        # 生成的tokens = 速率(kbps) * 时间(秒)
        tokens_generated = self.rate * 1000 * delta_t  # 转换为比特
        self.tokens = min(self.tokens + tokens_generated, self.capacity)
    
    def can_send(self, packet_size: int, current_time: float) -> bool:
        """
        检查是否可以发送指定大小的数据包
        
        Args:
            packet_size: 数据包大小(比特)
            current_time: 当前时间(秒)
        
        Returns:
            True 如果有足够tokens，False 否则
        """
        # 首先更新到当前时间
        time_elapsed = current_time - self.last_update_time
        if time_elapsed > 0:
            self.add_tokens(time_elapsed)
            self.last_update_time = current_time
        
        return self.tokens >= packet_size
    
    def send(self, packet_size: int, current_time: float):
        """
        消耗tokens发送数据包
        
        Args:
            packet_size: 数据包大小(比特)
            current_time: 当前时间(秒)
        """
        # 首先更新到当前时间
        time_elapsed = current_time - self.last_update_time
        if time_elapsed > 0:
            self.add_tokens(time_elapsed)
            self.last_update_time = current_time
        
        self.tokens = max(0, self.tokens - packet_size)
