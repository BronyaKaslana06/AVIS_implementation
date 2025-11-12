"""
网络仿真环境 - 模拟DASH视频流场景
"""
import numpy as np
import random
from typing import List, Dict, Tuple
from models import User, AllocationResult
from allocator import Allocator
from enforcer import Enforcer
from config import (
    NUM_USERS, TOTAL_RESOURCE_BLOCKS, SIMULATION_TIME, ALLOCATION_INTERVAL,
    CHUNK_DURATION, CHANNEL_MODELS, BITRATE_LEVELS, FAIRNESS_WINDOW
)


class NetworkSimulator:
    """LTE/无线网络仿真环境"""
    
    def __init__(self, num_users: int = NUM_USERS, total_resources: int = TOTAL_RESOURCE_BLOCKS):
        """
        初始化网络仿真环境
        
        Args:
            num_users: DASH用户数量
            total_resources: 基站总资源块数
        """
        self.num_users = num_users
        self.total_resources = total_resources
        self.current_time = 0.0
        
        # 用户列表
        self.users: List[User] = []
        
        # 信道条件 (模拟用户在不同位置)
        self.channel_qualities: Dict[int, str] = {}
        self.channel_capacities: Dict[int, float] = {}  # kbps
        
        # 创建用户和信道
        self._init_users()
    
    def _init_users(self):
        """初始化用户和信道条件"""
        channel_types = list(CHANNEL_MODELS.keys())
        
        for i in range(self.num_users):
            user = User(
                user_id=i,
                channel_quality=channel_types[i % len(channel_types)]
            )
            self.users.append(user)
            
            # 为用户分配信道容量（添加随机波动）
            quality = user.channel_quality
            model = CHANNEL_MODELS[quality]
            base_throughput = model['base_throughput']
            variance = model['variance']
            
            # 初始化信道容量
            capacity = np.random.normal(base_throughput, variance)
            capacity = max(500, capacity)  # 最低500kbps
            self.channel_capacities[user.user_id] = capacity
    
    def update_channel_conditions(self):
        """
        动态更新信道条件（模拟信道衰落）
        
        在每个调度时间间隔，信道容量会根据信道质量进行变化
        """
        for user in self.users:
            quality = user.channel_quality
            model = CHANNEL_MODELS[quality]
            base_throughput = model['base_throughput']
            variance = model['variance']
            
            # 随机游走模型：新容量 = 旧容量 + 随机变化
            current_capacity = self.channel_capacities[user.user_id]
            change = np.random.normal(0, variance * 0.5)
            new_capacity = current_capacity + change
            
            # 限制在合理范围内
            new_capacity = np.clip(new_capacity, base_throughput * 0.5, base_throughput * 1.5)
            self.channel_capacities[user.user_id] = max(500, new_capacity)
    
    def get_user_throughput(self, user_id: int) -> float:
        """获取用户在当前信道条件下的最大吞吐量(kbps)"""
        return self.channel_capacities.get(user_id, 2000)
    
    def get_channel_quality_snapshot(self) -> Dict[int, Dict]:
        """获取当前信道质量快照"""
        snapshot = {}
        for user in self.users:
            snapshot[user.user_id] = {
                'quality': user.channel_quality,
                'capacity': self.channel_capacities.get(user.user_id, 2000)
            }
        return snapshot


