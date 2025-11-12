#!/usr/bin/env python3
"""
AVIS仿真快速测试脚本
用于验证代码的正确性和可运行性
"""

import sys
import numpy as np
from simulator import SimulationEngine
from metrics import PerformanceMetrics

def quick_test():
    """快速测试各个模块"""
    print("\n" + "="*70)
    print("AVIS仿真模块检查")
    print("="*70)
    
    # 1. 测试AVIS模块
    print("\n【测试1】: AVIS模块初始化...")
    try:
        engine_avis = SimulationEngine(use_avis=True, alpha=0.5)
        print("  ✓ AVIS引擎初始化成功")
        print(f"    - 用户数: {engine_avis.simulator.num_users}")
        print(f"    - 总资源块: {engine_avis.simulator.total_resources}")
        print(f"    - Alpha参数: {engine_avis.alpha}")
    except Exception as e:
        print(f"  ✗ 初始化失败: {e}")
        return False
    
    # 2. 测试NO-AVIS模块
    print("\n【测试2】: NO-AVIS模块初始化...")
    try:
        engine_no_avis = SimulationEngine(use_avis=False)
        print("  ✓ NO-AVIS引擎初始化成功")
    except Exception as e:
        print(f"  ✗ 初始化失败: {e}")
        return False
    
    # 3. 运行短仿真
    print("\n【测试3】: 运行短仿真 (30秒)...")
    try:
        results_avis = engine_avis.run_simulation(duration=30)
        print("  ✓ AVIS仿真完成")
        print(f"    - 总时刻数: {len(results_avis['history']['time'])}")
        print(f"    - 用户数: {len(results_avis['users'])}")
    except Exception as e:
        print(f"  ✗ 仿真失败: {e}")
        return False
    
    # 4. 计算性能指标
    print("\n【测试4】: 计算性能指标...")
    try:
        bitrates = results_avis['history']['bitrates']
        
        # 公平性指数
        jain = PerformanceMetrics.calculate_jain_fairness_index(bitrates)
        print(f"  ✓ Jain公平性指数: {jain:.4f}")
        
        # 码率切换
        switches = PerformanceMetrics.calculate_bitrate_switch_frequency(bitrates)
        total_switches = sum(switches.values())
        print(f"  ✓ 总码率切换: {total_switches} 次")
        
        # 平均码率
        avg_br = PerformanceMetrics.calculate_avg_bitrate(bitrates)
        print(f"  ✓ 平均码率: {np.mean(list(avg_br.values())):.0f} kbps")
        
    except Exception as e:
        print(f"  ✗ 指标计算失败: {e}")
        return False
    
    # 5. 生成可视化
    print("\n【测试5】: 生成可视化...")
    try:
        from visualization import plot_bitrate_comparison
        results_no_avis = engine_no_avis.run_simulation(duration=30)
        plot_bitrate_comparison(results_avis, results_no_avis, 0.5, 'test_results')
        print("  ✓ 图表生成成功 (test_results/)")
    except Exception as e:
        print(f"  ⚠ 可视化生成失败: {e} (可能是matplotlib问题)")
    
    print("\n" + "="*70)
    print("所有模块检查完成!")
    print("="*70 + "\n")
    
    return True


if __name__ == '__main__':
    success = quick_test()
    sys.exit(0 if success else 1)
