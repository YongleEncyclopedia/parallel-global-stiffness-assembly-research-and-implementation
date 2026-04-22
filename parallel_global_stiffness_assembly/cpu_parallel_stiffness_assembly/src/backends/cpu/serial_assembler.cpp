#include "backends/cpu/serial_assembler.h"

#include <chrono>

namespace fem::cpu {

SerialAssembler::SerialAssembler(AssemblyOptions options) : CpuAssemblerBase(options) {}

void SerialAssembler::assemble() {
    ensure_ready();
    reset_result();
    const auto t0 = std::chrono::steady_clock::now();
    std::vector<Real> ke;
    for (Size e = 0; e < mesh_->num_elements(); ++e) {
        compute_element_matrix(*mesh_, e, options_, ke);
        add_element_to_result(e, ke);
    }
    const auto t1 = std::chrono::steady_clock::now();
    stats_.assembly_time_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    stats_.total_time_ms = stats_.preprocess_time_ms + stats_.assembly_time_ms;
}

} // namespace fem::cpu
