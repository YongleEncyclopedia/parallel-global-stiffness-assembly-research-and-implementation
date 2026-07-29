// 实现跨平台的系统信息、CPU 核数、OpenMP 状态和进程内存查询。
#include "core/platform.h"

#include <cstdlib>
#include <fstream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <thread>

#if defined(__APPLE__) || defined(__linux__)
#include <sys/resource.h>
#endif

#if defined(__APPLE__)
#include <sys/sysctl.h>
#endif

#if PGSA_HAS_OPENMP
#include <omp.h>
#endif

namespace fem {
namespace {

std::string read_environment_value(const char* name) {
    if (!name || !*name) return {};
#if defined(_WIN32)
    char* raw_value = nullptr;
    std::size_t size = 0;
    const int result = _dupenv_s(&raw_value, &size, name);
    const std::unique_ptr<char, decltype(&std::free)> value(raw_value, &std::free);
    if (result != 0 || value == nullptr) return {};
    return std::string(value.get());
#else
    const char* value = std::getenv(name);
    return value ? std::string(value) : std::string{};
#endif
}

#if defined(__APPLE__)
std::string sysctl_string(const char* name) {
    std::size_t size = 0;
    if (sysctlbyname(name, nullptr, &size, nullptr, 0) != 0 || size == 0) return {};
    std::string value(size, '\0');
    if (sysctlbyname(name, value.data(), &size, nullptr, 0) != 0) return {};
    while (!value.empty() && value.back() == '\0') value.pop_back();
    return value;
}

int sysctl_int(const char* name) {
    int value = 0;
    std::size_t size = sizeof(value);
    if (sysctlbyname(name, &value, &size, nullptr, 0) != 0) return 0;
    return value;
}
#endif

#if defined(__linux__)
std::string first_cpuinfo_value(const std::string& key) {
    std::ifstream in("/proc/cpuinfo");
    std::string line;
    while (std::getline(in, line)) {
        const auto pos = line.find(':');
        if (pos == std::string::npos) continue;
        if (line.substr(0, pos).find(key) == std::string::npos) continue;
        std::string value = line.substr(pos + 1);
        while (!value.empty() && value.front() == ' ') value.erase(value.begin());
        return value;
    }
    return {};
}
#endif

} // namespace

PlatformInfo get_platform_info() {
    PlatformInfo info;
#if defined(_WIN32)
    info.os = "Windows";
#elif defined(__APPLE__)
    info.os = "macOS";
#elif defined(__linux__)
    info.os = "Linux";
#else
    info.os = "UnknownOS";
#endif

#if defined(__aarch64__) || defined(_M_ARM64)
    info.arch = "arm64";
#elif defined(__x86_64__) || defined(_M_X64)
    info.arch = "x86_64";
#elif defined(__i386__) || defined(_M_IX86)
    info.arch = "x86";
#else
    info.arch = "unknown_arch";
#endif

#if defined(__clang__)
    info.compiler = "Clang " + std::string(__clang_version__);
#elif defined(__GNUC__)
    info.compiler = "GCC " + std::to_string(__GNUC__) + "." + std::to_string(__GNUC_MINOR__);
#elif defined(_MSC_VER)
    info.compiler = "MSVC " + std::to_string(_MSC_VER);
#else
    info.compiler = "UnknownCompiler";
#endif

#if PGSA_HAS_OPENMP
    info.openmp = "OpenMP " + std::to_string(_OPENMP);
#else
    info.openmp = "OpenMP disabled";
#endif
    return info;
}

std::string platform_info_compact() {
    const auto info = get_platform_info();
    std::ostringstream os;
    os << info.os << ";" << info.arch << ";" << info.compiler << ";" << info.openmp;
    return os.str();
}

CpuTopologyInfo get_cpu_topology_info() {
    CpuTopologyInfo info;
#if defined(__APPLE__)
    info.model = sysctl_string("machdep.cpu.brand_string");
    if (info.model.empty()) info.model = sysctl_string("hw.model");
    info.physical_cores = sysctl_int("hw.physicalcpu");
    info.logical_cores = sysctl_int("hw.logicalcpu");
#elif defined(__linux__)
    info.model = first_cpuinfo_value("model name");
    if (info.model.empty()) info.model = first_cpuinfo_value("Hardware");
    info.logical_cores = static_cast<int>(std::thread::hardware_concurrency());
    info.physical_cores = info.logical_cores;
#elif defined(_WIN32)
    info.model = read_environment_value("PROCESSOR_IDENTIFIER");
    if (info.model.empty()) info.model = "Windows CPU";
    info.logical_cores = static_cast<int>(std::thread::hardware_concurrency());
    info.physical_cores = info.logical_cores;
#else
    info.model = "Unknown CPU";
    info.logical_cores = static_cast<int>(std::thread::hardware_concurrency());
    info.physical_cores = info.logical_cores;
#endif
    if (info.model.empty()) info.model = "Unknown CPU";
    if (info.logical_cores <= 0) info.logical_cores = max_thread_count();
    if (info.physical_cores <= 0) info.physical_cores = info.logical_cores;
    return info;
}

std::string classify_thread_region(int requested_threads, const CpuTopologyInfo& cpu) {
    const int threads = requested_threads <= 0 ? max_thread_count() : requested_threads;
    int logical = cpu.logical_cores;
    if (logical <= 0) logical = max_thread_count();
    int physical = cpu.physical_cores;
    if (physical <= 0 || physical > logical) physical = logical;

    if (threads <= physical) return "physical_core_region";
    if (threads <= logical && logical > physical) return "logical_core_region";
    return "oversubscription_region";
}

int max_thread_count() {
#if PGSA_HAS_OPENMP
    return omp_get_max_threads();
#else
    return 1;
#endif
}

bool openmp_available() noexcept {
    return PGSA_HAS_OPENMP == 1;
}

void require_openmp(const std::string& feature) {
    if (openmp_available()) return;
    const std::string feature_name = feature.empty() ? "requested feature" : feature;
    throw std::runtime_error(
        "OpenMP is unavailable: " + feature_name + " requires an OpenMP-enabled build");
}

int effective_thread_count(int requested_threads) {
#if PGSA_HAS_OPENMP
    if (requested_threads <= 0) return max_thread_count();
    return requested_threads;
#else
    (void)requested_threads;
    return 1;
#endif
}

int current_thread_id() {
#if PGSA_HAS_OPENMP
    return omp_get_thread_num();
#else
    return 0;
#endif
}

double current_peak_rss_mb() {
#if defined(__APPLE__) || defined(__linux__)
    rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0) return 0.0;
#if defined(__APPLE__)
    return static_cast<double>(usage.ru_maxrss) / (1024.0 * 1024.0);
#else
    return static_cast<double>(usage.ru_maxrss) / 1024.0;
#endif
#else
    return 0.0;
#endif
}

std::string environment_value_or_empty(const char* name) {
    return read_environment_value(name);
}

} // namespace fem
