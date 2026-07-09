function plot_monthly_assembly_quadrants_revised_matlab(source_csv, out_root, formats)
% Draw the revised monthly assembly quadrant figure with MATLAB graphics.
%
% Example:
% matlab -batch "addpath('scripts'); plot_monthly_assembly_quadrants_revised_matlab('reports/2026-05-27-assembly-quadrants/source_data/quadrant_selected_rows.csv','reports/2026-06-12-assembly-quadrants-revision','svg,pdf,png')"

if nargin < 1 || strlength(string(source_csv)) == 0
    source_csv = fullfile(project_root(), 'reports', '2026-05-27-assembly-quadrants', 'source_data', 'quadrant_selected_rows.csv');
end
if nargin < 2 || strlength(string(out_root)) == 0
    out_root = fullfile(project_root(), 'reports', '2026-06-12-assembly-quadrants-revision');
end
if nargin < 3 || strlength(string(formats)) == 0
    formats = 'svg,pdf,png';
end

source_csv = char(source_csv);
out_root = char(out_root);
formats = split(string(formats), ",");
formats = lower(strtrim(formats(strlength(strtrim(formats)) > 0)));

opts = detectImportOptions(source_csv, 'Encoding', 'UTF-8', 'VariableNamingRule', 'preserve');
T = readtable(source_csv, opts);
T.persistent_symbolic_gib = T.csr_gib + T.plan_gib;
metrics = compute_metrics(T);

out_dir = fullfile(out_root, 'matlab');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end
source_dir = fullfile(out_root, 'source_data');
if ~exist(source_dir, 'dir')
    mkdir(source_dir);
end
copyfile(source_csv, fullfile(source_dir, 'quadrant_selected_rows.csv'));

fig = make_main_figure(T, metrics);
export_all(fig, fullfile(out_dir, 'assembly_quadrants_revised.matlab'), formats);
close(fig);

fig = figure('Color', 'white', 'Units', 'pixels', 'Position', [100 100 1200 540]);
ax = axes(fig, 'Position', [0.03 0.05 0.94 0.90]);
draw_direct_schematic(ax);
export_all(fig, fullfile(out_dir, 'direct_assembly_schematic.matlab'), formats);
close(fig);

fig = figure('Color', 'white', 'Units', 'pixels', 'Position', [100 100 1200 540]);
ax = axes(fig, 'Position', [0.03 0.05 0.94 0.90]);
draw_two_stage_schematic(ax);
export_all(fig, fullfile(out_dir, 'two_stage_assembly_schematic.matlab'), formats);
close(fig);

fprintf('MATLAB candidate written to %s\n', out_dir);
end

function root = project_root()
this_file = mfilename('fullpath');
root = fileparts(fileparts(this_file));
end

function metrics = compute_metrics(T)
sd = route(T, 'serial_direct');
ss = route(T, 'serial_symbolic');
pd = route(T, 'parallel_direct');
ps = route(T, 'parallel_symbolic');
metrics.serial_symbolic_vs_serial_direct = sd.total_ms / ss.total_ms;
metrics.parallel_symbolic_vs_serial_symbolic = ss.total_ms / ps.total_ms;
metrics.parallel_symbolic_vs_parallel_direct = pd.total_ms / ps.total_ms;
metrics.parallel_symbolic_vs_serial_direct = sd.total_ms / ps.total_ms;
assert(abs(metrics.serial_symbolic_vs_serial_direct - 1.6826022961518814) < 1e-9);
assert(abs(metrics.parallel_symbolic_vs_serial_symbolic - 4.668155618564831) < 1e-9);
assert(abs(metrics.parallel_symbolic_vs_parallel_direct - 2.520166069480942) < 1e-9);
assert(abs(metrics.parallel_symbolic_vs_serial_direct - 7.85464936259149) < 1e-9);
end

function r = route(T, key)
idx = strcmp(T.key, key);
if ~any(idx)
    error('Missing route row: %s', key);
end
r = T(find(idx, 1), :);
end

