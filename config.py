"""
AVIS仿真配置文件
"""

# 网络配置
TOTAL_RESOURCE_BLOCKS = 100  # 基站总资源块数
NUM_USERS = 4  # DASH用户数量
SIMULATION_TIME = 300  # 仿真时间（秒）
ALLOCATION_INTERVAL = 1  # 调度间隔（秒）

# 视频编码配置（DASH码率层）
BITRATE_LEVELS = [500, 1000, 2000, 4000, 8000]  # kbps

# 信道配置
CHANNEL_MODELS = {
    'good': {'base_throughput': 8000, 'variance': 500},      # 好
    'medium': {'base_throughput': 4000, 'variance': 500},    # 中等
    'poor': {'base_throughput': 2000, 'variance': 300},      # 差
}

# 调度参数
ALPHA_VALUES = [0.1, 0.5, 1.0]  # 惩罚函数权重参数（论文中的alpha）

# 评估参数
BITRATE_SWITCH_WINDOW = 10  # 码率切换计数窗口（秒，论文中的W）
