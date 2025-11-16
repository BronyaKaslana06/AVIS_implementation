"""
结果可视化模块
"""
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import numpy as np
from typing import Dict, List
import os


def plot_bitrate_comparison(results_avis: Dict, results_no_avis: Dict, 
                            alpha: float, output_dir: str = 'results'):
    """绘制码率对比图"""
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'AVIS vs NO-AVIS Bitrate Comparison (α={alpha})', fontsize=14, fontweight='bold')
    
    avis_bitrates = results_avis['history']['bitrates']
    no_avis_bitrates = results_no_avis['history']['bitrates']
    time = results_avis['history']['time']
    
    for idx, (user_id, avis_br) in enumerate(avis_bitrates.items()):
        ax = axes[idx // 2, idx % 2]
        
        no_avis_br = no_avis_bitrates.get(user_id, [])
        
        ax.plot(time, avis_br, label='AVIS', linewidth=1.5, alpha=0.7)
        ax.plot(time, no_avis_br, label='NO-AVIS', linewidth=1.5, alpha=0.7, linestyle='--')
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Bitrate (kbps)')
        ax.set_title(f'User {user_id}')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/bitrate_comparison_alpha_{alpha}.png', dpi=150)
    plt.close()


def plot_fairness_over_time(results_avis: Dict, results_no_avis: Dict, 
                            alpha: float, output_dir: str = 'results'):
    """绘制公平性指数随时间的变化"""
    os.makedirs(output_dir, exist_ok=True)
    
    from metrics import PerformanceMetrics
    
    avis_bitrates = results_avis['history']['bitrates']
    no_avis_bitrates = results_no_avis['history']['bitrates']
    time = results_avis['history']['time']
    
    # 计算滑动窗口的公平性
    window_size = 30
    avis_jain_over_time = []
    no_avis_jain_over_time = []
    time_points = []
    
    for i in range(len(time)):
        # 提取窗口内的数据
        start_idx = max(0, i - window_size)
        
        avis_window = {uid: br[start_idx:i+1] for uid, br in avis_bitrates.items()}
        no_avis_window = {uid: br[start_idx:i+1] for uid, br in no_avis_bitrates.items()}
        
        avis_jain = PerformanceMetrics.calculate_jain_fairness_index(avis_window)
        no_avis_jain = PerformanceMetrics.calculate_jain_fairness_index(no_avis_window)
        
        avis_jain_over_time.append(avis_jain)
        no_avis_jain_over_time.append(no_avis_jain)
        time_points.append(time[i])
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(time_points, avis_jain_over_time, label='AVIS', linewidth=2, alpha=0.8)
    ax.plot(time_points, no_avis_jain_over_time, label='NO-AVIS', linewidth=2, alpha=0.8, linestyle='--')
    
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Jain Fairness Index', fontsize=11)
    ax.set_title(f'Fairness Index Over Time (α={alpha})', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_ylim([0, 1.05])
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/fairness_over_time_alpha_{alpha}.png', dpi=150)
    plt.close()


def plot_bitrate_switches(results_avis: Dict, results_no_avis: Dict, 
                         alpha: float, output_dir: str = 'results'):
    """绘制码率切换频率对比"""
    os.makedirs(output_dir, exist_ok=True)
    
    from metrics import PerformanceMetrics
    
    avis_bitrates = results_avis['history']['bitrates']
    no_avis_bitrates = results_no_avis['history']['bitrates']
    
    avis_switches = PerformanceMetrics.calculate_bitrate_switch_frequency(avis_bitrates)
    no_avis_switches = PerformanceMetrics.calculate_bitrate_switch_frequency(no_avis_bitrates)
    
    user_ids = sorted(avis_switches.keys())
    x = np.arange(len(user_ids))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    avis_values = [avis_switches[uid] for uid in user_ids]
    no_avis_values = [no_avis_switches[uid] for uid in user_ids]
    
    bars1 = ax.bar(x - width/2, avis_values, width, label='AVIS', alpha=0.8)
    bars2 = ax.bar(x + width/2, no_avis_values, width, label='NO-AVIS', alpha=0.8)
    
    ax.set_xlabel('User ID', fontsize=11)
    ax.set_ylabel('Number of Switches', fontsize=11)
    ax.set_title(f'Bitrate Switching Frequency (α={alpha})', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'User {uid}' for uid in user_ids])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/bitrate_switches_alpha_{alpha}.png', dpi=150)
    plt.close()


def plot_metrics_comparison_bar(all_results: List[Dict], output_dir: str = 'results'):
    """绘制不同alpha值下的指标对比（柱状图）"""
    os.makedirs(output_dir, exist_ok=True)
    
    from metrics import PerformanceMetrics
    
    alphas = []
    jain_indices = []
    switch_counts = []
    avg_bitrates = []
    
    for result in all_results:
        alphas.append(result['alpha'])
        
        bitrates = result['history']['bitrates']
        jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
        switches = sum(PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates).values())
        avg_br = np.mean(list(PerformanceMetrics.calculate_avg_bitrate(bitrates).values()))
        
        jain_indices.append(jain)
        switch_counts.append(switches)
        avg_bitrates.append(avg_br)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('Performance Metrics vs Alpha Parameter', fontsize=13, fontweight='bold')
    
    # Jain指数
    axes[0].plot(alphas, jain_indices, 'o-', linewidth=2, markersize=8)
    axes[0].set_xlabel('Alpha (α)', fontsize=11)
    axes[0].set_ylabel('Jain Fairness Index', fontsize=11)
    axes[0].set_title('Fairness Index vs α')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim([0, 1.05])
    
    # 码率切换
    axes[1].plot(alphas, switch_counts, 'o-', linewidth=2, markersize=8, color='orange')
    axes[1].set_xlabel('Alpha (α)', fontsize=11)
    axes[1].set_ylabel('Total Bitrate Switches', fontsize=11)
    axes[1].set_title('Bitrate Switches vs α')
    axes[1].grid(True, alpha=0.3)
    
    # 平均码率
    axes[2].plot(alphas, avg_bitrates, 'o-', linewidth=2, markersize=8, color='green')
    axes[2].set_xlabel('Alpha (α)', fontsize=11)
    axes[2].set_ylabel('Average Bitrate (kbps)', fontsize=11)
    axes[2].set_title('Average Bitrate vs α')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/metrics_vs_alpha.png', dpi=150)
    plt.close()


