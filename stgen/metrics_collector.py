# stgen/metrics_collector.py
"""
@file metrics_collector.py
@brief Advanced Metrics Collection and Statistical Analysis
@details Handles efficient collection and calculation of performance metrics with minimal overhead.
         Includes classes for Histogram buckets, Streaming percentiles, and a central MetricsCollector.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from collections import deque
from dataclasses import dataclass, asdict
import json

## @brief Logger for the metrics collector module
_LOG = logging.getLogger("metrics_collector")


@dataclass
class Percentile:
    """
    @brief Container for percentile value.
    @details Holds standard percentile points (p50, p75, p90, p95, p99).
    """
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    
    def to_dict(self) -> Dict[str, float]:
        """
        @brief Convert percentile data to a dictionary.
        @return Dict[str, float] Dictionary representation of the percentile values.
        """
        return asdict(self)


class HistogramBucket:
    """
    @brief Efficient histogram with configurable buckets.
    @details Manages data distribution into fixed-width buckets to calculate statistics
             without storing every individual data point.
    """
    
    def __init__(self, min_val: float = 0, max_val: float = 1000, num_buckets: int = 100):
        """
        @brief Initialize histogram.
        
        @param min_val Minimum value for the histogram range.
        @param max_val Maximum value for the histogram range.
        @param num_buckets Number of buckets to divide the range into.
        """
        self.min_val = min_val
        self.max_val = max_val
        self.num_buckets = num_buckets
        self.buckets = [0] * num_buckets
        self.underflow = 0
        self.overflow = 0
        self.total_count = 0
        self.total_sum = 0.0
        
        self.bucket_width = (max_val - min_val) / num_buckets
    
    def add(self, value: float) -> None:
        """
        @brief Add value to histogram.
        
        @details Increments the count for the specific bucket corresponding to the value.
                 Handles underflow and overflow if value is outside range.
        
        @param value The numerical value to add.
        @return None
        """
        self.total_count += 1
        self.total_sum += value
        
        if value < self.min_val:
            self.underflow += 1
            return
        
        if value >= self.max_val:
            self.overflow += 1
            return
        
        bucket_idx = int((value - self.min_val) / self.bucket_width)
        bucket_idx = min(bucket_idx, self.num_buckets - 1)
        self.buckets[bucket_idx] += 1
    
    def percentile(self, p: float) -> float:
        """
        @brief Calculate percentile (0-100).
        
        @details Uses linear interpolation within buckets to estimate the percentile value.
        
        @param p Percentile to calculate (0-100).
            
        @return float Value at the specified percentile.
        """
        if self.total_count == 0:
            return 0.0
        
        target_count = (p / 100.0) * self.total_count
        cumulative = self.underflow
        
        for i, count in enumerate(self.buckets):
            cumulative += count
            if cumulative >= target_count:
                # Linear interpolation within bucket
                bucket_start = self.min_val + i * self.bucket_width
                bucket_end = bucket_start + self.bucket_width
                
                if count == 0:
                    return bucket_start
                
                bucket_fraction = (cumulative - target_count) / count
                return bucket_end - (bucket_fraction * self.bucket_width)
        
        return self.max_val
    
    def mean(self) -> float:
        """
        @brief Calculate the arithmetic mean of added values.
        @return float The mean value, or 0.0 if count is 0.
        """
        if self.total_count == 0:
            return 0.0
        return self.total_sum / self.total_count
    
    def stats(self) -> Dict[str, Any]:
        """
        @brief Get histogram statistics.
        @return Dict[str, Any] Dictionary containing count, sum, mean, min, max, underflow, and overflow.
        """
        return {
            "count": self.total_count,
            "sum": self.total_sum,
            "mean": self.mean(),
            "min": self.min_val,
            "max": self.max_val,
            "underflow": self.underflow,
            "overflow": self.overflow
        }


class StreamingPercentile:
    """
    @brief Calculate percentiles on-the-fly with bounded memory (t-digest style).
    @details Maintains a fixed-size buffer of recent samples to calculate exact percentiles
             over a sliding window or limited dataset.
    """
    
    def __init__(self, buffer_size: int = 10000):
        """
        @brief Initialize streaming percentile calculator.
        
        @param buffer_size Max samples to keep in memory (deque size).
        """
        self.buffer = deque(maxlen=buffer_size)
        self.sorted_cache = None
        self.cache_valid = False
    
    def add(self, value: float) -> None:
        """
        @brief Add sample to the buffer.
        @details Invalidates the sorted cache.
        @param value The value to add.
        @return None
        """
        self.buffer.append(value)
        self.cache_valid = False
    
    def _ensure_sorted(self) -> None:
        """
        @brief Ensure sorted cache is valid.
        @details Sorts the buffer if the cache is currently invalid.
        @return None
        """
        if not self.cache_valid:
            self.sorted_cache = sorted(self.buffer)
            self.cache_valid = True
    
    def percentile(self, p: float) -> float:
        """
        @brief Calculate a single percentile.
        
        @param p Percentile to calculate (0-100).
            
        @return float The percentile value.
        """
        if len(self.buffer) == 0:
            return 0.0
        
        self._ensure_sorted()
        idx = int((p / 100.0) * len(self.sorted_cache))
        idx = min(max(idx, 0), len(self.sorted_cache) - 1)
        return self.sorted_cache[idx]
    
    def percentiles(self, ps: List[float]) -> Dict[str, float]:
        """
        @brief Calculate multiple percentiles efficiently.
        
        @param ps List of percentiles to calculate (e.g., [50, 90, 99]).
        @return Dict[str, float] Dictionary mapping percentile keys (e.g., 'p90') to values.
        """
        result = {}
        for p in ps:
            result[f"p{int(p)}"] = self.percentile(p)
        return result


class MetricsCollector:
    """
    @brief Efficient metrics collection for protocol testing.
    @details Aggregates latency, throughput, loss, and error metrics. 
             Supports per-client tracking and export functionality.
    """
    
    def __init__(self, max_samples: int = 100000):
        """
        @brief Initialize metrics collector.
        
        @param max_samples Maximum samples to keep in memory for streaming percentiles.
        """
        self.max_samples = max_samples
        
        # Latency tracking
        self.latencies = StreamingPercentile(max_samples)
        self.latency_histogram = HistogramBucket(min_val=0, max_val=1000, num_buckets=100)
        
        # Throughput
        self.packets_sent = 0
        self.packets_recv = 0
        self.packets_lost = 0
        
        # Errors
        self.errors: List[str] = []
        self.error_types: Dict[str, int] = {}
        
        # Timing
        self.start_time = time.time()
        self.end_time = None
        
        # Per-client metrics
        self.client_stats: Dict[str, Dict[str, Any]] = {}
        
        _LOG.info("MetricsCollector initialized (max_samples=%d)", max_samples)
    
    def record_latency(self, latency_ms: float, client_id: str = None) -> None:
        """
        @brief Record a latency sample.
        
        @details Updates both global statistics and per-client statistics if a client_id is provided.
        
        @param latency_ms Latency in milliseconds.
        @param client_id Optional client identifier string.
        @return None
        """
        # Global tracking
        self.latencies.add(latency_ms)
        self.latency_histogram.add(latency_ms)
        
        # Per-client tracking
        if client_id:
            if client_id not in self.client_stats:
                self.client_stats[client_id] = {
                    "latencies": [],
                    "count": 0,
                    "errors": 0
                }
            self.client_stats[client_id]["latencies"].append(latency_ms)
            self.client_stats[client_id]["count"] += 1
    
    def record_send(self) -> None:
        """
        @brief Record packet sent.
        @return None
        """
        self.packets_sent += 1
    
    def record_recv(self) -> None:
        """
        @brief Record packet received.
        @return None
        """
        self.packets_recv += 1
    
    def record_loss(self, count: int = 1) -> None:
        """
        @brief Record packet loss.
        @param count Number of packets lost (default 1).
        @return None
        """
        self.packets_lost += count
    
    def record_error(self, error_type: str, message: str = "") -> None:
        """
        @brief Record an error.
        
        @param error_type Category/Type of the error.
        @param message Detailed error message.
        @return None
        """
        self.errors.append(f"{error_type}: {message}")
        self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
    
    def finalize(self) -> None:
        """
        @brief Finalize collection (call after test completes).
        @details Sets the end time for duration calculations.
        @return None
        """
        self.end_time = time.time()
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """
        @brief Get latency percentiles.
        @return Dict[str, float] Dictionary containing p50, p75, p90, p95, and p99 latency in ms.
        """
        return {
            "p50_ms": self.latencies.percentile(50),
            "p75_ms": self.latencies.percentile(75),
            "p90_ms": self.latencies.percentile(90),
            "p95_ms": self.latencies.percentile(95),
            "p99_ms": self.latencies.percentile(99),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        @brief Get complete metrics summary.
        @details Calculates duration, loss rate, throughput, and aggregates all stats.
        @return Dict[str, Any] Comprehensive dictionary of all collected metrics.
        """
        duration = (self.end_time or time.time()) - self.start_time
        loss_rate = 1.0 - (self.packets_recv / max(self.packets_sent, 1))
        
        summary = {
            "duration_sec": duration,
            "sent": self.packets_sent,
            "recv": self.packets_recv,
            "lost": self.packets_lost,
            "loss": loss_rate,
            "throughput_msg_sec": self.packets_recv / max(duration, 1),
            "errors": len(self.errors),
            "error_types": self.error_types,
        }
        
        # Add latency stats
        summary.update(self.get_latency_percentiles())
        
        # Add histogram stats
        summary["latency_histogram"] = self.latency_histogram.stats()
        
        return summary
    
    def get_client_summary(self, client_id: str) -> Dict[str, Any]:
        """
        @brief Get per-client metrics.
        
        @param client_id The ID of the client to retrieve stats for.
        @return Dict[str, Any] Dictionary containing packet counts, error counts, and latency stats for the client.
        """
        if client_id not in self.client_stats:
            return {}
        
        stats = self.client_stats[client_id]
        lats = sorted(stats["latencies"]) if stats["latencies"] else []
        
        result = {
            "client_id": client_id,
            "packet_count": stats["count"],
            "error_count": stats["errors"]
        }
        
        if lats:
            result.update({
                "lat_min_ms": lats[0],
                "lat_max_ms": lats[-1],
                "lat_avg_ms": sum(lats) / len(lats),
                "lat_p50_ms": lats[len(lats) // 2],
                "lat_p95_ms": lats[int(len(lats) * 0.95)],
            })
        
        return result
    
    def export_results(self, filepath: str) -> None:
        """
        @brief Export metrics to JSON.
        
        @details Serializes the summary and per-client summaries to a JSON file.
        
        @param filepath Output file path.
        @return None
        """
        summary = self.get_summary()
        
        # Add per-client summaries
        summary["client_summaries"] = [
            self.get_client_summary(cid) 
            for cid in sorted(self.client_stats.keys())
        ]
        
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        _LOG.info("Metrics exported to %s", filepath)
    
    def print_summary(self) -> None:
        """
        @brief Print metrics summary to console.
        @details Formats key metrics (duration, throughput, latency, errors) for human readability.
        @return None
        """
        summary = self.get_summary()
        
        print("\n" + "=" * 70)
        print("METRICS SUMMARY")
        print("=" * 70)
        print(f"Duration: {summary['duration_sec']:.2f}s")
        print(f"Sent: {summary['sent']}, Received: {summary['recv']}, "
              f"Lost: {summary['lost']} ({summary['loss']*100:.2f}%)")
        print(f"Throughput: {summary['throughput_msg_sec']:.1f} msg/s")
        print(f"Errors: {summary['errors']}")
        
        if summary.get("p50_ms"):
            print(f"\nLatency:")
            print(f"  P50: {summary['p50_ms']:.2f}ms")
            print(f"  P95: {summary['p95_ms']:.2f}ms")
            print(f"  P99: {summary['p99_ms']:.2f}ms")
        
        if summary.get("error_types"):
            print(f"\nError Types: {summary['error_types']}")
        
        print("=" * 70 + "\n")