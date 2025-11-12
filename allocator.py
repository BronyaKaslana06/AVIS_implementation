"""
AVIS Allocator - 资源分配优化模块
实现离散优化和连续优化模型

优化问题（离散版本，论文Problem 1）：
  目标函数: max sum_i sum_j (u_ij - alpha*f_ij) * x_ij
  其中:
    u_ij = P_i * log(r_ij)  (效用 = 优先级 × 码率的对数)
    f_ij = (|j - j*| + 1) * S_i  (惩罚 = 码率索引差 × 历史切换次数)
    
优化问题（连续版本，论文Problem 2）：
  目标函数: max sum_i (u_i - alpha*f_i)
  其中:
    u_i = P_i * log(r_i)
    f_i = (sqrt((r_i - r_i*)^2) + 1) * S_i
"""
import numpy as np
from typing import List, Dict, Tuple
from models import User, AllocationResult
from config import TOTAL_RESOURCE_BLOCKS, BITRATE_LEVELS, BITRATE_SWITCH_WINDOW


class Allocator:
    """资源分配器 - 基于多选择背包问题的优化"""
    
    def __init__(self, alpha: float = 0.5):
        """
        初始化Allocator
        
        Args:
            alpha: 惩罚函数权重参数，控制码率切换的惩罚
                   更大的alpha意味着对码率切换的惩罚更大
        """
        self.alpha = alpha
        self.total_resources = TOTAL_RESOURCE_BLOCKS
        
    def discrete_optimization(self, users: List[User], 
                             channel_capacities: Dict[int, float]) -> AllocationResult:
        """
        离散优化模型 - 多选择背包问题
        
        目标函数: max sum_i sum_j (u_ij - alpha*f_ij) * x_ij
        其中:
          - u_ij: 用户i选择码率j的效用
          - f_ij: 用户i从当前码率切换到码率j的惩罚（切换成本）
          - x_ij: 二进制决策变量（用户i是否选择码率j）
          - alpha: 惩罚函数权重
        
        约束条件:
          1. sum_i r_ij * (resources_per_kbps_ij) <= R_total (资源块总数限制)
          2. sum_j x_ij <= 1 for all i (每个用户最多选择一个码率)
        """
        n_users = len(users)
        n_bitrates = len(BITRATE_LEVELS)
        
        # 计算每种码率对应的资源块数 (模拟物理层编码效率)
        # 更高的码率需要更多资源块
        resources_per_bitrate = self._compute_resource_requirements(users, channel_capacities)
        
        # 构建效用矩阵: u_ij - alpha * f_ij
        # 论文公式:
        # u_ij = P_i * log(r_ij)  (效用函数，公式源自论文Section 3)
        # f_ij = (|j - j*| + 1) * S_i  (惩罚函数，公式7)
        # 其中 S_i 是用户i在过去W时间内的码率切换次数
        utility_matrix = np.zeros((n_users, n_bitrates))
        
        for i, user in enumerate(users):
            # 用户优先级 P_i (论文默认为1.0，表示所有用户平等)
            P_i = user.priority if hasattr(user, 'priority') else 1.0
            
            # 历史切换次数 S_i (过去W秒内的切换)
            S_i = user.get_bitrate_switches(window_size=BITRATE_SWITCH_WINDOW)
            
            # 当前码率对应的索引 j*
            if user.current_bitrate in BITRATE_LEVELS:
                j_star = BITRATE_LEVELS.index(user.current_bitrate)
            else:
                j_star = 0  # 默认最低码率索引
            
            for j, bitrate in enumerate(BITRATE_LEVELS):
                # 效用函数: u_ij = P_i * log(r_ij)
                # 避免log(0)，码率为0时效用为负无穷（实际不会选择）
                if bitrate > 0:
                    u_ij = P_i * np.log(bitrate)
                else:
                    u_ij = -np.inf
                
                # 惩罚函数: f_ij = (|j - j*| + 1) * S_i
                # 注意：即使不切换(j == j*)，论文中仍有基础惩罚1*S_i
                f_ij = (abs(j - j_star) + 1) * S_i
                
                utility_matrix[i, j] = u_ij - self.alpha * f_ij
        
        # 贪心算法求解（近似解）
        # 简单策略：对每个用户独立选择效用最大的码率，同时满足总资源约束
        allocation_result = AllocationResult()
        
        # 为每个用户计算"效用/资源"比率，按贪心方式分配
        user_options = []  # (user_idx, bitrate_idx, utility, resource_blocks)
        
        for i in range(n_users):
            best_j = np.argmax(utility_matrix[i, :])
            best_utility = utility_matrix[i, best_j]
            best_bitrate = BITRATE_LEVELS[best_j]
            resources_needed = resources_per_bitrate[i][best_j]
            
            user_options.append({
                'user_idx': i,
                'user_id': users[i].user_id,
                'bitrate_idx': best_j,
                'bitrate': best_bitrate,
                'utility': best_utility,
                'resources': resources_needed
            })
        
        # 按效用贪心分配资源
        user_options_sorted = sorted(user_options, key=lambda x: x['utility'], reverse=True)
        
        resources_remaining = self.total_resources
        allocated_users = set()
        
        for option in user_options_sorted:
            if option['resources'] <= resources_remaining:
                allocation_result.user_allocations[option['user_id']] = option['resources']
                allocation_result.user_bitrates[option['user_id']] = option['bitrate']
                allocation_result.total_resources_used += option['resources']
                resources_remaining -= option['resources']
                allocated_users.add(option['user_idx'])
                allocation_result.objective_value += option['utility']
        
        return allocation_result
    
    def continuous_optimization(self, users: List[User], 
                               channel_capacities: Dict[int, float]) -> AllocationResult:
        """
        连续优化模型 - 放松整数约束（论文Problem 2）
        
        目标函数: max sum_i (u_i - alpha*f_i)
        其中:
          u_i = P_i * log(r_i)  (效用函数，公式11)
          f_i = (sqrt((r_i - r_i*)^2) + 1) * S_i  (惩罚函数，公式12)
        
        约束条件: sum_i c_i <= R_total (总资源限制)
        
        使用拉格朗日对偶方法求解（论文Section 3.1.2）
        """
        n_users = len(users)
        
        # 初始化码率（连续变量）
        bitrates = np.array([float(user.current_bitrate) for user in users])
        
        # 拉格朗日乘子（资源约束的对偶变量）
        lambda_param = 1.0
        learning_rate = 0.1
        max_iterations = 100
        
        for iteration in range(max_iterations):
            # 对每个用户优化其码率（基于梯度上升）
            for i, user in enumerate(users):
                # 用户优先级 P_i
                P_i = user.priority if hasattr(user, 'priority') else 1.0
                
                # 历史切换次数 S_i
                S_i = user.get_bitrate_switches(window_size=BITRATE_SWITCH_WINDOW)
                
                # 当前码率 r_i*
                r_i_star = float(user.current_bitrate)
                
                # 当前迭代的码率 r_i
                r_i = bitrates[i]
                
                # 计算效用函数的梯度: d(u_i)/d(r_i) = P_i / r_i
                if r_i > 0:
                    du_dr = P_i / r_i
                else:
                    du_dr = 0
                
                # 计算惩罚函数的梯度: d(f_i)/d(r_i) = (r_i - r_i*) / sqrt((r_i - r_i*)^2) * S_i
                r_diff = r_i - r_i_star
                if abs(r_diff) > 1e-6:
                    df_dr = (r_diff / np.sqrt(r_diff**2)) * S_i
                else:
                    df_dr = 0
                
                # 梯度上升更新: r_i += learning_rate * (du/dr - alpha * df/dr - lambda * resource_cost)
                # resource_cost = 物理层资源消耗的近似梯度（简化为常数1）
                gradient = du_dr - self.alpha * df_dr - lambda_param
                bitrates[i] += learning_rate * gradient
                
                # 限制码率范围
                bitrates[i] = np.clip(bitrates[i], min(BITRATE_LEVELS), max(BITRATE_LEVELS))
            
            # 更新拉格朗日乘子（确保资源约束满足）
            # 简化：假设每kbps需要固定资源
            total_resources_needed = sum([self._compute_resources_for_bitrate(
                bitrates[i], channel_capacities.get(users[i].user_id, 2000)
            ) for i in range(n_users)])
            
            resource_deficit = total_resources_needed - self.total_resources
            lambda_param += 0.01 * resource_deficit
            lambda_param = max(lambda_param, 0.001)
        
        # 转换回离散码率并分配资源
        allocation_result = AllocationResult()
        total_resources = 0
        
        for i, user in enumerate(users):
            # 找最接近的离散码率
            closest_bitrate_idx = np.argmin(np.abs(np.array(BITRATE_LEVELS) - bitrates[i]))
            closest_bitrate = BITRATE_LEVELS[closest_bitrate_idx]
            
            resources_needed = self._compute_resources_for_bitrate(
                closest_bitrate, channel_capacities.get(user.user_id, 2000)
            )
            
            if total_resources + resources_needed <= self.total_resources:
                allocation_result.user_allocations[user.user_id] = resources_needed
                allocation_result.user_bitrates[user.user_id] = closest_bitrate
                total_resources += resources_needed
                
                # 计算目标函数值
                P_i = 1.0
                S_i = user.get_bitrate_switches(window_size=BITRATE_SWITCH_WINDOW)
                u_i = P_i * np.log(closest_bitrate) if closest_bitrate > 0 else 0
                r_i_star = float(user.current_bitrate)
                f_i = (np.sqrt((closest_bitrate - r_i_star)**2) + 1) * S_i
                allocation_result.objective_value += (u_i - self.alpha * f_i)
        
        allocation_result.total_resources_used = total_resources
        return allocation_result
    
    def _compute_resource_requirements(self, users: List[User], 
                                      channel_capacities: Dict[int, float]) -> np.ndarray:
        """计算每个用户选择每种码率所需的资源块数"""
        resources = np.zeros((len(users), len(BITRATE_LEVELS)))
        
        for i, user in enumerate(users):
            channel_cap = channel_capacities.get(user.user_id, 2000)
            
            for j, bitrate in enumerate(BITRATE_LEVELS):
                # 资源块数 = ceil(bitrate / channel_capacity) * scaling_factor
                # 码率越高相对于信道容量，需要的资源块越多
                if bitrate <= channel_cap:
                    # 信道足以支持此码率
                    resources[i, j] = max(1, int(np.ceil(bitrate / channel_cap * 10)))
                else:
                    # 信道不足以支持此码率，分配更多资源
                    resources[i, j] = int(np.ceil(bitrate / channel_cap * 15))
        
        return resources
    
    def _compute_resources_for_bitrate(self, bitrate: int, channel_capacity: float) -> int:
        """计算给定码率所需的资源块数"""
        if bitrate <= channel_capacity:
            return max(1, int(np.ceil(bitrate / channel_capacity * 10)))
        else:
            return int(np.ceil(bitrate / channel_capacity * 15))
