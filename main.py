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
    create_summary_report, plot_resource_utilization_comparison
)
from config import ALPHA_VALUES, SIMULATION_TIME, TOTAL_RESOURCE_BLOCKS


def run_single_simulation(use_avis: bool, alpha: float = None, optimization_type: str = 'continuous') -> Dict:
    """
    运行单次仿真
    
    Args:
        use_avis: 是否使用AVIS
        alpha: 如果使用AVIS，则为惩罚函数参数
        optimization_type: 优化方法类型 ('discrete' 或 'continuous')
    
    Returns:
        仿真结果字典
    """
    if use_avis:
        mode_str = f"AVIS-{optimization_type.upper()} (α={alpha})"
    else:
        mode_str = "NO-AVIS"
    print(f"\n启动仿真: {mode_str}")
    print(f"  仿真时长: {SIMULATION_TIME}秒")
    
    engine = SimulationEngine(
        use_avis=use_avis, 
        alpha=alpha if use_avis else 0,
        optimization_type=optimization_type
    )
    results = engine.run_simulation(duration=SIMULATION_TIME)
    
    print(f"  仿真完成!")
    
    return results


def main():
    """主程序"""
    print("\n" + "="*80)
    print("AVIS自适应视频流调度算法仿真")
    print("="*80)
    # print("\n论文: A Scheduling Framework for Adaptive Video Delivery over Cellular Networks")
    # print("作者: Jiasi Chen, Rajesh Mahindra, Mohammad A. Khojastepour, Sampath Rangarajan, Mung Chiang")
    
    # 创建输出目录
    output_dir_discrete = 'results_discrete'
    output_dir_continuous = 'results_continuous'
    os.makedirs(output_dir_discrete, exist_ok=True)
    os.makedirs(output_dir_continuous, exist_ok=True)
    
    # =========================================================================
    # 对比实验: 离散型AVIS vs 连续型AVIS vs NO-AVIS
    # =========================================================================
    print("\n" + "="*80)
    print("对比实验: 离散型 vs 连续型 vs NO-AVIS")
    print("="*80)
    
    # 运行NO-AVIS（只需一次）
    print("\n【基线方案】")
    no_avis_results = run_single_simulation(use_avis=False)
    
    # 针对每个alpha值，分别运行离散型和连续型
    discrete_results_by_alpha = {}
    continuous_results_by_alpha = {}
    
    for alpha in ALPHA_VALUES:
        print(f"\n【测试参数集 α={alpha}】")
        
        # 运行离散型AVIS
        discrete_results = run_single_simulation(use_avis=True, alpha=alpha, optimization_type='discrete')
        discrete_results_by_alpha[alpha] = discrete_results
        
        # 运行连续型AVIS
        continuous_results = run_single_simulation(use_avis=True, alpha=alpha, optimization_type='continuous')
        continuous_results_by_alpha[alpha] = continuous_results
        
        # 打印对比
        print("\n  【离散型AVIS vs NO-AVIS】")
        print_performance_summary(discrete_results, no_avis_results, alpha)
        
        print("\n  【连续型AVIS vs NO-AVIS】")
        print_performance_summary(continuous_results, no_avis_results, alpha)
    
    
    # =========================================================================
    # 第二阶段: 生成可视化结果
    # =========================================================================
    print("\n" + "="*80)
    print("第二阶段: 生成可视化结果")
    print("="*80)
    
    # 为离散型生成图表
    print("\n【离散型AVIS图表】")
    for alpha in ALPHA_VALUES:
        print(f"\n生成 α={alpha} 的图表...")
        discrete_results = discrete_results_by_alpha[alpha]
        
        plot_bitrate_comparison(discrete_results, no_avis_results, alpha, output_dir_discrete)
        print(f"  ✓ 码率对比图: bitrate_comparison_alpha_{alpha}.png")
        
        plot_fairness_over_time(discrete_results, no_avis_results, alpha, output_dir_discrete)
        print(f"  ✓ 公平性时间序列: fairness_over_time_alpha_{alpha}.png")
        
        plot_bitrate_switches(discrete_results, no_avis_results, alpha, output_dir_discrete)
        print(f"  ✓ 码率切换对比: bitrate_switches_alpha_{alpha}.png")
    
    all_discrete_results = [discrete_results_by_alpha[alpha] for alpha in ALPHA_VALUES]
    for result, alpha in zip(all_discrete_results, ALPHA_VALUES):
        result['alpha'] = alpha
    
    plot_metrics_comparison_bar(all_discrete_results, output_dir_discrete)
    print(f"\n  ✓ α参数影响分析: metrics_vs_alpha.png")
    
    # 用户数较多时不生成汇总报告图（太拥挤）
    # create_summary_report(all_discrete_results, output_dir_discrete)
    # print(f"  ✓ 汇总报告: summary_report.png")
    
    # 为连续型生成图表
    print("\n【连续型AVIS图表】")
    for alpha in ALPHA_VALUES:
        print(f"\n生成 α={alpha} 的图表...")
        continuous_results = continuous_results_by_alpha[alpha]
        
        plot_bitrate_comparison(continuous_results, no_avis_results, alpha, output_dir_continuous)
        print(f"  ✓ 码率对比图: bitrate_comparison_alpha_{alpha}.png")
        
        plot_fairness_over_time(continuous_results, no_avis_results, alpha, output_dir_continuous)
        print(f"  ✓ 公平性时间序列: fairness_over_time_alpha_{alpha}.png")
        
        plot_bitrate_switches(continuous_results, no_avis_results, alpha, output_dir_continuous)
        print(f"  ✓ 码率切换对比: bitrate_switches_alpha_{alpha}.png")
    
    all_continuous_results = [continuous_results_by_alpha[alpha] for alpha in ALPHA_VALUES]
    for result, alpha in zip(all_continuous_results, ALPHA_VALUES):
        result['alpha'] = alpha
    
    plot_metrics_comparison_bar(all_continuous_results, output_dir_continuous)
    print(f"\n  ✓ α参数影响分析: metrics_vs_alpha.png")
    
    # 用户数较多时不生成汇总报告图（太拥挤）
    # create_summary_report(all_continuous_results, output_dir_continuous)
    # print(f"  ✓ 汇总报告: summary_report.png")
    
    # 生成资源利用率对比图（同时保存在两个目录）
    print("\n【资源利用率对比图】")
    plot_resource_utilization_comparison(
        discrete_results_by_alpha,
        continuous_results_by_alpha,
        no_avis_results,
        ALPHA_VALUES,
        output_dir_discrete
    )
    plot_resource_utilization_comparison(
        discrete_results_by_alpha,
        continuous_results_by_alpha,
        no_avis_results,
        ALPHA_VALUES,
        output_dir_continuous
    )
    
    # =========================================================================
    # 第三阶段: 统计汇总与报告生成
    # =========================================================================
    print("\n" + "="*80)
    print("第三阶段: 实验统计汇总与报告生成")
    print("="*80)
    
    def generate_report_content(results_by_alpha, mode_name):
        """生成报告内容字符串"""
        lines = []
        lines.append(f"================================================================================")
        lines.append(f"AVIS仿真实验报告 - {mode_name}")
        lines.append(f"================================================================================")
        
        # 1. 参数影响分析
        lines.append(f"\n【ALPHA参数影响分析】")
        lines.append("-" * 80)
        lines.append(f"{'α值':<10} {'公平性':<12} {'码率切换':<15} {'平均码率':<15}")
        lines.append("-" * 80)
        
        best_alpha = ALPHA_VALUES[0]
        best_score = float('inf')
        
        for alpha in ALPHA_VALUES:
            results = results_by_alpha[alpha]
            bitrates = results['history']['bitrates']
            
            jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
            switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates).values())
            avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(bitrates).values()))
            
            lines.append(f"{alpha:<10.1f} {jain:<12.4f} {switches:<15d} {avg_br:<15.0f}")
            
            # 简单的评分逻辑：公平性越高越好，切换越少越好
            score = -jain + switches / 100
            if score < best_score:
                best_score = score
                best_alpha = alpha
        
        # 2. 最优配置 vs NO-AVIS
        best_results = results_by_alpha[best_alpha]
        best_bitrates = best_results['history']['bitrates']
        no_avis_bitrates = no_avis_results['history']['bitrates']
        
        best_jain = PerformanceMetrics.calculate_jain_fairness_index(best_bitrates)
        no_avis_jain = PerformanceMetrics.calculate_jain_fairness_index(no_avis_bitrates)
        
        best_switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(best_bitrates).values())
        no_avis_switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(no_avis_bitrates).values())
        
        best_util = PerformanceMetrics.calculate_resource_utilization(
            best_results['history']['allocated_resources'], 
            TOTAL_RESOURCE_BLOCKS
        )
        no_avis_util = PerformanceMetrics.calculate_resource_utilization(
            no_avis_results['history']['allocated_resources'], 
            TOTAL_RESOURCE_BLOCKS
        )
        
        lines.append(f"\n【最终结论 (基于最优参数 α={best_alpha})】")
        lines.append("-" * 80)
        lines.append(f"1. 公平性 (Jain's Index):")
        lines.append(f"   - NO-AVIS: {no_avis_jain:.4f}")
        lines.append(f"   - AVIS:    {best_jain:.4f}")
        lines.append(f"   - 提升:    {(best_jain - no_avis_jain)*100:+.1f}%")
        
        lines.append(f"\n2. 稳定性 (总码率切换次数):")
        lines.append(f"   - NO-AVIS: {no_avis_switches} 次")
        lines.append(f"   - AVIS:    {best_switches} 次")
        lines.append(f"   - 减少:    {no_avis_switches - best_switches} 次 ({(1 - best_switches/max(1, no_avis_switches))*100:.1f}%)")
        
        lines.append(f"\n3. 资源利用率:")
        lines.append(f"   - NO-AVIS: {no_avis_util*100:.1f}%")
        lines.append(f"   - AVIS:    {best_util*100:.1f}%")
        lines.append(f"   - 差异:    {(best_util - no_avis_util)*100:+.1f}%")
        
        return "\n".join(lines)

    # 生成并保存离散型报告
    discrete_report = generate_report_content(discrete_results_by_alpha, "离散型 (Discrete)")
    with open(os.path.join(output_dir_discrete, 'EXPERIMENT_REPORT.txt'), 'w') as f:
        f.write(discrete_report)
    print(f"\n已保存离散型实验报告: {os.path.join(output_dir_discrete, 'EXPERIMENT_REPORT.txt')}")
    print(discrete_report) # 同时也打印到控制台

    # 生成并保存连续型报告
    continuous_report = generate_report_content(continuous_results_by_alpha, "连续型 (Continuous)")
    with open(os.path.join(output_dir_continuous, 'EXPERIMENT_REPORT.txt'), 'w') as f:
        f.write(continuous_report)
    print(f"\n已保存连续型实验报告: {os.path.join(output_dir_continuous, 'EXPERIMENT_REPORT.txt')}")
    print(continuous_report) # 同时也打印到控制台
    
    # =========================================================================
    # 最终总结
    # =========================================================================
    print("\n" + "="*80)
    print("仿真完成!")
    print("="*80)
    print(f"  离散型结果: results_discrete/")
    print(f"  连续型结果: results_continuous/")
    
    print("\n【关键发现】")
    print("-" * 80)
    
    # 对比连续型最优配置
    best_alpha_cont = ALPHA_VALUES[0]
    best_score_cont = float('inf')
    
    for alpha in ALPHA_VALUES:
        continuous_results = continuous_results_by_alpha[alpha]
        bitrates = continuous_results['history']['bitrates']
        
        jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
        switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates).values())
        
        score = -jain + switches / 10
        
        if score < best_score_cont:
            best_score_cont = score
            best_alpha_cont = alpha
    
    best_continuous = continuous_results_by_alpha[best_alpha_cont]
    best_cont_bitrates = best_continuous['history']['bitrates']
    best_cont_jain = PerformanceMetrics.calculate_jain_fairness_index(best_cont_bitrates)
    
    # 对比离散型最优配置
    best_alpha_disc = ALPHA_VALUES[0]
    best_score_disc = float('inf')
    
    for alpha in ALPHA_VALUES:
        discrete_results = discrete_results_by_alpha[alpha]
        bitrates = discrete_results['history']['bitrates']
        
        jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
        switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates).values())
        
        score = -jain + switches / 10
        
        if score < best_score_disc:
            best_score_disc = score
            best_alpha_disc = alpha
    
    best_discrete = discrete_results_by_alpha[best_alpha_disc]
    best_disc_bitrates = best_discrete['history']['bitrates']
    best_disc_jain = PerformanceMetrics.calculate_jain_fairness_index(best_disc_bitrates)
    
    no_avis_bitrates = no_avis_results['history']['bitrates']
    no_avis_jain = PerformanceMetrics.calculate_jain_fairness_index(no_avis_bitrates)
    
    print(f"\n1. 连续型AVIS最优参数: α={best_alpha_cont}")
    print(f"   - 公平性提升: {(best_cont_jain - no_avis_jain)*100:+.1f}%")
    print(f"   - 公平性指数: {best_cont_jain:.4f}")
    
    print(f"\n2. 离散型AVIS最优参数: α={best_alpha_disc}")
    print(f"   - 公平性提升: {(best_disc_jain - no_avis_jain)*100:+.1f}%")
    print(f"   - 公平性指数: {best_disc_jain:.4f}")
    
    best_cont_switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(best_cont_bitrates).values())
    best_disc_switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(best_disc_bitrates).values())
    no_avis_switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(no_avis_bitrates).values())
    
    print(f"\n3. 码率切换对比:")
    print(f"   - NO-AVIS: {no_avis_switches} 次")
    print(f"   - 连续型AVIS: {best_cont_switches} 次 ({(1-best_cont_switches/max(no_avis_switches,1))*100:+.1f}%)")
    print(f"   - 离散型AVIS: {best_disc_switches} 次 ({(1-best_disc_switches/max(no_avis_switches,1))*100:+.1f}%)")
    
    best_cont_avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(best_cont_bitrates).values()))
    best_disc_avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(best_disc_bitrates).values()))
    no_avis_avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(no_avis_bitrates).values()))
    
    print(f"\n4. 吞吐量对比:")
    print(f"   - NO-AVIS: {no_avis_avg_br:.0f}kbps")
    print(f"   - 连续型AVIS: {best_cont_avg_br:.0f}kbps")
    print(f"   - 离散型AVIS: {best_disc_avg_br:.0f}kbps")
    
    print("\n【生成的文件】")
    print("-" * 80)
    print(f"离散型结果目录 (results_discrete/):")
    for file in sorted(os.listdir(output_dir_discrete)):
        if file.endswith('.png'):
            print(f"  ✓ {file}")
    
    print(f"\n连续型结果目录 (results_continuous/):")
    for file in sorted(os.listdir(output_dir_continuous)):
        if file.endswith('.png'):
            print(f"  ✓ {file}")

if __name__ == '__main__':
    main()
