"""
AVIS Enforcer - 资源执行和流量整形模块
负责维持分配的码率稳定性

论文设计要点（Section 3.2）：
1. MaxRate设置（公式13）: MaxRate_i = (r_ij + r_ij+1) / 2
   - "甜点"策略：让客户端稳定在分配的码率，不升不降
2. MinRate保障: MinRate_i = r_ij
   - 加权调度器确保每个流获得最低保障
3. Token Bucket整形 + 加权公平调度 (WFQ)
"""
import numpy as np
from typing import Dict, List
from models import User
from config import BITRATE_LEVELS


class Enforcer:
    """
    执行器 - 按照Allocator的分配结果执行调度
    
    功能:
    1. Token bucket流量整形 - 确保每个流的发送速率不超过MaxRate
    2. 加权公平调度 (WFQ) - 确保每个流获得MinRate保障
    3. Per-flow shaping - 为每个用户维持独立的队列和整形器
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
        self.min_rates: Dict[int, float] = {}  # user_id -> MinRate (kbps)
        self.max_rates: Dict[int, float] = {}  # user_id -> MaxRate (kbps)
    
    def init_for_users(self, users: List[User]):
        """为所有用户初始化Token Bucket和速率参数"""
        for user in users:
            # 计算MaxRate（论文公式13）
            max_rate = self._compute_max_rate(user.current_bitrate)
            
            # 初始化token bucket：容量设置为4秒的数据量
            # 注意：capacity单位需要是bits，与tokens单位一致
            self.token_buckets[user.user_id] = TokenBucket(
                rate=max_rate,  # 使用MaxRate而非分配码率 (kbps)
                capacity=max_rate * 4 * 1000  # 4秒的数据量 (bits)
            )
            self.per_flow_queues[user.user_id] = 0
            self.min_rates[user.user_id] = user.current_bitrate  # MinRate = r_ij
            self.max_rates[user.user_id] = max_rate
    
    def _compute_max_rate(self, allocated_bitrate: int) -> float:
        """
        计算MaxRate（论文公式13的"甜点"策略）
        
        MaxRate_i = (r_ij + r_ij+1) / 2
        
        物理意义：
        - 如果MaxRate = r_ij，客户端会降级到r_ij-1
        - 如果MaxRate = r_ij+1，客户端会升级到r_ij+1
        - 甜点MaxRate让客户端稳定在r_ij
        
        Args:
            allocated_bitrate: Allocator分配的码率r_ij (kbps)
        
        Returns:
            MaxRate (kbps)
        """
        try:
            current_idx = BITRATE_LEVELS.index(allocated_bitrate)
        except ValueError:
            # 如果码率不在标准列表中，返回自身
            return allocated_bitrate
        
        # 如果已经是最高档，MaxRate = r_ij * 1.2 (留20%余量)
        if current_idx >= len(BITRATE_LEVELS) - 1:
            return allocated_bitrate * 1.2
        
        # 否则，MaxRate = (r_ij + r_ij+1) / 2
        next_bitrate = BITRATE_LEVELS[current_idx + 1]
        max_rate = (allocated_bitrate + next_bitrate) / 2.0
        
        return max_rate
    
    def update_allocation(self, allocations: Dict[int, int]):
        """
        更新每个用户的速率限制（论文方法）
        
        Args:
            allocations: user_id -> 分配的码率(kbps)
        """
        for user_id, bitrate in allocations.items():
            if user_id in self.token_buckets:
                # 更新MinRate和MaxRate
                self.min_rates[user_id] = bitrate
                max_rate = self._compute_max_rate(bitrate)
                self.max_rates[user_id] = max_rate
                
                # 更新Token Bucket的速率和容量
                bucket = self.token_buckets[user_id]
                bucket.rate = max_rate
                bucket.capacity = max_rate * 4 * 1000  # 4秒的数据量 (bits)
                
                # 确保tokens不超过新容量，但也给予足够的初始预算
                # 这模拟了"新分配周期开始时有足够的传输预算"
                if bucket.tokens < bucket.capacity * 0.5:
                    bucket.tokens = bucket.capacity * 0.5
    
    def enforce_bitrate(self, user_id: int, requested_bitrate: int, 
                       delta_t: float) -> tuple:
        """
        使用Token Bucket对请求的码率进行流量整形
        
        这是Enforcer的核心功能：确保用户不能超过MaxRate限制。
        
        Args:
            user_id: 用户ID
            requested_bitrate: Allocator分配的码率 (kbps)
            delta_t: 时间间隔 (秒)
        
        Returns:
            (实际允许的码率, 是否被限速): 
            - 如果tokens充足，返回原码率
            - 如果tokens不足，返回降级后的码率
        """
        if user_id not in self.token_buckets:
            return requested_bitrate, False
        
        bucket = self.token_buckets[user_id]
        
        # 1. 时间流逝，添加新的tokens（模拟带宽恢复）
        bucket.add_tokens(delta_t)
        
        # 2. 计算这个周期需要传输的数据量
        # 单位: kbps * 秒 * 1000 = bits
        required_bits = requested_bitrate * delta_t * 1000
        
        # 3. 检查Token Bucket是否有足够的tokens
        if bucket.tokens >= required_bits:
            # tokens充足，允许全速传输
            bucket.tokens -= required_bits
            return requested_bitrate, False
        else:
            # tokens不足，需要限速
            # 计算当前tokens能支持的最大码率
            available_bits = bucket.tokens
            max_supported_kbps = available_bits / (delta_t * 1000)
            
            # 消耗所有可用tokens
            bucket.tokens = 0
            
            # 找到不超过可支持速率的最高标准码率档位
            suitable_bitrates = [br for br in BITRATE_LEVELS 
                               if br <= max_supported_kbps]
            
            if suitable_bitrates:
                enforced_bitrate = max(suitable_bitrates)
            else:
                # tokens严重不足，只能选最低档
                enforced_bitrate = BITRATE_LEVELS[0]
            
            return enforced_bitrate, True
    
    def get_token_status(self, user_id: int) -> Dict:
        """
        获取用户Token Bucket的状态（用于调试和统计）
        
        Returns:
            包含tokens、rate、capacity的字典
        """
        if user_id not in self.token_buckets:
            return {'tokens': 0, 'rate': 0, 'capacity': 0}
        
        bucket = self.token_buckets[user_id]
        return {
            'tokens': bucket.tokens,
            'rate': bucket.rate,
            'capacity': bucket.capacity,
            'fill_ratio': bucket.tokens / bucket.capacity if bucket.capacity > 0 else 0
        }
    
    def schedule_packet(self, user_id: int, packet_size: int, 
                       current_time: float) -> bool:
        """
        对一个数据包进行调度决策（包含WFQ调度逻辑）
        
        检查两个条件：
        1. Token Bucket允许（MaxRate限制）
        2. WFQ调度器允许（MinRate保障）
        
        Args:
            user_id: 用户ID
            packet_size: 数据包大小(比特)
            current_time: 当前时间(秒)
        
        Returns:
            True 如果数据包可以立即发送，False 否则
        """
        if user_id not in self.token_buckets:
            return False
        
        # 条件1: 检查Token Bucket（MaxRate限制）
        bucket = self.token_buckets[user_id]
        if not bucket.can_send(packet_size, current_time):
            return False
        
        # 条件2: 检查WFQ调度（MinRate保障）
        # 简化实现：只要在MaxRate限制内，就允许发送
        # 完整的WFQ需要维护虚拟时间和权重，这里简化为MinRate已由Allocator保证
        return True
    
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
    
    def get_shaping_rate(self, user_id: int) -> Dict[str, float]:
        """
        获取用户的整形参数（用于调试和监控）
        
        Returns:
            {'min_rate': MinRate, 'max_rate': MaxRate}
        """
        return {
            'min_rate': self.min_rates.get(user_id, 0),
            'max_rate': self.max_rates.get(user_id, 0)
        }


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
