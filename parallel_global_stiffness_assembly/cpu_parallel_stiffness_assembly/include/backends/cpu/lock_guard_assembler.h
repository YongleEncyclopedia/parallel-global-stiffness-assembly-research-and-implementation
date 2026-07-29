// 互斥锁后端：线程共享全局 CSR，写入一个条目前先取得对应的锁。
#pragma once

#include "backends/cpu/cpu_assembler_base.h"

#include <memory>
#include <mutex>

namespace fem::cpu {

class LockGuardAssembler final : public CpuAssemblerBase {
public:
    explicit LockGuardAssembler(AssemblyOptions options);
    void prepare() override;
    void assemble() override;
    void cleanup() override;
    [[nodiscard]] std::string get_name() const override { return "cpu_lock_guard"; }
    [[nodiscard]] AlgorithmType get_type() const override { return AlgorithmType::CpuLockGuard; }

private:
    std::unique_ptr<std::mutex[]> entry_mutexes_;
    Size entry_mutex_count_ = 0;
};

} // namespace fem::cpu
