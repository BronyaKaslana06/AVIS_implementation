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
    CHANNEL_MODELS, BITRATE_LEVELS
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
        self.channel_capacities: Dict[int, float] = {}  # kbps 由simulator维护，表示各个用户当前的信道容量
        
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
    
    def __init__(self, use_avis: bool = True, alpha: float = 0.5, optimization_type: str = 'continuous'):
        """
        初始化仿真引擎
        
        Args:
            use_avis: 是否使用AVIS调度器（True）或无调度（False）
            alpha: AVIS的惩罚函数参数
            optimization_type: 优化方法类型 ('discrete' 或 'continuous')
        """
        self.use_avis = use_avis
        self.alpha = alpha
        self.optimization_type = optimization_type
        self.simulator = NetworkSimulator()
        
        # 如果使用AVIS，初始化Allocator和Enforcer
        if use_avis:
            self.allocator = Allocator(alpha=alpha)
            self.enforcer = Enforcer(allocation_interval=ALLOCATION_INTERVAL)
            self.enforcer.init_for_users(self.simulator.users)
        else:
            # NO-AVIS也需要allocator来计算资源（用于对比）
            self.allocator = Allocator(alpha=0)
            self.enforcer = None
        
        # NO-AVIS: 每个用户的TCP吞吐量估计器（移动平均）
        self.throughput_estimates = {user.user_id: None for user in self.simulator.users}
        self.ewma_alpha = 0.3  # 指数加权移动平均的平滑系数
        
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
        
        # 详细调度日志
        self.scheduling_log: List[Dict] = []
    
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
        # Allocator阶段：根据优化类型选择方法
        if self.optimization_type == 'discrete':
            allocation_result = self.allocator.discrete_optimization(
                self.simulator.users,
                self.simulator.channel_capacities
            )
        else:  # continuous
            allocation_result = self.allocator.continuous_optimization(
                self.simulator.users,
                self.simulator.channel_capacities
            )
        
        # 更新用户推荐码率
        for user in self.simulator.users:
            old_bitrate = user.current_bitrate
            
            if user.user_id in allocation_result.user_bitrates:
                user.current_bitrate = allocation_result.user_bitrates[user.user_id]
            
            # Enforcer阶段：Token Bucket流量整形
            if self.enforcer:
                # 1. 更新MaxRate参数
                self.enforcer.update_allocation({
                    user.user_id: user.current_bitrate
                })
                
                # 2. 使用Token Bucket进行流量整形
                # 检查是否有足够的tokens支持当前码率
                enforced_bitrate, was_throttled = self.enforcer.enforce_bitrate(
                    user.user_id,
                    user.current_bitrate,
                    ALLOCATION_INTERVAL
                )
                
                # 如果被限速，使用Enforcer允许的码率
                if was_throttled:
                    user.current_bitrate = enforced_bitrate
                    # 记录限速事件（可选，用于分析）
                    if 'throttle_count' not in self.stats:
                        self.stats['throttle_count'] = {u.user_id: 0 for u in self.simulator.users}
                    self.stats['throttle_count'][user.user_id] += 1
            
            # 统计码率切换
            if user.current_bitrate != old_bitrate:
                self.stats['total_bitrate_switches'][user.user_id] += 1
            
            user.bitrate_history.append(user.current_bitrate)
            user.allocated_resources.append(
                allocation_result.user_allocations.get(user.user_id, 0)
            )
        
        # 记录本轮调度详细信息
        self._log_scheduling_round(allocation_result)
    
    def _run_no_avis_scheduling(self):
        """
        无调度的基线方案 - 模拟真实DASH客户端行为
        """
        # 计算当前时刻的资源竞争情况（模拟块下载重叠）
        # total_demand是所有用户实际正在请求的数据量，比如用户选择了 4000kbps 的码率档位
        # channel_capacities是各个用户当前的信道容量，是simulator维护的，是这条链路理论上最大能承载的速率
        # update_channel_conditions对所有用户的信道容量进行更新，下一秒的容量是在当前容量的基础上加一个随机变化量，而不是重新生成，模拟真实世界中信号强度的连续变化。
        total_demand = sum(user.current_bitrate for user in self.simulator.users)
        competition_factor = total_demand / (sum(self.simulator.channel_capacities.values()) + 1e-6)
        
        for user in self.simulator.users:
            old_bitrate = user.current_bitrate
            
            # 获取真实信道容量
            true_capacity = self.simulator.get_user_throughput(user.user_id)
            
            # 模拟TCP吞吐量估计（带噪声和竞争干扰）
            # 论文: "under-estimation or over-estimation of the underlying bandwidth"
            
            # 1. 基础测量值 = 真实容量 + 高斯噪声
            measurement_noise = np.random.normal(0, true_capacity * 0.15)
            measured_throughput = true_capacity + measurement_noise
            
            # 2. 竞争干扰：当多用户同时下载时，会低估可用带宽
            if competition_factor > 0.5:
                # 高竞争时，测量值被压低
                interference = np.random.uniform(0.7, 0.95)
                measured_throughput *= interference
            elif competition_factor < 0.3:
                # 低竞争时，可能高估带宽
                overestimate = np.random.uniform(1.0, 1.2)
                measured_throughput *= overestimate
            
            # 3. 更新移动平均估计（EWMA）
            # 论文: "moving average of the TCP throughput"
            if self.throughput_estimates[user.user_id] is None:
                self.throughput_estimates[user.user_id] = measured_throughput
            else:
                self.throughput_estimates[user.user_id] = (
                    self.ewma_alpha * measured_throughput + 
                    (1 - self.ewma_alpha) * self.throughput_estimates[user.user_id]
                )
            
            estimated_throughput = self.throughput_estimates[user.user_id]
            
            # 基于估计吞吐量选择码率
            # 论文: "requests chunks of the highest rate that can be supported"
            
            # 选择不超过估计吞吐量的最高码率（留10%余量）
            suitable_bitrates = [br for br in BITRATE_LEVELS if br <= estimated_throughput * 0.9]
            if suitable_bitrates:
                new_bitrate = max(suitable_bitrates)
            else:
                new_bitrate = BITRATE_LEVELS[0]
            
            user.current_bitrate = new_bitrate
            
            # 统计码率切换
            if user.current_bitrate != old_bitrate:
                self.stats['total_bitrate_switches'][user.user_id] += 1
            
            user.bitrate_history.append(user.current_bitrate)
            # NO-AVIS也计算资源消耗（用于对比）
            resources = self.allocator._compute_resources_for_bitrate(user.current_bitrate, true_capacity)
            user.allocated_resources.append(resources)
        
        # 记录本轮调度详细信息（NO-AVIS模式）
        self._log_scheduling_round()
    
    def _log_scheduling_round(self, allocation_result=None):
        """
        记录每轮调度的详细信息
        
        Args:
            allocation_result: Allocator返回的分配结果（仅AVIS模式）
        """
        round_log = {
            'time': self.current_time,
            'mode': 'AVIS' if self.use_avis else 'NO-AVIS',
            'users': {}
        }
        
        for user in self.simulator.users:
            user_log = {
                'channel_capacity': self.simulator.channel_capacities[user.user_id],
                'current_bitrate': user.current_bitrate,
            }
            
            # AVIS模式下，记录更多详细信息
            if self.use_avis and allocation_result:
                user_log['allocated_bitrate'] = allocation_result.user_bitrates.get(user.user_id, 0)
                user_log['allocated_resources'] = allocation_result.user_allocations.get(user.user_id, 0)
                
                # Enforcer信息
                if self.enforcer:
                    user_log['max_rate'] = self.enforcer.max_rates.get(user.user_id, 0)
                    user_log['min_rate'] = self.enforcer.min_rates.get(user.user_id, 0)
                    token_status = self.enforcer.get_token_status(user.user_id)
                    user_log['tokens'] = token_status.get('tokens', 0)
                    user_log['bucket_capacity'] = token_status.get('capacity', 0)
                    user_log['was_throttled'] = user_log['current_bitrate'] < user_log['allocated_bitrate']
            else:
                # NO-AVIS模式
                user_log['estimated_throughput'] = self.throughput_estimates.get(user.user_id, 0)
            
            round_log['users'][user.user_id] = user_log
        
        self.scheduling_log.append(round_log)
    
    def save_scheduling_log(self, filepath: str):
        """
        将调度日志保存到CSV文件
        
        Args:
            filepath: 保存路径 (应为.csv扩展名)
        """
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入表头
            if self.use_avis:
                headers = ['time', 'user_id', 'channel_capacity', 'allocated_bitrate', 
                          'enforced_bitrate', 'allocated_resources', 'max_rate', 
                          'min_rate', 'tokens', 'bucket_capacity', 'was_throttled']
            else:
                headers = ['time', 'user_id', 'channel_capacity', 'estimated_throughput', 
                          'selected_bitrate']
            writer.writerow(headers)
            
            # 写入数据
            for round_log in self.scheduling_log:
                time = round_log['time']
                for user_id, user_log in round_log['users'].items():
                    if self.use_avis:
                        row = [
                            time,
                            user_id,
                            round(user_log['channel_capacity'], 2),
                            user_log.get('allocated_bitrate', 0),
                            user_log['current_bitrate'],
                            round(user_log.get('allocated_resources', 0), 2),
                            round(user_log.get('max_rate', 0), 2),
                            round(user_log.get('min_rate', 0), 2),
                            round(user_log.get('tokens', 0), 2),
                            round(user_log.get('bucket_capacity', 0), 2),
                            1 if user_log.get('was_throttled', False) else 0
                        ]
                    else:
                        row = [
                            time,
                            user_id,
                            round(user_log['channel_capacity'], 2),
                            round(user_log.get('estimated_throughput', 0), 2),
                            user_log['current_bitrate']
                        ]
                    writer.writerow(row)
    
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
