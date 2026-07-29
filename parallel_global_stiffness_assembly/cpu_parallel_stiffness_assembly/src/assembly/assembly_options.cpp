// 提供一份默认 AssemblyOptions，供未显式指定参数的调用者使用。
#include "assembly/assembly_options.h"

namespace fem {
AssemblyOptions make_default_options() { return AssemblyOptions{}; }
} // namespace fem
