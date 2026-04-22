#include "core/platform.h"

#include <sstream>
#include <thread>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace fem {

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

#ifdef _OPENMP
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

int max_thread_count() {
#ifdef _OPENMP
    return omp_get_max_threads();
#else
    const auto n = std::thread::hardware_concurrency();
    return n == 0 ? 1 : static_cast<int>(n);
#endif
}

int effective_thread_count(int requested_threads) {
    if (requested_threads <= 0) return max_thread_count();
    return requested_threads;
}

int current_thread_id() {
#ifdef _OPENMP
    return omp_get_thread_num();
#else
    return 0;
#endif
}

} // namespace fem
