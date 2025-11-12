"""
性能评估指标计算模块
"""
import numpy as np
from typing import Dict, List


class PerformanceMetrics:
    """性能指标计算"""
    
    @staticmethod
    def calculate_jain_fairness_index(bitrate_histories: Dict[int, List[float]], 
                                      window_size: int = 30) -> float:
        """
        计算Jain公平性指数
        
        公式: J = (sum(F_i))^2 / (N * sum(F_i^2))
        其中 F_i = r_i / C_i
             r_i: 用户i分配的码率
             C_i: 用户i的信道容量
        
        Args:
            bitrate_histories: user_id -> [码率序列]
            window_size: 计算窗口大小（最近window_size个时刻）
        
        Returns:
            Jain公平性指数 (0-1, 1表示完全公平)
        """
        if not bitrate_histories or len(bitrate_histories) == 0:
            return 0
        
        N = len(bitrate_histories)
        fairness_metrics = []
        
        for user_id, history in bitrate_histories.items():
            if len(history) == 0:
                continue
            
            # 使用最后window_size个数据点
            recent_history = history[-window_size:] if len(history) >= window_size else history
            avg_bitrate = np.mean(recent_history)
            fairness_metrics.append(avg_bitrate)
        
        if len(fairness_metrics) == 0:
            return 0
        
        fairness_metrics = np.array(fairness_metrics)
        
        # 正规化为相对公平性（相对于平均值）
        mean_bitrate = np.mean(fairness_metrics)
        if mean_bitrate == 0:
            return 0
        
        normalized_metrics = fairness_metrics / mean_bitrate
        
        # 计算Jain指数
        sum_metrics = np.sum(normalized_metrics)
        sum_metrics_sq = np.sum(normalized_metrics ** 2)
        
        jain_index = (sum_metrics ** 2) / (len(normalized_metrics) * sum_metrics_sq)
        return float(np.clip(jain_index, 0, 1))
    
    @staticmethod
    def calculate_bitrate_switch_frequency(bitrate_histories: Dict[int, List[float]]) -> Dict[int, int]:
        """
        计算每个用户的码率切换频率
        
        Args:
            bitrate_histories: user_id -> [码率序列]
        
        Returns:
            user_id -> 切换次数
        """
        switch_counts = {}
        
        for user_id, history in bitrate_histories.items():
            if len(history) < 2:
                switch_counts[user_id] = 0
                continue
            
            switches = 0
            for i in range(1, len(history)):
                if history[i] != history[i-1]:
                    switches += 1
            
            switch_counts[user_id] = switches
        
        return switch_counts
    
    @staticmethod
    def calculate_resource_utilization(allocated_resources: Dict[int, List[int]], 
                                      total_resources: int = 100) -> float:
        """
        计算资源利用率
        
        利用率 = 平均分配的资源块数 / 总资源块数
        
        Args:
            allocated_resources: user_id -> [分配资源序列]
            total_resources: 总资源块数
        
        Returns:
            资源利用率 (0-1)
        """
        if not allocated_resources:
            return 0
        
        all_allocations = []
        for resources_list in allocated_resources.values():
            if resources_list:
                all_allocations.extend(resources_list)
        
        if not all_allocations:
            return 0
        
        avg_allocation = np.mean(all_allocations)
        utilization = avg_allocation / total_resources
        
        return float(np.clip(utilization, 0, 1))
    
    @staticmethod
    def calculate_avg_bitrate(bitrate_histories: Dict[int, List[float]]) -> Dict[int, float]:
        """
        计算每个用户的平均码率
        
        Args:
            bitrate_histories: user_id -> [码率序列]
        
        Returns:
            user_id -> 平均码率
        """
        avg_bitrates = {}
        
        for user_id, history in bitrate_histories.items():
            if history:
                avg_bitrates[user_id] = float(np.mean(history))
            else:
                avg_bitrates[user_id] = 0
        
        return avg_bitrates
    
    @staticmethod
    def calculate_bitrate_stability(bitrate_histories: Dict[int, List[float]]) -> Dict[int, float]:
        """
        计算码率稳定性（低方差表示更稳定）
        
        Args:
            bitrate_histories: user_id -> [码率序列]
        
        Returns:
            user_id -> 码率标准差
        """
        stability = {}
        
        for user_id, history in bitrate_histories.items():
            if history:
                stability[user_id] = float(np.std(history))
            else:
                stability[user_id] = 0
        
        return stability


