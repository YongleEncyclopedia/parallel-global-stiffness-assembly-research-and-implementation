function plot_stiffness_pattern_matlab(serial_csv, parallel_csv, out_base, title_text)
% Generate MATLAB spy-style sparse stiffness pattern figures.
%
% Usage from shell:
% matlab -batch "addpath('scripts'); plot_stiffness_pattern_matlab('serial.csv','parallel.csv','out/pattern','WindHub sparse pattern')"

if nargin < 4
    title_text = 'WindHub stiffness sparse pattern';
end

serial_table = readtable(serial_csv);
parallel_table = readtable(parallel_csv);
n = max([serial_table.row; serial_table.col; parallel_table.row; parallel_table.col]) + 1;

bins = min(1800, n);
serial_r = min(bins, floor(double(serial_table.row) * bins / max(1, n - 1)) + 1);
serial_c = min(bins, floor(double(serial_table.col) * bins / max(1, n - 1)) + 1);
parallel_r = min(bins, floor(double(parallel_table.row) * bins / max(1, n - 1)) + 1);
parallel_c = min(bins, floor(double(parallel_table.col) * bins / max(1, n - 1)) + 1);

serial_image = false(bins, bins);
parallel_image = false(bins, bins);
serial_image(sub2ind([bins, bins], serial_r, serial_c)) = true;
parallel_image(sub2ind([bins, bins], parallel_r, parallel_c)) = true;

fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1400 700]);
tiledlayout(fig, 1, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

nexttile;
imagesc([0 n], [0 n], serial_image);
colormap(flipud(gray));
caxis([0 1]);
set(gca, 'YDir', 'reverse');
axis square;
title(sprintf('Serial CSR pattern\\nn=%d, nnz=%d, raster=%dx%d', n, height(serial_table), bins, bins), 'Interpreter', 'none');
xlabel('column');
ylabel('row');

nexttile;
imagesc([0 n], [0 n], parallel_image);
colormap(flipud(gray));
caxis([0 1]);
set(gca, 'YDir', 'reverse');
axis square;
title(sprintf('Parallel assembled pattern\\nn=%d, nnz=%d, raster=%dx%d', n, height(parallel_table), bins, bins), 'Interpreter', 'none');
xlabel('column');
ylabel('row');

sgtitle(title_text, 'Interpreter', 'none', 'FontWeight', 'bold');
saveas(fig, strcat(out_base, '.png'));
saveas(fig, strcat(out_base, '.svg'));
close(fig);
end
