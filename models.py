"""
用户和视频流数据模型
"""
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict
from config import BITRATE_LEVELS


@dataclass
class User:
    """DASH视频流用户"""
    user_id: int
    channel_quality: str  # 'good', 'medium', 'poor'
    
    # 当前传输状态
    current_bitrate: int = BITRATE_LEVELS[0]  # 当前选择的码率(kbps)
    buffer_occupancy: float = 0.0  # 缓冲区占有量(秒)
    
    # 统计信息
    bitrate_history: List[int] = field(default_factory=list)
    allocated_resources: List[int] = field(default_factory=list)  # 每时刻分配的资源块数
    timestamps: List[float] = field(default_factory=list)
    
    def get_available_bitrates(self) -> List[int]:
        """获取用户可以选择的码率列表"""
        return BITRATE_LEVELS.copy()
    
    def get_bitrate_switches(self, window_size: int = 10) -> int:
        """获取最近window_size个时刻的码率切换次数"""
        if len(self.bitrate_history) < 2:
            return 0
        recent = self.bitrate_history[-window_size:] if len(self.bitrate_history) > window_size else self.bitrate_history
        switches = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        return switches


@dataclass
class AllocationResult:
    """Allocator模块的分配结果"""
    user_allocations: Dict[int, int] = field(default_factory=dict)  # user_id -> 分配的资源块数
    user_bitrates: Dict[int, int] = field(default_factory=dict)    # user_id -> 推荐的码率(kbps)
    total_resources_used: int = 0
    objective_value: float = 0.0  # 目标函数值
    
    def __str__(self) -> str:
        return f"Allocation(users={len(self.user_allocations)}, resources_used={self.total_resources_used}, obj={self.objective_value:.2f})"
