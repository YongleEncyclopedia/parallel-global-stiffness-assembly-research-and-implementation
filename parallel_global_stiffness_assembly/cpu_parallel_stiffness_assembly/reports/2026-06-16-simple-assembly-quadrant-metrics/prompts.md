# Three-Platform Quadrant Redraw Prompts

Use these prompts when redrawing the same figures with an image-generation tool. Keep the three figures visually identical except for platform notes and numbers.

## Shared Requirements

Create a clean 16:9 scientific performance comparison slide, white background, NVIDIA technical talk style, rigorous not marketing-like. Use a simple 2x2 quadrant layout with clean metric cards. Do not include algorithm cartoons, CSR schematics, worker icons, dense matrices, arrows, stock imagery, decorative gradients, or extra visual metaphors.

Axes:
- x-axis title: "符号结构复用"; left label: "不复用 CSR/scatter"; right label: "复用 CSR/scatter"
- y-axis title: "执行方式"; bottom label: "串行"; top label: "并行"

Each quadrant card must show only:
- Q tag
- method name
- thread/backend line
- assembly time
- memory
- speedup vs Q1

Color mapping must be identical:
- Q1 serial direct: muted red
- Q2 serial symbolic + numeric: NVIDIA blue
- Q3 parallel direct: muted orange
- Q4 parallel symbolic + numeric: NVIDIA green, subtly highlighted as best

Footer for every figure:
"Draft corrected placeholder dataset; values marked † are estimates pending direct-serial retest. Speedup is relative to Q1. Do not mix this figure with previous wrong Q1 source."

## Prompt 1: macOS Apple M4 Max

Title: "Global stiffness matrix assembly strategy comparison - macOS Apple M4 Max"

Platform note:
"WindHub Tet4, Apple M4 Max, 14 physical cores; memory is pre-run lifecycle estimate, not OS peak capture."

Cards:
- Q1 bottom-left, muted red: "串行无符号直接"; "1 thread, direct/no-symbolic"; "5.20 s"; "预估内存 2.39 GiB"; "1.00x"
- Q2 bottom-right, NVIDIA blue: "串行有符号 + 数值"; "1 thread, cpu_serial"; "3.09 s"; "预估内存 0.96 GiB"; "1.68x"
- Q3 top-left, muted orange: "并行无符号直接"; "14 threads, direct/no-symbolic"; "1.67 s"; "预估内存 2.53 GiB†"; "3.11x"
- Q4 top-right, NVIDIA green and best-highlighted: "并行有符号 + 数值"; "14 threads, cpu_atomic"; "662 ms"; "预估内存 1.10 GiB"; "7.86x"

## Prompt 2: Linux Intel

Title: "Global stiffness matrix assembly strategy comparison - Linux Intel"

Platform note:
"WindHub Tet4 physics_tet4, Intel Core Ultra 7 265KF, 20 physical cores; memory is isolated process peak RSS."

Cards:
- Q1 bottom-left, muted red: "串行无符号直接"; "1 thread, direct/no-symbolic"; "10.21 s†"; "OS peak RSS 3.30 GiB†"; "1.00x"
- Q2 bottom-right, NVIDIA blue: "串行有符号 + 数值"; "1 thread, cpu_serial"; "4.39 s"; "OS peak RSS 2.72 GiB"; "2.33x"
- Q3 top-left, muted orange: "并行无符号直接"; "20 threads, direct/no-symbolic"; "2.64 s"; "OS peak RSS 3.75 GiB"; "3.87x"
- Q4 top-right, NVIDIA green and best-highlighted: "并行有符号 + 数值"; "20 threads, cpu_atomic"; "917 ms"; "OS peak RSS 3.28 GiB"; "11.14x"

## Prompt 3: Windows AMD

Title: "Global stiffness matrix assembly strategy comparison - Windows AMD"

Platform note:
"WindHub Tet4 linear_elastic_solid, Windows AMD, 8-thread sweep; memory is GetProcessMemoryInfo peak working set."

Cards:
- Q1 bottom-left, muted red: "串行无符号直接"; "1 thread, direct/no-symbolic"; "8.02 s†"; "OS peak working set 3.20 GiB†"; "1.00x"
- Q2 bottom-right, NVIDIA blue: "串行有符号 + 数值"; "1 thread, cpu_serial"; "4.08 s"; "OS peak working set 2.26 GiB"; "1.97x"
- Q3 top-left, muted orange: "并行无符号直接"; "8 threads, direct/no-symbolic"; "2.15 s"; "OS peak working set 3.65 GiB"; "3.73x"
- Q4 top-right, NVIDIA green and best-highlighted: "并行有符号 + 数值"; "8 threads, cpu_atomic"; "1.13 s"; "OS peak working set 2.32 GiB"; "7.10x"
