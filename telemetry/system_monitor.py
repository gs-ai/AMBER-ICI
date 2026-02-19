"""
System Telemetry Monitor
Tracks GPU, CPU, RAM, and model memory usage
"""

import psutil
from typing import Dict, Optional
from datetime import datetime


class SystemMonitor:
    """Monitor system resources and telemetry"""
    
    def __init__(self):
        self.gpu_available = self._check_gpu_support()
    
    def _check_gpu_support(self) -> bool:
        """Check if GPU monitoring is available"""
        try:
            import GPUtil
            return True
        except ImportError:
            return False
    
    def get_current_stats(self) -> Dict:
        """Get current system statistics"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "cpu": self._get_cpu_stats(),
            "memory": self._get_memory_stats(),
            "disk": self._get_disk_stats(),
        }
        
        if self.gpu_available:
            stats["gpu"] = self._get_gpu_stats()
        else:
            stats["gpu"] = {"available": False, "message": "GPU monitoring not available"}
        
        return stats
    
    def _get_cpu_stats(self) -> Dict:
        """Get CPU usage statistics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        return {
            "usage_percent": cpu_percent,
            "core_count": cpu_count,
            "frequency_mhz": cpu_freq.current if cpu_freq else None,
            "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True)
        }
    
    def _get_memory_stats(self) -> Dict:
        """Get memory usage statistics"""
        memory = psutil.virtual_memory()
        
        return {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "usage_percent": memory.percent,
            "free_gb": round(memory.free / (1024**3), 2)
        }
    
    def _get_disk_stats(self) -> Dict:
        """Get disk usage statistics"""
        disk = psutil.disk_usage('/')
        
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "usage_percent": disk.percent
        }
    
    def _get_gpu_stats(self) -> Dict:
        """Get GPU usage statistics"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            if not gpus:
                return {"available": False, "message": "No GPUs detected"}
            
            gpu_stats = []
            for gpu in gpus:
                gpu_stats.append({
                    "id": gpu.id,
                    "name": gpu.name,
                    "load_percent": round(gpu.load * 100, 2),
                    "memory_used_mb": round(gpu.memoryUsed, 2),
                    "memory_total_mb": round(gpu.memoryTotal, 2),
                    "memory_free_mb": round(gpu.memoryFree, 2),
                    "memory_usage_percent": round((gpu.memoryUsed / gpu.memoryTotal) * 100, 2),
                    "temperature_c": gpu.temperature
                })
            
            return {
                "available": True,
                "count": len(gpus),
                "gpus": gpu_stats
            }
        
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def get_process_stats(self, pid: Optional[int] = None) -> Dict:
        """Get statistics for a specific process"""
        try:
            if pid is None:
                process = psutil.Process()
            else:
                process = psutil.Process(pid)
            
            return {
                "pid": process.pid,
                "name": process.name(),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": round(process.memory_info().rss / (1024**2), 2),
                "memory_percent": round(process.memory_percent(), 2),
                "num_threads": process.num_threads(),
                "status": process.status()
            }
        
        except Exception as e:
            return {"error": str(e)}