def print_performance_summary(results_avis: Dict, results_no_avis: Dict, alpha: float):
    """
    打印性能对比总结
    
    Args:
        results_avis: AVIS方案的仿真结果
        results_no_avis: NO-AVIS方案的仿真结果
        alpha: 使用的alpha参数
    """
    print("\n" + "="*80)
    print(f"性能评估总结 (alpha={alpha})")
    print("="*80)
    
    # 提取数据
    avis_bitrates = results_avis['history']['bitrates']
    avis_resources = results_avis['history']['allocated_resources']
    
    no_avis_bitrates = results_no_avis['history']['bitrates']
    no_avis_resources = results_no_avis['history']['allocated_resources']
    
    # 计算指标
    print("\n【公平性指数 (Jain's Fairness Index)】")
    avis_jain = PerformanceMetrics.calculate_jain_fairness_index(avis_bitrates)
    no_avis_jain = PerformanceMetrics.calculate_jain_fairness_index(no_avis_bitrates)
    print(f"  AVIS:    {avis_jain:.4f}")
    print(f"  NO-AVIS: {no_avis_jain:.4f}")
    print(f"  改进:    {(avis_jain - no_avis_jain):.4f} ({(avis_jain/max(no_avis_jain, 0.001)-1)*100:+.1f}%)")
    
    # 码率切换频率
    print("\n【码率切换频率 (总切换次数)】")
    avis_switches = PerformanceMetrics.calculate_bitrate_switch_frequency(avis_bitrates)
    no_avis_switches = PerformanceMetrics.calculate_bitrate_switch_frequency(no_avis_bitrates)
    
    avis_total_switches = sum(avis_switches.values())
    no_avis_total_switches = sum(no_avis_switches.values())
    
    print(f"  AVIS 总切换: {avis_total_switches} 次")
    for uid, count in sorted(avis_switches.items()):
        print(f"    用户{uid}: {count} 次")
    
    print(f"  NO-AVIS 总切换: {no_avis_total_switches} 次")
    for uid, count in sorted(no_avis_switches.items()):
        print(f"    用户{uid}: {count} 次")
    
    print(f"  改进: {(no_avis_total_switches - avis_total_switches)} 次减少 ({(1-avis_total_switches/max(no_avis_total_switches, 1))*100:+.1f}%)")
    
    # 资源利用率
    print("\n【资源利用率】")
    avis_util = PerformanceMetrics.calculate_resource_utilization(avis_resources)
    no_avis_util = PerformanceMetrics.calculate_resource_utilization(no_avis_resources)
    print(f"  AVIS:    {avis_util:.2%}")
    print(f"  NO-AVIS: {no_avis_util:.2%}")
    print(f"  改进:    {(avis_util - no_avis_util):+.2%}")
    
    # 平均码率
    print("\n【平均码率 (kbps)】")
    avis_avg_br = PerformanceMetrics.calculate_avg_bitrate(avis_bitrates)
    no_avis_avg_br = PerformanceMetrics.calculate_avg_bitrate(no_avis_bitrates)
    
    avis_overall_avg = np.mean(list(avis_avg_br.values()))
    no_avis_overall_avg = np.mean(list(no_avis_avg_br.values()))
    
    print(f"  AVIS:    {avis_overall_avg:.0f} kbps")
    for uid, avg in sorted(avis_avg_br.items()):
        print(f"    用户{uid}: {avg:.0f} kbps")
    
    print(f"  NO-AVIS: {no_avis_overall_avg:.0f} kbps")
    for uid, avg in sorted(no_avis_avg_br.items()):
        print(f"    用户{uid}: {avg:.0f} kbps")
    
    # 码率稳定性
    print("\n【码率稳定性 (标准差, 越低越稳定)】")
    avis_stability = PerformanceMetrics.calculate_bitrate_stability(avis_bitrates)
    no_avis_stability = PerformanceMetrics.calculate_bitrate_stability(no_avis_bitrates)
    
    avis_overall_std = np.mean(list(avis_stability.values()))
    no_avis_overall_std = np.mean(list(no_avis_stability.values()))
    
    print(f"  AVIS:    {avis_overall_std:.0f} kbps")
    print(f"  NO-AVIS: {no_avis_overall_std:.0f} kbps")
    print(f"  改进:    {(no_avis_overall_std - avis_overall_std):.0f} kbps 更稳定")
    
    print("="*80 + "\n")