class SimulationEngine:
    """AVIS仿真引擎"""
    
    def __init__(self, use_avis: bool = True, alpha: float = 0.5):
        """
        初始化仿真引擎
        
        Args:
            use_avis: 是否使用AVIS调度器（True）或无调度（False）
            alpha: AVIS的惩罚函数参数
        """
        self.use_avis = use_avis
        self.alpha = alpha
        self.simulator = NetworkSimulator()
        
        # 如果使用AVIS，初始化Allocator和Enforcer
        if use_avis:
            self.allocator = Allocator(alpha=alpha)
            self.enforcer = Enforcer(allocation_interval=ALLOCATION_INTERVAL)
            self.enforcer.init_for_users(self.simulator.users)
        else:
            self.allocator = None
            self.enforcer = None
        
        # 历史记录
        self.history = {
            'time': [],
            'bitrates': {user.user_id: [] for user in self.simulator.users},
            'allocated_resources': {user.user_id: [] for user in self.simulator.users},
            'channel_capacities': {user.user_id: [] for user in self.simulator.users},
            'resource_switches': {user.user_id: 0 for user in self.simulator.users},
        }
        
        # 统计数据
        self.stats = {
            'total_bitrate_switches': {user.user_id: 0 for user in self.simulator.users},
            'avg_bitrate': {user.user_id: [] for user in self.simulator.users},
            'total_resources_used': 0,
        }
    
    def run_simulation(self, duration: float = SIMULATION_TIME) -> Dict:
        """
        运行完整仿真
        
        Args:
            duration: 仿真时长（秒）
        
        Returns:
            包含仿真结果的字典
        """
        num_steps = int(duration / ALLOCATION_INTERVAL)
        
        for step in range(num_steps):
            self.current_time = step * ALLOCATION_INTERVAL
            
            # 更新信道条件
            self.simulator.update_channel_conditions()
            
            # 执行调度
            if self.use_avis:
                self._run_avis_scheduling()
            else:
                self._run_no_avis_scheduling()
            
            # 记录历史
            self._record_history()
            
            # 实时进度
            if step % 50 == 0:
                print(f"  仿真进度: {step}/{num_steps} (时间: {self.current_time:.1f}s)")
        
        return self._compute_final_stats()
    
    def _run_avis_scheduling(self):
        """运行AVIS调度"""
        # Allocator阶段：计算最优码率分配
        allocation_result = self.allocator.discrete_optimization(
            self.simulator.users,
            self.simulator.channel_capacities
        )
        
        # 更新用户推荐码率
        for user in self.simulator.users:
            old_bitrate = user.current_bitrate
            
            if user.user_id in allocation_result.user_bitrates:
                user.current_bitrate = allocation_result.user_bitrates[user.user_id]
            
            # 统计码率切换
            if user.current_bitrate != old_bitrate:
                self.stats['total_bitrate_switches'][user.user_id] += 1
            
            # Enforcer阶段：流量整形
            if self.enforcer:
                self.enforcer.update_allocation({
                    user.user_id: user.current_bitrate
                })
            
            user.bitrate_history.append(user.current_bitrate)
            user.allocated_resources.append(
                allocation_result.user_allocations.get(user.user_id, 0)
            )
    
    def _run_no_avis_scheduling(self):
        """无调度的基线方案"""
        # 简单策略：根据信道容量选择最接近的码率
        for user in self.simulator.users:
            old_bitrate = user.current_bitrate
            
            # 获取用户的信道容量
            capacity = self.simulator.get_user_throughput(user.user_id)
            
            # 选择不超过信道容量的最高码率
            suitable_bitrates = [br for br in BITRATE_LEVELS if br <= capacity * 0.9]
            if suitable_bitrates:
                new_bitrate = max(suitable_bitrates)
            else:
                new_bitrate = BITRATE_LEVELS[0]
            
            # 为了增加一些波动（模拟TCP估计误差），有概率选择低码率
            if np.random.random() < 0.1:
                current_idx = BITRATE_LEVELS.index(new_bitrate) if new_bitrate in BITRATE_LEVELS else 0
                if current_idx > 0:
                    new_bitrate = BITRATE_LEVELS[current_idx - 1]
            
            user.current_bitrate = new_bitrate
            
            # 统计码率切换
            if user.current_bitrate != old_bitrate:
                self.stats['total_bitrate_switches'][user.user_id] += 1
            
            user.bitrate_history.append(user.current_bitrate)
            # NO-AVIS不记录分配资源
            user.allocated_resources.append(0)
    
    def _record_history(self):
        """记录当前仿真状态"""
        self.history['time'].append(self.current_time)
        
        for user in self.simulator.users:
            self.history['bitrates'][user.user_id].append(user.current_bitrate)
            if user.allocated_resources:
                self.history['allocated_resources'][user.user_id].append(
                    user.allocated_resources[-1]
                )
            self.history['channel_capacities'][user.user_id].append(
                self.simulator.channel_capacities[user.user_id]
            )
    
    def _compute_final_stats(self) -> Dict:
        """计算最终统计数据"""
        results = {
            'mode': 'AVIS' if self.use_avis else 'NO-AVIS',
            'alpha': self.alpha if self.use_avis else None,
            'users': [],
        }
        
        for user in self.simulator.users:
            user_stats = {
                'user_id': user.user_id,
                'channel_quality': user.channel_quality,
                'total_bitrate_switches': self.stats['total_bitrate_switches'][user.user_id],
                'avg_bitrate': np.mean(user.bitrate_history) if user.bitrate_history else 0,
                'bitrate_history': user.bitrate_history,
            }
            results['users'].append(user_stats)
        
        results['history'] = self.history
        return results
