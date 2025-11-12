# 研究生课程大作业

# 一、作业题目

自适应视频流调度算法实现与现代无线通信网络仿真评估

# 二、任务背景

随着移动视频流量的激增，基于HTTP的自适应视频流（如DASH）已成为主流。然而，多个自适应视频流在共享无线链路时存在公平性、稳定性和资源利用率等问题。论文《A Scheduling Framework for Adaptive Video Delivery over Cellular Networks》提出通过在基站侧调度资源，实现了多用户自适应视频流的公平、稳定与高效传输。

# 三、任务目标

1. 理解数学优化问题，离散与连续两种建模方式；  
2. 实现AVIS调度器，Allocator与Enforcer模块；  
3. 现代通信网络协议，对照现代3GPP协议，指出关键代码与某一协议的对照关系；  
4. 在仿真环境中验证算法性能，评估其在公平性、稳定性与资源利用率方面的表现；  
5. 撰写实验报告并制作汇报PPT，展示实现过程与结果分析。

# 四、任务要求

# 1. 组队方式

- 1~2人一组，鼓励独立完成，也支持合作。

# 2. 提交内容

- 可运行代码 (Python/MATLAB/C++等)  
- 实验报告（PDF格式，包含问题建模、算法设计、实验结果与分析）  
- 汇报PPT (10-15分钟，用于课堂展示)

# 3. 实现内容

# (1) 数学建模与算法实现

- 实现离散优化模型（多选择背包问题）：

目标函数:

$$
\max  \sum_ {i = 1} ^ {N} \sum_ {j = 1} ^ {M _ {i}} \left(u _ {i j} - \alpha f _ {i j}\right) x _ {i j}
$$

。约束条件：资源块总数限制、每个用户只能选择一个码率版本

- 实现连续优化模型及其量化方法  
- 实现惩罚函数（如multiplicative penalty）与参数α调节机制

# (2) 仿真环境搭建

- 使用LTE或5G系统仿真平台（如NS-3, SimuLTE, MATLAB LTE Toolbox）  
- 或使用Wi-Fi + DASH仿真环境（如Mininet + DASH.js）  
- 模拟多个DASH用户在不同信道条件下的视频流行为

# (3) 性能评估

- 对比AVIS与无调度（NO-AVIS）情况下的：

。公平性指数（Jain'sFairnessIndex）  
码率切换频率  
资源利用率

- 分析不同α值对性能的影响

# (4) 扩展功能

- 实现动态用户加入/离开场景  
- 支持VBR视频流量模型  
- 实现Enforcer中的流量整形与调度机制

# 五、评分标准

<table><tr><td>项目</td><td>分值</td><td>说明</td></tr><tr><td>模型理解与建模</td><td>20%</td><td>是否准确理解并实现了论文中的优化问题</td></tr><tr><td>算法实现与代码质量</td><td>30%</td><td>代码结构清晰、可运行、注释完整</td></tr><tr><td>仿真实验与结果分析</td><td>30%</td><td>实验设计合理、结果可视化、分析深入</td></tr><tr><td>报告与PPT</td><td>20%</td><td>逻辑清晰、表达准确、展示专业</td></tr></table>

# 六、参考资料

- 论文原文：《A Scheduling Framework for Adaptive Video Delivery over Cellular Networks》  
DASH标准：MPEG-DASH (dashif.org)  
- 仿真工具推荐：

MATLAB LTE/NR Toolbox  
- NS-3 + LENA模块 (LTE/5G)  
SimuLTE (OMNeT++ based)  
• Mininet + DASH.js (用于网络层仿真)