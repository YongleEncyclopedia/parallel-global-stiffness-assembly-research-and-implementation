// 封装操作系统、CPU 拓扑、OpenMP 线程数和进程内存等平台信息。
#pragma once

#include <string>

#ifndef PGSA_HAS_OPENMP
#define PGSA_HAS_OPENMP 0
#endif

namespace fem {

struct PlatformInfo {
    std::string os;
    std::string arch;
    std::string compiler;
    std::string openmp;
};

struct CpuTopologyInfo {
    std::string model;
    int physical_cores = 0;
    int logical_cores = 0;
};

PlatformInfo get_platform_info();
std::string platform_info_compact();
CpuTopologyInfo get_cpu_topology_info();
std::string classify_thread_region(int requested_threads, const CpuTopologyInfo& cpu);
bool openmp_available() noexcept;
void require_openmp(const std::string& feature);
int effective_thread_count(int requested_threads);
int current_thread_id();
int max_thread_count();
double current_peak_rss_mb();
std::string environment_value_or_empty(const char* name);

} // namespace fem
