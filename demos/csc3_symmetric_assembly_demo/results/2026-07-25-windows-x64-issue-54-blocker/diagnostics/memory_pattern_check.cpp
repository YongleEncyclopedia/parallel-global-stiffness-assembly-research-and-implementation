#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <psapi.h>

#include <algorithm>
#include <cinttypes>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>

namespace {

constexpr std::uint64_t kGibibyte = 1024ULL * 1024ULL * 1024ULL;
constexpr std::uint64_t kDefaultBytes = 8ULL * kGibibyte;
constexpr std::size_t kMaximumPrintedMismatches = 32;

std::uint64_t splitmix64(std::uint64_t value) noexcept {
    value += 0x9E3779B97F4A7C15ULL;
    value = (value ^ (value >> 30U)) * 0xBF58476D1CE4E5B9ULL;
    value = (value ^ (value >> 27U)) * 0x94D049BB133111EBULL;
    return value ^ (value >> 31U);
}

std::uint64_t expected_value(std::size_t pass, std::uint64_t index) noexcept {
    switch (pass) {
    case 0:
        return 0x4246C99787241DC5ULL;
    case 1:
        return 0x0000000000000000ULL;
    case 2:
        return 0xFFFFFFFFFFFFFFFFULL;
    default:
        return splitmix64(index ^ 0x54C5C3A55AA55AA5ULL);
    }
}

} // namespace

int main(int argc, char** argv) {
    std::uint64_t bytes = kDefaultBytes;
    if (argc == 2) {
        char* end = nullptr;
        const unsigned long long parsed = std::strtoull(argv[1], &end, 10);
        if (end == argv[1] || *end != '\0' || parsed == 0 ||
            parsed > std::numeric_limits<std::size_t>::max()) {
            std::fprintf(stderr, "invalid byte count\n");
            return 64;
        }
        bytes = parsed;
    }
    bytes -= bytes % sizeof(std::uint64_t);
    const std::size_t count = static_cast<std::size_t>(bytes / sizeof(std::uint64_t));

    auto* memory = static_cast<std::uint64_t*>(
        VirtualAlloc(nullptr, static_cast<SIZE_T>(bytes),
                     MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE));
    if (memory == nullptr) {
        std::fprintf(stderr, "VirtualAlloc failed: error=%lu bytes=%" PRIu64 "\n",
                     GetLastError(), bytes);
        return 65;
    }

    std::uint64_t checksum = 0;
    std::uint64_t total_mismatches = 0;
    for (std::size_t pass = 0; pass < 4; ++pass) {
        for (std::uint64_t index = 0; index < count; ++index) {
            memory[index] = expected_value(pass, index);
        }
        FlushProcessWriteBuffers();

        std::uint64_t pass_mismatches = 0;
        for (std::uint64_t index = 0; index < count; ++index) {
            const std::uint64_t expected = expected_value(pass, index);
            const std::uint64_t observed = memory[index];
            checksum ^= observed + index;
            if (observed != expected) {
                if (total_mismatches < kMaximumPrintedMismatches) {
                    std::printf(
                        "MISMATCH pass=%zu index=%" PRIu64
                        " expected=0x%016" PRIX64 " observed=0x%016" PRIX64
                        " xor=0x%016" PRIX64 "\n",
                        pass, index, expected, observed, expected ^ observed);
                }
                ++pass_mismatches;
                ++total_mismatches;
            }
        }
        std::printf("PASS_SCAN pass=%zu bytes=%" PRIu64
                    " mismatches=%" PRIu64 "\n",
                    pass, bytes, pass_mismatches);
        std::fflush(stdout);
    }

    PROCESS_MEMORY_COUNTERS counters{};
    counters.cb = sizeof(counters);
    const BOOL memory_info_ok =
        GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters));
    std::printf(
        "RESULT status=%s bytes=%" PRIu64 " passes=4 mismatches=%" PRIu64
        " checksum=0x%016" PRIX64 " peak_working_set_bytes=%zu"
        " memory_info_ok=%d\n",
        total_mismatches == 0 ? "PASS" : "FAIL", bytes, total_mismatches,
        checksum, memory_info_ok ? static_cast<std::size_t>(counters.PeakWorkingSetSize) : 0U,
        memory_info_ok ? 1 : 0);
    VirtualFree(memory, 0, MEM_RELEASE);
    return total_mismatches == 0 ? 0 : 2;
}
