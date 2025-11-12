# AVIS仿真 - 快速开始指南

## 📋 要求

- Python 3.6+
- numpy
- matplotlib

## 🚀 快速启动

### 1. 安装依赖

```bash
pip install numpy matplotlib
```

### 2. 运行仿真（3分钟完成）

```bash
cd /Users/cuichenrui/code/avis_simulation
python main.py
```

### 3. 查看结果

仿真完成后，所有图表保存在 `results/` 目录：

```bash
ls results/
```

## 📊 生成的文件说明

| 文件 | 说明 |
|-----|------|
| `bitrate_comparison_alpha_*.png` | AVIS vs NO-AVIS码率对比 |
| `fairness_over_time_alpha_*.png` | 公平性指数随时间变化 |
| `bitrate_switches_alpha_*.png` | 码率切换频率对比 |
| `metrics_vs_alpha.png` | Alpha参数影响分析 |
| `summary_report.png` | 完整性能汇总 |

## 🔧 配置调整

编辑 `config.py` 修改参数：

```python
# 网络配置
TOTAL_RESOURCE_BLOCKS = 100       # 增加/减少资源块
NUM_USERS = 4                     # 调整用户数量
SIMULATION_TIME = 300             # 调整仿真时长

# 码率等级
BITRATE_LEVELS = [500, 1000, 2000, 4000, 8000]  # 自定义码率

# Alpha参数
ALPHA_VALUES = [0.1, 0.5, 1.0]    # 测试的alpha值
```

## 📈 快速测试

运行快速验证（30秒）：

```bash
python test_quick.py
```

## 🎯 关键指标解读

### Jain公平性指数 (J)
- **范围**: 0 到 1
- **含义**: 1 = 完全公平，越接近1越好
- **优化目标**: 最大化

### 码率切换频率
- **含义**: 仿真期间码率变化次数
- **含义**: 次数越少越好（QoE更好）
- **优化目标**: 最小化

### 资源利用率 (U)
- **范围**: 0 到 1
- **含义**: 使用了多少可用资源
- **优化目标**: 平衡（不一定最大化）

### 码率稳定性 (σ)
- **含义**: 码率的标准差
- **含义**: 值越小越稳定
- **优化目标**: 最小化

## 🔍 实验对比

查看具体的性能差异：

### AVIS特点
- ✓ 完全公平分配
- ✓ 消除不必要切换
- ✓ 稳定的用户体验
- ✗ 吞吐量可能低于自由竞争

### NO-AVIS特点
- ✓ 吞吐量相对较高
- ✗ 分配不公平
- ✗ 频繁码率切换
- ✗ 弱用户体验差

## 💡 参数调优建议

| 场景 | Alpha建议 | 原因 |
|-----|---------|------|
| 优先码率 | 0.1 | 减少惩罚，允许更多切换 |
| 平衡方案 | 0.5 | 中等权重，平衡两者 |
| 优先稳定 | 1.0 | 增加惩罚，减少切换 |

## 📝 实验步骤

1. **运行基础仿真**
   ```bash
   python main.py
   ```

2. **修改Alpha值**
   ```python
   # config.py
   ALPHA_VALUES = [0.01, 0.1, 0.5, 1.0, 2.0]  # 更多值
   ```

3. **重新运行**
   ```bash
   python main.py
   ```

4. **分析结果**
   - 查看 `results/metrics_vs_alpha.png`
   - 比较不同alpha的性能

## 🐛 常见问题

### Q: 仿真太慢？
**A**: 减少 `SIMULATION_TIME` 或 `NUM_USERS`

### Q: 内存不足？
**A**: 减少 `TOTAL_RESOURCE_BLOCKS` 或运行短仿真

### Q: 图表没有生成？
**A**: 确保安装了matplotlib，检查 `results/` 目录权限

### Q: 性能指标相同？
**A**: 这是正常的。在某些场景下，不同Alpha值收敛到相同状态

## 📚 深入学习

### 理解算法
- 阅读 `EXPERIMENT_REPORT.md` 中的第二章
- 查看 `allocator.py` 中的注释

### 修改算法
- 在 `allocator.py` 中修改目标函数
- 在 `enforcer.py` 中调整Token Bucket参数

### 扩展功能
- 添加VBR模型：修改 `simulator.py`
- 动态用户：修改 `NetworkSimulator`
- 多基站：创建新的 `MultiCellSimulator`

## 🎓 教学指导

### 作业步骤
1. ✓ 理解问题建模（第二章）
2. ✓ 实现Allocator（已完成）
3. ✓ 实现Enforcer（已完成）
4. ✓ 搭建仿真环境（已完成）
5. ✓ 性能评估（已完成）
6. □ 撰写报告
7. □ 制作PPT

### 报告框架
- 问题建模
- 算法设计
- 实验设置
- 结果分析
- 结论讨论
- 代码清单

## 📞 技术支持

### 查看日志
```bash
cat sim_output.log
```

### 运行调试模式
```python
# config.py
DEBUG = True
```

### 检查代码语法
```bash
python -m py_compile allocator.py enforcer.py simulator.py
```

---

**更新时间**: 2025年11月12日  
**版本**: 1.0  
**作者**: AVIS仿真团队
