"""
AVIS (Adaptive Video Scheduling) 仿真主程序

复现论文: A Scheduling Framework for Adaptive Video Delivery over Cellular Networks
论文作者: Jiasi Chen et al., Princeton University & NEC Labs America

功能:
1. 实现AVIS调度器的Allocator和Enforcer模块
2. 对比AVIS与无调度(NO-AVIS)方案
3. 评估不同alpha参数对性能的影响
4. 计算公平性指数、码率切换频率、资源利用率等指标
5. 生成可视化结果报告
"""

import os
import sys
import numpy as np
from typing import List, Dict

from simulator import SimulationEngine
from metrics import PerformanceMetrics, print_performance_summary
from visualization import (
    plot_bitrate_comparison, plot_fairness_over_time, 
    plot_bitrate_switches, plot_metrics_comparison_bar,
    create_summary_report
)
from config import ALPHA_VALUES, SIMULATION_TIME


def run_single_simulation(use_avis: bool, alpha: float = None) -> Dict:
    """
    运行单次仿真
    
    Args:
        use_avis: 是否使用AVIS
        alpha: 如果使用AVIS，则为惩罚函数参数
    
    Returns:
        仿真结果字典
    """
    mode_str = f"AVIS (α={alpha})" if use_avis else "NO-AVIS"
    print(f"\n启动仿真: {mode_str}")
    print(f"  仿真时长: {SIMULATION_TIME}秒")
    
    engine = SimulationEngine(use_avis=use_avis, alpha=alpha if use_avis else 0)
    results = engine.run_simulation(duration=SIMULATION_TIME)
    
    print(f"  仿真完成!")
    
    return results


def main():
    """主程序"""
    print("\n" + "="*80)
    print("AVIS自适应视频流调度算法仿真")
    print("="*80)
    print("\n论文: A Scheduling Framework for Adaptive Video Delivery over Cellular Networks")
    print("作者: Jiasi Chen, Rajesh Mahindra, Mohammad A. Khojastepour, Sampath Rangarajan, Mung Chiang")
    
    # 创建输出目录
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)
    
    # =========================================================================
    # 第一阶段: 对于每个alpha值，对比AVIS与NO-AVIS
    # =========================================================================
    print("\n" + "="*80)
    print("第一阶段: 不同α参数下的对比实验")
    print("="*80)
    
    avis_results_by_alpha = {}
    no_avis_results = None  # NO-AVIS只需运行一次
    
    for alpha in ALPHA_VALUES:
        print(f"\n【测试参数集 α={alpha}】")
        
        # 运行AVIS
        avis_results = run_single_simulation(use_avis=True, alpha=alpha)
        avis_results_by_alpha[alpha] = avis_results
        
        # 第一次运行时，也运行NO-AVIS基线
        if no_avis_results is None:
            no_avis_results = run_single_simulation(use_avis=False, alpha=None)
        
        # 打印对比
        print_performance_summary(avis_results, no_avis_results, alpha)
    
    # =========================================================================
    # 第二阶段: 生成可视化结果
    # =========================================================================
    print("\n" + "="*80)
    print("第二阶段: 生成可视化结果")
    print("="*80)
    
    for alpha in ALPHA_VALUES:
        print(f"\n生成 α={alpha} 的图表...")
        
        avis_results = avis_results_by_alpha[alpha]
        
        # 生成对比图
        plot_bitrate_comparison(avis_results, no_avis_results, alpha, output_dir)
        print(f"  ✓ 码率对比图: bitrate_comparison_alpha_{alpha}.png")
        
        # 生成公平性随时间变化图
        plot_fairness_over_time(avis_results, no_avis_results, alpha, output_dir)
        print(f"  ✓ 公平性时间序列: fairness_over_time_alpha_{alpha}.png")
        
        # 生成码率切换对比图
        plot_bitrate_switches(avis_results, no_avis_results, alpha, output_dir)
        print(f"  ✓ 码率切换对比: bitrate_switches_alpha_{alpha}.png")
    
    # 生成α参数影响分析图
    all_avis_results = [avis_results_by_alpha[alpha] for alpha in ALPHA_VALUES]
    for result, alpha in zip(all_avis_results, ALPHA_VALUES):
        result['alpha'] = alpha
    
    plot_metrics_comparison_bar(all_avis_results, output_dir)
    print(f"\n  ✓ α参数影响分析: metrics_vs_alpha.png")
    
    # 生成汇总报告
    create_summary_report(all_avis_results, output_dir)
    print(f"  ✓ 汇总报告: summary_report.png")
    
    # =========================================================================
    # 第三阶段: 统计汇总
    # =========================================================================
    print("\n" + "="*80)
    print("第三阶段: 实验统计汇总")
    print("="*80)
    
    print("\n【ALPHA参数对AVIS性能的影响】")
    print("-" * 80)
    print(f"{'α值':<10} {'公平性':<12} {'码率切换':<15} {'平均码率':<15} {'稳定性':<12}")
    print("-" * 80)
    
    for alpha in ALPHA_VALUES:
        avis_results = avis_results_by_alpha[alpha]
        bitrates = avis_results['history']['bitrates']
        
        jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
        switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates).values())
        avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(bitrates).values()))
        stability = np.mean(list(PerformanceMetrics.calculate_bitrate_stability(bitrates).values()))
        
        print(f"{alpha:<10.1f} {jain:<12.4f} {switches:<15d} {avg_br:<15.0f} {stability:<12.0f}")
    
    # =========================================================================
    # 最终总结
    # =========================================================================
    print("\n" + "="*80)
    print("仿真完成! 所有结果已保存到 results/ 目录")
    print("="*80)
    
    print("\n【关键发现】")
    print("-" * 80)
    
    # 找到最优的alpha值（基于公平性和切换频率的权衡）
    best_alpha = ALPHA_VALUES[0]
    best_score = float('inf')
    
    for alpha in ALPHA_VALUES:
        avis_results = avis_results_by_alpha[alpha]
        bitrates = avis_results['history']['bitrates']
        
        jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
        switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates).values())
        
        # 综合评分：最大化公平性，最小化切换（切换数权重更大）
        score = -jain + switches / 10
        
        if score < best_score:
            best_score = score
            best_alpha = alpha
    
    best_avis = avis_results_by_alpha[best_alpha]
    best_bitrates = best_avis['history']['bitrates']
    best_jain = PerformanceMetrics.calculate_jain_fairness_index(best_bitrates)
    
    no_avis_bitrates = no_avis_results['history']['bitrates']
    no_avis_jain = PerformanceMetrics.calculate_jain_fairness_index(no_avis_bitrates)
    
    print(f"\n1. 最优参数: α={best_alpha}")
    print(f"   - 实现公平性提升: {(best_jain - no_avis_jain)*100:+.1f}%")
    print(f"   - 达到公平性指数: {best_jain:.4f}")
    
    best_switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(best_bitrates).values())
    no_avis_switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(no_avis_bitrates).values())
    print(f"\n2. 码率稳定性改进: {no_avis_switches - best_switches} 次切换减少 ({(1-best_switches/max(no_avis_switches,1))*100:.1f}%)")
    
    best_avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(best_bitrates).values()))
    no_avis_avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(no_avis_bitrates).values()))
    print(f"\n3. 吞吐量: AVIS={best_avg_br:.0f}kbps, NO-AVIS={no_avis_avg_br:.0f}kbps")
    
    print("\n【生成的文件】")
    print("-" * 80)
    for file in sorted(os.listdir(output_dir)):
        if file.endswith('.png'):
            print(f"  ✓ {file}")

if __name__ == '__main__':
    main()