function c = colors(name)
switch name
    case 'ink', c = [23 33 43] / 255;
    case 'muted', c = [102 112 133] / 255;
    case 'grid', c = [215 221 228] / 255;
    case 'direct', c = [216 132 58] / 255;
    case 'generate', c = [233 184 94] / 255;
    case 'bucket', c = [216 132 58] / 255;
    case 'sort', c = [198 96 90] / 255;
    case 'symbolic', c = [95 135 200] / 255;
    case 'scatter', c = [126 106 174] / 255;
    case 'numeric', c = [60 154 122] / 255;
    case 'gain', c = [47 133 90] / 255;
    case 'light_direct', c = [247 228 204] / 255;
    case 'light_sort', c = [242 217 214] / 255;
    case 'light_symbolic', c = [220 232 246] / 255;
    case 'light_scatter', c = [230 224 242] / 255;
    case 'light_numeric', c = [220 239 232] / 255;
    otherwise, c = [1 1 1];
end
end

function s = fmt_time(ms)
if ms >= 1000
    s = sprintf('%.2f s', ms / 1000);
else
    s = sprintf('%.0f ms', ms);
end
end

function fig = make_main_figure(T, metrics)
fig = figure('Color', 'white', 'Units', 'pixels', 'Position', [100 100 1920 1080]);
annotation(fig, 'textbox', [0.055 0.925 0.75 0.05], 'String', '四类刚度组装路线：时间优先，内存为辅', 'EdgeColor', 'none', 'FontSize', 24, 'FontWeight', 'bold', 'Color', colors('ink'), 'FontName', 'Arial Unicode MS');
annotation(fig, 'textbox', [0.055 0.895 0.80 0.04], 'String', 'WindHub Tet4 / Apple M4 Max；total time includes symbolic/direct construction and numeric assembly', 'EdgeColor', 'none', 'FontSize', 11, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS');
annotation(fig, 'line', [0.055 0.945], [0.885 0.885], 'Color', colors('grid'));

ax1 = axes(fig, 'Position', [0.055 0.69 0.43 0.20]);
draw_direct_schematic(ax1);
ax2 = axes(fig, 'Position', [0.515 0.69 0.43 0.20]);
draw_two_stage_schematic(ax2);

ax3 = axes(fig, 'Position', [0.09 0.31 0.58 0.30]);
draw_timing_panel(ax3, T);
ax4 = axes(fig, 'Position', [0.715 0.29 0.23 0.34]);
draw_badges(ax4, metrics);
ax5 = axes(fig, 'Position', [0.09 0.075 0.82 0.15]);
draw_memory_panel(ax5, T);
annotation(fig, 'textbox', [0.055 0.01 0.88 0.03], 'String', 'Source: curated WindHub / Apple M4 Max quadrant rows; direct/no-symbolic is contribution-list sort/reduce, not a dense matrix.', 'EdgeColor', 'none', 'FontSize', 9, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS');
end

function draw_direct_schematic(ax)
cla(ax);
axis(ax, [0 1 0 1]);
axis(ax, 'off');
hold(ax, 'on');
rectangle(ax, 'Position', [0.01 0.03 0.98 0.94], 'Curvature', 0.08, 'FaceColor', [1.0 0.98 0.95], 'EdgeColor', colors('direct'), 'LineWidth', 1.4);
text(ax, 0.05, 0.87, '直接组装算法', 'FontSize', 16, 'FontWeight', 'bold', 'Color', colors('direct'), 'FontName', 'Arial Unicode MS');
text(ax, 0.05, 0.76, 'element contributions → triples → bucket/merge → sort/reduce → CSR', 'FontSize', 10, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS');
draw_box(ax, [0.05 0.46 0.18 0.20], {'element', 'contrib.'}, 'light_direct', 'direct');
draw_box(ax, [0.31 0.43 0.18 0.26], {'(row,col,value)', 'triples'}, 'white', 'direct');
draw_box(ax, [0.57 0.59 0.19 0.12], 'bucket/merge', 'light_direct', 'bucket');
draw_box(ax, [0.57 0.37 0.19 0.12], 'sort/reduce', 'light_sort', 'sort');
draw_matrix(ax, 0.83, 0.38, 0.12, 0.25, 'sort');
draw_arrow(ax, [0.23 0.56], [0.31 0.56], 'direct');
draw_arrow(ax, [0.49 0.56], [0.57 0.65], 'direct');
draw_arrow(ax, [0.665 0.59], [0.665 0.49], 'sort');
draw_arrow(ax, [0.76 0.43], [0.83 0.50], 'sort');
text(ax, 0.05, 0.15, '每轮保留 transient buffer；无法复用 CSR/scatter。', 'FontSize', 10, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS');
hold(ax, 'off');
end

function draw_two_stage_schematic(ax)
cla(ax);
axis(ax, [0 1 0 1]);
axis(ax, 'off');
hold(ax, 'on');
rectangle(ax, 'Position', [0.01 0.03 0.98 0.94], 'Curvature', 0.08, 'FaceColor', [0.96 0.99 0.97], 'EdgeColor', colors('numeric'), 'LineWidth', 1.4);
text(ax, 0.05, 0.87, '两阶段组装算法', 'FontSize', 16, 'FontWeight', 'bold', 'Color', colors('numeric'), 'FontName', 'Arial Unicode MS');
text(ax, 0.05, 0.76, 'symbolic builds reusable CSR/scatter → numeric scatters values', 'FontSize', 10, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS');
draw_box(ax, [0.05 0.46 0.18 0.20], {'element', 'connectivity'}, 'light_symbolic', 'symbolic');
draw_box(ax, [0.31 0.50 0.17 0.13], 'symbolic', 'light_symbolic', 'symbolic');
draw_matrix(ax, 0.55, 0.39, 0.17, 0.29, 'symbolic');
text(ax, 0.635, 0.31, 'CSR + scatter reusable', 'FontSize', 9, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS', 'HorizontalAlignment', 'center');
draw_box(ax, [0.80 0.43 0.12 0.22], 'values', 'light_numeric', 'numeric');
draw_arrow(ax, [0.23 0.56], [0.31 0.56], 'symbolic');
draw_arrow(ax, [0.48 0.56], [0.55 0.55], 'symbolic');
draw_arrow(ax, [0.72 0.61], [0.80 0.59], 'numeric');
draw_arrow(ax, [0.72 0.52], [0.80 0.51], 'numeric');
draw_arrow(ax, [0.72 0.43], [0.80 0.44], 'numeric');
text(ax, 0.05, 0.15, 'symbolic 可并行且可复用；numeric 只 scatter 到 values。', 'FontSize', 10, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS');
hold(ax, 'off');
end

function draw_box(ax, pos, label, fill_name, edge_name)
rectangle(ax, 'Position', pos, 'Curvature', 0.15, 'FaceColor', colors(fill_name), 'EdgeColor', colors(edge_name), 'LineWidth', 1.2);
text(ax, pos(1) + pos(3) / 2, pos(2) + pos(4) / 2, label, 'FontSize', 10, 'Color', colors('ink'), 'FontName', 'Arial Unicode MS', 'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');
end

function draw_matrix(ax, x, y, w, h, color_name)
rectangle(ax, 'Position', [x y w h], 'FaceColor', 'white', 'EdgeColor', colors(color_name), 'LineWidth', 1.1);
for i = 1:5
    line(ax, [x + w * i / 5, x + w * i / 5], [y, y + h], 'Color', colors('grid'), 'LineWidth', 0.5);
    line(ax, [x, x + w], [y + h * i / 5, y + h * i / 5], 'Color', colors('grid'), 'LineWidth', 0.5);
end
pts = [0.15 0.82; 0.36 0.65; 0.58 0.48; 0.78 0.30; 0.78 0.12];
scatter(ax, x + pts(:, 1) * w, y + pts(:, 2) * h, 32, colors(color_name), 'filled');
end

function draw_arrow(ax, p1, p2, color_name)
quiver(ax, p1(1), p1(2), p2(1) - p1(1), p2(2) - p1(2), 0, 'Color', colors(color_name), 'LineWidth', 1.2, 'MaxHeadSize', 0.35);
end

function draw_timing_panel(ax, T)
cla(ax);
order = {'serial_direct', 'serial_symbolic', 'parallel_direct', 'parallel_symbolic'};
yticks = numel(order):-1:1;
hold(ax, 'on');
max_s = max(T.total_ms) / 1000;
for i = 1:numel(order)
    r = route(T, order{i});
    y = yticks(i);
    if startsWith(string(r.mode), "direct")
        parts = {'generate', r.direct_generate_ms; 'bucket', r.direct_bucket_merge_ms; 'sort', r.direct_sort_reduce_ms};
    else
        csr_ms = r.symbolic_ms * r.csr_gib / max(r.csr_gib + r.plan_gib, eps);
        parts = {'symbolic', csr_ms; 'scatter', r.symbolic_ms - csr_ms; 'numeric', r.numeric_ms};
    end
    left = 0;
    for j = 1:size(parts, 1)
        name = parts{j, 1};
        value = parts{j, 2} / 1000;
        rectangle(ax, 'Position', [left, y - 0.25, value, 0.5], 'FaceColor', light_for(name), 'EdgeColor', colors(name), 'LineWidth', 1.0);
        if value > 0.35
            text(ax, left + value / 2, y, fmt_time(parts{j, 2}), 'HorizontalAlignment', 'center', 'FontSize', 9, 'FontName', 'Arial Unicode MS', 'Color', colors('ink'));
        end
        left = left + value;
    end
    text(ax, -0.16, y, sprintf('%s\n%d thread(s)', string(r.label), r.threads), 'HorizontalAlignment', 'right', 'FontSize', 10, 'FontName', 'Arial Unicode MS', 'Color', colors('ink'));
    text(ax, left + 0.10, y, fmt_time(r.total_ms), 'FontWeight', 'bold', 'FontSize', 13, 'FontName', 'Arial Unicode MS', 'Color', colors('ink'));
end
xlim(ax, [0, max_s * 1.22]);
ylim(ax, [0.35, numel(order) + 0.65]);
set(ax, 'YTick', [], 'Box', 'off', 'FontName', 'Arial Unicode MS', 'XColor', colors('muted'), 'YColor', colors('muted'), 'GridColor', colors('grid'));
grid(ax, 'on');
title(ax, '四类路线端到端耗时构成', 'FontName', 'Arial Unicode MS', 'FontWeight', 'bold', 'Color', colors('ink'));
xlabel(ax, '');
hold(ax, 'off');
end

function c = light_for(name)
switch char(name)
    case {'generate', 'bucket'}, c = colors('light_direct');
    case 'sort', c = colors('light_sort');
    case 'symbolic', c = colors('light_symbolic');
    case 'scatter', c = colors('light_scatter');
    case 'numeric', c = colors('light_numeric');
    otherwise, c = [1 1 1];
end
end

function draw_badges(ax, metrics)
cla(ax);
axis(ax, [0 1 0 1]);
axis(ax, 'off');
text(ax, 0.02, 0.93, '对比结论', 'FontSize', 15, 'FontWeight', 'bold', 'Color', colors('ink'), 'FontName', 'Arial Unicode MS');
items = {
    sprintf('%.2fx', metrics.serial_symbolic_vs_serial_direct), '串行：有符号优于无符号', '5.20 s → 3.09 s';
    sprintf('%.2fx', metrics.parallel_symbolic_vs_serial_symbolic), '并行符号优于串行符号', '3.09 s → 662 ms';
    sprintf('%.2fx', metrics.parallel_symbolic_vs_parallel_direct), '同为 14 线程：有符号优于 direct', '1.67 s → 662 ms';
    sprintf('%.2fx', metrics.parallel_symbolic_vs_serial_direct), '最佳路线相对串行 direct', '5.20 s → 662 ms'
};
for i = 1:size(items, 1)
    y = 0.74 - (i - 1) * 0.205;
    rectangle(ax, 'Position', [0.02 y 0.94 0.155], 'Curvature', 0.18, 'FaceColor', [0.965 0.99 0.97], 'EdgeColor', colors('gain'), 'LineWidth', 1.1);
    text(ax, 0.08, y + 0.083, items{i, 1}, 'FontSize', 18, 'FontWeight', 'bold', 'Color', colors('gain'), 'FontName', 'Arial Unicode MS');
    text(ax, 0.36, y + 0.105, items{i, 2}, 'FontSize', 10, 'FontWeight', 'bold', 'Color', colors('ink'), 'FontName', 'Arial Unicode MS');
    text(ax, 0.36, y + 0.052, items{i, 3}, 'FontSize', 10, 'Color', colors('muted'), 'FontName', 'Arial Unicode MS');
end
end

function draw_memory_panel(ax, T)
cla(ax);
order = {'serial_direct', 'serial_symbolic', 'parallel_direct', 'parallel_symbolic'};
yticks = numel(order):-1:1;
max_mem = max(T.persistent_symbolic_gib + T.symbolic_temp_gib + T.direct_transient_gib);
hold(ax, 'on');
for i = 1:numel(order)
    r = route(T, order{i});
    y = yticks(i);
    parts = {'symbolic', r.persistent_symbolic_gib; 'scatter', r.symbolic_temp_gib; 'sort', r.direct_transient_gib};
    left = 0;
    for j = 1:size(parts, 1)
        name = parts{j, 1};
        value = parts{j, 2};
        if value <= 0
            continue;
        end
        rectangle(ax, 'Position', [left, y - 0.24, value, 0.48], 'FaceColor', light_for(name), 'EdgeColor', colors(name), 'LineWidth', 1.0);
        if value > 0.18
            text(ax, left + value / 2, y, sprintf('%.2f', value), 'HorizontalAlignment', 'center', 'FontSize', 8, 'FontName', 'Arial Unicode MS', 'Color', colors('ink'));
        elseif strcmp(order{i}, 'parallel_symbolic') && strcmp(name, 'scatter')
            text(ax, left + value + 0.04, y + 0.23, sprintf('+%.2f temp', value), 'HorizontalAlignment', 'left', 'FontSize', 8, 'FontName', 'Arial Unicode MS', 'Color', colors('scatter'));
        end
        left = left + value;
    end
    text(ax, -0.08, y, string(r.label), 'HorizontalAlignment', 'right', 'FontSize', 9, 'FontName', 'Arial Unicode MS', 'Color', colors('ink'));
    text(ax, left + 0.05, y, sprintf('%.2f GiB', left), 'FontWeight', 'bold', 'FontSize', 10, 'FontName', 'Arial Unicode MS', 'Color', colors('ink'));
end
xlim(ax, [0, max_mem * 1.22]);
ylim(ax, [0.35, numel(order) + 0.65]);
set(ax, 'YTick', [], 'Box', 'off', 'FontName', 'Arial Unicode MS', 'XColor', colors('muted'), 'YColor', colors('muted'), 'GridColor', colors('grid'));
grid(ax, 'on');
title(ax, '内存占用（辅证）', 'FontName', 'Arial Unicode MS', 'FontWeight', 'bold', 'Color', colors('ink'));
xlabel(ax, '可解释数据结构内存 / GiB', 'FontName', 'Arial Unicode MS', 'Color', colors('muted'));
hold(ax, 'off');
end

function export_all(fig, out_base, formats)
set(fig, 'InvertHardcopy', 'off');
set(fig, 'Units', 'pixels');
pos = get(fig, 'Position');
paper_w = pos(3) / 120;
paper_h = pos(4) / 120;
set(fig, 'PaperUnits', 'inches');
set(fig, 'PaperSize', [paper_w paper_h]);
set(fig, 'PaperPosition', [0 0 paper_w paper_h]);
set(fig, 'PaperPositionMode', 'manual');
for i = 1:numel(formats)
    fmt = char(formats(i));
    target = char(string(out_base) + "." + string(fmt));
    switch fmt
        case 'svg'
            print(fig, target, '-dsvg', '-painters');
        case 'pdf'
            print(fig, target, '-dpdf', '-painters');
        case 'png'
            print(fig, target, '-dpng', '-r300');
        otherwise
            error('Unsupported format: %s', fmt);
    end
end
end
