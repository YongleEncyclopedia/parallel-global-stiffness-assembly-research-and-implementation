#pragma once

#include <string>

namespace fem {

struct PlatformInfo {
    std::string os;
    std::string arch;
    std::string compiler;
    std::string openmp;
};

PlatformInfo get_platform_info();
std::string platform_info_compact();
int effective_thread_count(int requested_threads);
int current_thread_id();
int max_thread_count();
double current_peak_rss_mb();
std::string environment_value_or_empty(const char* name);

} // namespace fem