def create_summary_report(all_results: List[Dict], output_dir: str = 'results'):
    """创建汇总报告图表"""
    os.makedirs(output_dir, exist_ok=True)
    
    from metrics import PerformanceMetrics
    
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    fig.suptitle('AVIS Performance Evaluation Report', fontsize=16, fontweight='bold')
    
    # 为每个alpha值创建子图
    for idx, result in enumerate(all_results):
        alpha = result['alpha']
        bitrates = result['history']['bitrates']
        time = result['history']['time']
        
        # 码率时间序列
        ax = fig.add_subplot(gs[idx, 0])
        for uid, br in bitrates.items():
            ax.plot(time, br, label=f'User {uid}', linewidth=1, alpha=0.7)
        ax.set_title(f'Bitrate Traces (α={alpha})', fontsize=10)
        ax.set_xlabel('Time (s)', fontsize=9)
        ax.set_ylabel('Bitrate (kbps)', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        
        # 公平性指数
        ax = fig.add_subplot(gs[idx, 1])
        jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
        ax.barh(['Fairness'], [jain], color='skyblue')
        ax.set_xlim([0, 1])
        ax.set_title(f'Jain Index (α={alpha})', fontsize=10)
        ax.text(jain/2, 0, f'{jain:.3f}', ha='center', va='center', fontweight='bold')
        
        # 码率切换
        ax = fig.add_subplot(gs[idx, 2])
        switches = PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates)
        users = sorted(switches.keys())
        counts = [switches[u] for u in users]
        ax.bar([f'U{u}' for u in users], counts, color='salmon')
        ax.set_title(f'Switches (α={alpha})', fontsize=10)
        ax.set_ylabel('Count', fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.savefig(f'{output_dir}/summary_report.png', dpi=150)
    plt.close()


def plot_resource_utilization_comparison(discrete_results_by_alpha: Dict, 
                                         continuous_results_by_alpha: Dict,
                                         no_avis_results: Dict,
                                         alpha_values: List[float],
                                         output_dir: str = 'results'):
    """
    绘制资源利用率对比图（柱状图）
    
    Args:
        discrete_results_by_alpha: 离散型AVIS各alpha值的结果字典
        continuous_results_by_alpha: 连续型AVIS各alpha值的结果字典
        no_avis_results: NO-AVIS的结果
        alpha_values: alpha参数列表
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    
    from metrics import PerformanceMetrics
    
    # 准备数据
    no_avis_util = PerformanceMetrics.calculate_resource_utilization(
        no_avis_results['history']['allocated_resources']
    )
    
    discrete_utils = []
    continuous_utils = []
    
    for alpha in alpha_values:
        discrete_util = PerformanceMetrics.calculate_resource_utilization(
            discrete_results_by_alpha[alpha]['history']['allocated_resources']
        )
        continuous_util = PerformanceMetrics.calculate_resource_utilization(
            continuous_results_by_alpha[alpha]['history']['allocated_resources']
        )
        
        discrete_utils.append(discrete_util)
        continuous_utils.append(continuous_util)
    
    # 绘制柱状图
    fig, ax = plt.subplots(figsize=(12, 6))
    
    x = np.arange(len(alpha_values))
    width = 0.25
    
    # 三组柱子
    bars1 = ax.bar(x - width, [no_avis_util] * len(alpha_values), width, 
                   label='NO-AVIS', color='lightcoral', alpha=0.8)
    bars2 = ax.bar(x, discrete_utils, width, 
                   label='Discrete AVIS', color='skyblue', alpha=0.8)
    bars3 = ax.bar(x + width, continuous_utils, width, 
                   label='Continuous AVIS', color='lightgreen', alpha=0.8)
    
    # 添加数值标签
    def add_value_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height*100:.1f}%',
                   ha='center', va='bottom', fontsize=9)
    
    add_value_labels(bars1)
    add_value_labels(bars2)
    add_value_labels(bars3)
    
    # 设置图表属性
    ax.set_xlabel('Alpha (α)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Resource Utilization (%)', fontsize=12, fontweight='bold')
    ax.set_title('Resource Utilization Comparison: NO-AVIS vs Discrete AVIS vs Continuous AVIS', 
                fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{alpha:.1f}' for alpha in alpha_values])
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim([0, max(max(discrete_utils), max(continuous_utils), no_avis_util) * 1.15])
    
    # 转换y轴为百分比显示
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.0f}%'))
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/resource_utilization_comparison.png', dpi=150)
    plt.close()
    
    print(f"  ✓ 资源利用率对比图: resource_utilization_comparison.png")
