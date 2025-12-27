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
        
        # 动态规划求解多选择背包问题（论文Algorithm 1）
        # dp[i][t] = 前i个用户使用至多t个资源块的最大效用
        allocation_result = self._solve_multi_choice_knapsack(
            users, utility_matrix, resources_per_bitrate
        )
        
        return allocation_result
    
    def _solve_multi_choice_knapsack(self, users: List[User], 
                                     utility_matrix: np.ndarray,
                                     resources_per_bitrate: np.ndarray) -> AllocationResult:
        """
        多选择背包问题动态规划求解（论文Algorithm 1）
        
        状态定义: dp[i][t] = 前i个用户使用至多t个资源块的最大效用
        状态转移: dp[i][t] = max_j { dp[i-1][t - c_ij] + u_ij }
        
        Args:
            users: 用户列表
            utility_matrix: 效用矩阵 [n_users, n_bitrates]
            resources_per_bitrate: 资源需求矩阵 [n_users, n_bitrates]
        
        Returns:
            最优分配结果
        """
        n_users = len(users)
        n_bitrates = len(BITRATE_LEVELS)
        T = self.total_resources
        
        # 初始化DP表: dp[i][t] = 前i个用户使用至多t资源的最大效用
        # 使用-inf表示不可达状态
        dp = np.full((n_users + 1, T + 1), -np.inf)
        dp[0, :] = 0  # 0个用户，任意资源，效用为0
        
        # 记录选择路径: choice[i][t] = (j, prev_t)
        # j: 用户i选择的码率索引; prev_t: 上一个状态的资源数
        choice = {}
        
        # 动态规划填表
        for i in range(1, n_users + 1):
            user_idx = i - 1
            for t in range(T + 1):
                # 遍历用户i-1的所有码率选项j
                for j in range(n_bitrates):
                    u_ij = utility_matrix[user_idx, j]
                    c_ij = int(resources_per_bitrate[user_idx, j])
                    
                    # 检查资源是否足够
                    if c_ij <= t:
                        prev_t = t - c_ij
                        new_utility = dp[i-1, prev_t] + u_ij
                        
                        # 更新最优解
                        if new_utility > dp[i, t]:
                            dp[i, t] = new_utility
                            choice[(i, t)] = (j, prev_t)
        
        # 回溯找到最优解
        allocation_result = AllocationResult()
        current_t = T
        
        # 从最后一个用户开始回溯
        for i in range(n_users, 0, -1):
            if (i, current_t) in choice:
                j, prev_t = choice[(i, current_t)]
                user_idx = i - 1
                user_id = users[user_idx].user_id
                
                # 记录分配结果
                allocation_result.user_bitrates[user_id] = BITRATE_LEVELS[j]
                allocation_result.user_allocations[user_id] = int(resources_per_bitrate[user_idx, j])
                allocation_result.total_resources_used += int(resources_per_bitrate[user_idx, j])
                allocation_result.objective_value += utility_matrix[user_idx, j]
                
                current_t = prev_t
        
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
                
                # 用户的信道容量 C_i (kbps)
                C_i = channel_capacities.get(user.user_id, 2000)
                
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
                
                # 计算资源成本梯度: d(c_i)/d(r_i) ≈ 1 / C_i
                # 论文公式: c_i = ceil(r_i / C_i)，近似为连续时 dc_i/dr_i = 1/C_i
                dc_dr = 1.0 / C_i if C_i > 0 else 1.0
                
                # 梯度上升更新: r_i += learning_rate * (du/dr - alpha * df/dr - lambda * dc/dr)
                gradient = du_dr - self.alpha * df_dr - lambda_param * dc_dr
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
        
        # 量化到离散码率（论文方法：向下取整 + 贪心升级）
        allocation_result = self._quantize_and_upgrade(
            users, bitrates, channel_capacities
        )
        
        allocation_result.total_resources_used = sum(allocation_result.user_allocations.values())
        return allocation_result
    
    def _quantize_and_upgrade(self, users: List[User], 
                             continuous_bitrates: np.ndarray,
                             channel_capacities: Dict[int, float]) -> AllocationResult:
        """
        量化连续码率到离散值（论文方法：向下取整 + 贪心升级）
        
        步骤:
        1. 所有用户向下取整到最近的离散码率
        2. 计算剩余资源
        3. 贪心地为某些用户升级到下一档码率（选择性价比最高的）
        
        Args:
            users: 用户列表
            continuous_bitrates: 连续优化得到的码率 [n_users]
            channel_capacities: 信道容量字典
        
        Returns:
            离散化后的分配结果
        """
        allocation_result = AllocationResult()
        n_users = len(users)
        
        # 步骤1: 向下取整
        floor_indices = []
        for i, user in enumerate(users):
            r_i = continuous_bitrates[i]
            
            # 找到不超过r_i的最大离散码率索引
            floor_idx = 0
            for j, bitrate in enumerate(BITRATE_LEVELS):
                if bitrate <= r_i:
                    floor_idx = j
                else:
                    break
            
            floor_indices.append(floor_idx)
            
            # 分配向下取整的码率
            floor_bitrate = BITRATE_LEVELS[floor_idx]
            resources_needed = self._compute_resources_for_bitrate(
                floor_bitrate, channel_capacities.get(user.user_id, 2000)
            )
            
            allocation_result.user_bitrates[user.user_id] = floor_bitrate
            allocation_result.user_allocations[user.user_id] = resources_needed
        
        # 步骤2: 计算剩余资源
        used_resources = sum(allocation_result.user_allocations.values())
        remaining_resources = self.total_resources - used_resources
        
        # 步骤3: 贪心升级（选择性价比最高的用户）
        # 性价比 = (升级后效用增益) / (额外资源消耗)
        upgrade_candidates = []
        
        for i, user in enumerate(users):
            floor_idx = floor_indices[i]
            
            # 检查是否可以升级
            if floor_idx + 1 < len(BITRATE_LEVELS):
                current_bitrate = BITRATE_LEVELS[floor_idx]
                next_bitrate = BITRATE_LEVELS[floor_idx + 1]
                
                # 计算效用增益
                P_i = 1.0
                S_i = user.get_bitrate_switches(window_size=BITRATE_SWITCH_WINDOW)
                r_i_star = float(user.current_bitrate)
                
                u_current = P_i * np.log(current_bitrate) if current_bitrate > 0 else 0
                f_current = (np.sqrt((current_bitrate - r_i_star)**2) + 1) * S_i
                
                u_next = P_i * np.log(next_bitrate)
                f_next = (np.sqrt((next_bitrate - r_i_star)**2) + 1) * S_i
                
                utility_gain = (u_next - self.alpha * f_next) - (u_current - self.alpha * f_current)
                
                # 计算资源增量
                C_i = channel_capacities.get(user.user_id, 2000)
                resources_current = self._compute_resources_for_bitrate(current_bitrate, C_i)
                resources_next = self._compute_resources_for_bitrate(next_bitrate, C_i)
                resource_cost = resources_next - resources_current
                
                if resource_cost > 0 and utility_gain > 0:
                    cost_efficiency = utility_gain / resource_cost # 性价比=增益/资源块成本
                    upgrade_candidates.append({
                        'user_id': user.user_id,
                        'user_idx': i,
                        'next_bitrate': next_bitrate,
                        'resource_cost': resource_cost,
                        'utility_gain': utility_gain,
                        'cost_efficiency': cost_efficiency
                    })
        
        # 按性价比排序，贪心升级
        upgrade_candidates.sort(key=lambda x: x['cost_efficiency'], reverse=True)
        
        for candidate in upgrade_candidates:
            if candidate['resource_cost'] <= remaining_resources:
                user_id = candidate['user_id']
                
                # 执行升级
                old_resources = allocation_result.user_allocations[user_id]
                allocation_result.user_bitrates[user_id] = candidate['next_bitrate']
                allocation_result.user_allocations[user_id] += candidate['resource_cost']
                
                remaining_resources -= candidate['resource_cost']
                allocation_result.objective_value += candidate['utility_gain']
        
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
