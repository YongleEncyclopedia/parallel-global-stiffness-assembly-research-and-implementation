#!/usr/bin/env Rscript
# Draw the revised monthly assembly quadrant figure with ggplot2/patchwork.

required_packages <- c("ggplot2", "patchwork", "svglite", "ragg")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages) > 0) {
  stop(sprintf("Missing R package(s): %s", paste(missing_packages, collapse = ", ")), call. = FALSE)
}

library(ggplot2)
library(patchwork)

`%||%` <- function(a, b) {
  if (!is.null(a) && length(a) > 0 && !is.na(a)) a else b
}

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
script_path <- normalizePath(sub("^--file=", "", script_arg[1] %||% "scripts/plot_monthly_assembly_quadrants_revised.R"), mustWork = FALSE)
project_root <- normalizePath(file.path(dirname(script_path), ".."), mustWork = FALSE)
default_source_csv <- file.path(project_root, "reports", "2026-05-27-assembly-quadrants", "source_data", "quadrant_selected_rows.csv")
default_out_root <- file.path(project_root, "reports", "2026-06-12-assembly-quadrants-revision")

parse_args <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  value_after <- function(flag, default) {
    hit <- which(args == flag)
    if (length(hit) == 0 || hit[length(hit)] == length(args)) return(default)
    args[hit[length(hit)] + 1]
  }
  list(
    source_csv = value_after("--source-csv", default_source_csv),
    out_root = value_after("--out-root", default_out_root),
    formats = strsplit(value_after("--format", "svg,pdf,png"), ",", fixed = TRUE)[[1]]
  )
}

palette <- list(
  ink = "#17212B",
  muted = "#667085",
  grid = "#D7DDE4",
  direct = "#D8843A",
  generate = "#E9B85E",
  bucket = "#D8843A",
  sort = "#C6605A",
  symbolic = "#5F87C8",
  scatter = "#7E6AAE",
  numeric = "#3C9A7A",
  gain = "#2F855A",
  light_direct = "#F7E4CC",
  light_sort = "#F2D9D6",
  light_symbolic = "#DCE8F6",
  light_scatter = "#E6E0F2",
  light_numeric = "#DCEFE8"
)

theme_pgsa <- function(base_size = 9) {
  theme_minimal(base_size = base_size, base_family = "Arial Unicode MS") +
    theme(
      plot.title = element_text(face = "bold", colour = palette$ink),
      plot.subtitle = element_text(colour = palette$muted),
      axis.title = element_text(colour = palette$muted),
      axis.text = element_text(colour = palette$muted),
      panel.grid.major.y = element_blank(),
      panel.grid.minor = element_blank(),
      legend.position = "bottom",
      legend.title = element_blank()
    )
}

fmt_time <- function(ms) {
  ifelse(ms >= 1000, sprintf("%.2f s", ms / 1000), sprintf("%.0f ms", ms))
}

load_rows <- function(source_csv) {
  rows <- read.csv(source_csv, stringsAsFactors = FALSE, check.names = FALSE, fileEncoding = "UTF-8")
  required <- c("serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic")
  missing <- setdiff(required, rows$key)
  if (length(missing) > 0) stop(sprintf("Missing route row(s): %s", paste(missing, collapse = ", ")))
  rows$persistent_symbolic_gib <- rows$csr_gib + rows$plan_gib
  rows
}

metrics_from_rows <- function(rows) {
  by_key <- split(rows, rows$key)
  metrics <- c(
    serial_symbolic_vs_serial_direct = by_key$serial_direct$total_ms / by_key$serial_symbolic$total_ms,
    parallel_symbolic_vs_serial_symbolic = by_key$serial_symbolic$total_ms / by_key$parallel_symbolic$total_ms,
    parallel_symbolic_vs_parallel_direct = by_key$parallel_direct$total_ms / by_key$parallel_symbolic$total_ms,
    parallel_symbolic_vs_serial_direct = by_key$serial_direct$total_ms / by_key$parallel_symbolic$total_ms
  )
  stopifnot(abs(metrics[["serial_symbolic_vs_serial_direct"]] - 1.6826022961518814) < 1e-9)
  stopifnot(abs(metrics[["parallel_symbolic_vs_serial_symbolic"]] - 4.668155618564831) < 1e-9)
  stopifnot(abs(metrics[["parallel_symbolic_vs_parallel_direct"]] - 2.520166069480942) < 1e-9)
  stopifnot(abs(metrics[["parallel_symbolic_vs_serial_direct"]] - 7.85464936259149) < 1e-9)
  metrics
}

direct_schematic <- function() {
  ggplot() +
    annotate("rect", xmin = 0, xmax = 1, ymin = 0, ymax = 1, fill = "#FFF9F1", colour = palette$direct, linewidth = 0.8) +
    annotate("text", x = 0.04, y = 0.88, label = "直接组装算法", hjust = 0, size = 5, fontface = "bold", colour = palette$direct, family = "Arial Unicode MS") +
    annotate("text", x = 0.04, y = 0.76, label = "element contributions → triples → bucket/merge → sort/reduce → CSR", hjust = 0, size = 3.1, colour = palette$muted, family = "Arial Unicode MS") +
    annotate("label", x = 0.15, y = 0.50, label = "element\ncontrib.", fill = palette$light_direct, colour = palette$direct, label.size = 0.35, size = 3.1, family = "Arial Unicode MS") +
    annotate("label", x = 0.39, y = 0.50, label = "(row,col,value)\ntriples", fill = "white", colour = palette$direct, label.size = 0.35, size = 3.0, family = "Arial Unicode MS") +
    annotate("label", x = 0.64, y = 0.60, label = "bucket/merge", fill = palette$light_direct, colour = palette$bucket, label.size = 0.35, size = 3.0, family = "Arial Unicode MS") +
    annotate("label", x = 0.64, y = 0.40, label = "sort/reduce", fill = palette$light_sort, colour = palette$sort, label.size = 0.35, size = 3.0, family = "Arial Unicode MS") +
    annotate("rect", xmin = 0.84, xmax = 0.95, ymin = 0.36, ymax = 0.62, fill = "white", colour = palette$sort, linewidth = 0.6) +
    annotate("point", x = c(0.86, 0.89, 0.92, 0.935), y = c(0.58, 0.53, 0.47, 0.40), colour = palette$sort, size = 2) +
    annotate("segment", x = c(0.23, 0.49, 0.64, 0.74), xend = c(0.32, 0.57, 0.64, 0.84), y = c(0.50, 0.50, 0.55, 0.40), yend = c(0.50, 0.60, 0.46, 0.49), arrow = arrow(length = unit(0.12, "inches")), colour = palette$direct, linewidth = 0.6) +
    annotate("text", x = 0.04, y = 0.14, label = "每轮保留 transient buffer；无法复用 CSR/scatter。", hjust = 0, size = 3.0, colour = palette$muted, family = "Arial Unicode MS") +
    coord_cartesian(xlim = c(0, 1), ylim = c(0, 1), expand = FALSE) +
    theme_void()
}

two_stage_schematic <- function() {
  ggplot() +
    annotate("rect", xmin = 0, xmax = 1, ymin = 0, ymax = 1, fill = "#F4FAF7", colour = palette$numeric, linewidth = 0.8) +
    annotate("text", x = 0.04, y = 0.88, label = "两阶段组装算法", hjust = 0, size = 5, fontface = "bold", colour = palette$numeric, family = "Arial Unicode MS") +
    annotate("text", x = 0.04, y = 0.76, label = "symbolic builds reusable CSR/scatter → numeric scatters values", hjust = 0, size = 3.1, colour = palette$muted, family = "Arial Unicode MS") +
    annotate("label", x = 0.15, y = 0.50, label = "element\nconnectivity", fill = palette$light_symbolic, colour = palette$symbolic, label.size = 0.35, size = 3.0, family = "Arial Unicode MS") +
    annotate("label", x = 0.39, y = 0.50, label = "symbolic", fill = palette$light_symbolic, colour = palette$symbolic, label.size = 0.35, size = 3.2, family = "Arial Unicode MS") +
    annotate("rect", xmin = 0.55, xmax = 0.72, ymin = 0.34, ymax = 0.64, fill = "white", colour = palette$symbolic, linewidth = 0.6) +
    annotate("point", x = c(0.58, 0.62, 0.66, 0.70), y = c(0.58, 0.53, 0.47, 0.40), colour = palette$symbolic, size = 2) +
    annotate("label", x = 0.86, y = 0.49, label = "values", fill = palette$light_numeric, colour = palette$numeric, label.size = 0.35, size = 3.1, family = "Arial Unicode MS") +
    annotate("segment", x = c(0.23, 0.48, 0.72, 0.72, 0.72), xend = c(0.32, 0.55, 0.80, 0.80, 0.80), y = c(0.50, 0.50, 0.58, 0.50, 0.42), yend = c(0.50, 0.50, 0.56, 0.49, 0.43), arrow = arrow(length = unit(0.12, "inches")), colour = c(palette$symbolic, palette$symbolic, palette$numeric, palette$numeric, palette$numeric), linewidth = 0.6) +
    annotate("text", x = 0.04, y = 0.14, label = "symbolic 可并行且可复用；numeric 只 scatter 到 values。", hjust = 0, size = 3.0, colour = palette$muted, family = "Arial Unicode MS") +
    coord_cartesian(xlim = c(0, 1), ylim = c(0, 1), expand = FALSE) +
    theme_void()
}

timing_data <- function(rows) {
  out <- data.frame()
  for (i in seq_len(nrow(rows))) {
    r <- rows[i, ]
    if (startsWith(r$mode, "direct")) {
      parts <- data.frame(
        key = r$key,
        label = r$label,
        threads = r$threads,
        total_ms = r$total_ms,
        stage = c("direct generate", "bucket/merge", "sort/reduce"),
        ms = c(r$direct_generate_ms, r$direct_bucket_merge_ms, r$direct_sort_reduce_ms),
        fill = c("generate", "bucket", "sort")
      )
    } else {
      csr_ms <- r$symbolic_ms * r$csr_gib / max(r$csr_gib + r$plan_gib, 1e-12)
      parts <- data.frame(
        key = r$key,
        label = r$label,
        threads = r$threads,
        total_ms = r$total_ms,
        stage = c("CSR pattern", "scatter plan", "numeric"),
        ms = c(csr_ms, r$symbolic_ms - csr_ms, r$numeric_ms),
        fill = c("symbolic", "scatter", "numeric")
      )
    }
    out <- rbind(out, parts)
  }
  out$key <- factor(out$key, levels = rev(c("serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic")))
  out
}

memory_data <- function(rows) {
  out <- data.frame(
    key = rep(rows$key, each = 3),
    label = rep(rows$label, each = 3),
    component = rep(c("CSR + scatter", "symbolic temp", "direct transient"), nrow(rows)),
    gib = as.vector(t(cbind(rows$persistent_symbolic_gib, rows$symbolic_temp_gib, rows$direct_transient_gib))),
    fill = rep(c("symbolic", "scatter", "sort"), nrow(rows))
  )
  out$label_text <- ""
  out$label_x <- NA_real_
  for (key in unique(out$key)) {
    idx <- which(out$key == key)
    running <- 0
    for (i in idx) {
      running <- running + out$gib[i]
      if (key == "parallel_symbolic" && out$component[i] == "symbolic temp") {
        out$label_text[i] <- sprintf("+%.2f temp", out$gib[i])
        out$label_x[i] <- running + 0.08
      }
    }
  }
  out$key <- factor(out$key, levels = rev(c("serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic")))
  out
}

main_plot <- function(rows, metrics) {
  td <- timing_data(rows)
  md <- memory_data(rows)
  fills <- c(
    generate = palette$light_direct,
    bucket = palette$direct,
    sort = palette$light_sort,
    symbolic = palette$light_symbolic,
    scatter = palette$light_scatter,
    numeric = palette$light_numeric
  )
  outlines <- c(
    generate = palette$generate,
    bucket = palette$bucket,
    sort = palette$sort,
    symbolic = palette$symbolic,
    scatter = palette$scatter,
    numeric = palette$numeric
  )
  timing <- ggplot(td, aes(x = ms / 1000, y = key, fill = fill, colour = fill)) +
    geom_col(width = 0.58, linewidth = 0.35) +
    geom_text(data = rows, aes(x = total_ms / 1000 + 0.13, y = factor(key, levels = rev(c("serial_direct", "serial_symbolic", "parallel_direct", "parallel_symbolic"))), label = fmt_time(total_ms)), inherit.aes = FALSE, hjust = 0, family = "Arial Unicode MS", fontface = "bold", size = 3.4, colour = palette$ink) +
    scale_fill_manual(values = fills, labels = c(generate = "direct generate", bucket = "bucket/merge", sort = "sort/reduce", symbolic = "CSR pattern", scatter = "scatter plan", numeric = "numeric")) +
    scale_colour_manual(values = outlines, guide = "none") +
    scale_y_discrete(labels = setNames(paste0(rows$label, "\n", rows$threads, " thread(s)"), rows$key)) +
    labs(title = "四类路线端到端耗时构成", x = NULL, y = NULL) +
    coord_cartesian(xlim = c(0, max(rows$total_ms) / 1000 * 1.22), clip = "off") +
    theme_pgsa(9)

  memory <- ggplot(md[md$gib > 0, ], aes(x = gib, y = key, fill = fill, colour = fill)) +
    geom_col(width = 0.55, linewidth = 0.35) +
    geom_text(data = md[md$label_text != "", ], aes(x = label_x, y = key, label = label_text), inherit.aes = FALSE, hjust = 0, family = "Arial Unicode MS", size = 2.7, colour = palette$scatter) +
    scale_fill_manual(values = fills[c("symbolic", "scatter", "sort")], labels = c(symbolic = "CSR + scatter", scatter = "symbolic temp", sort = "direct transient")) +
    scale_colour_manual(values = outlines, guide = "none") +
    scale_y_discrete(labels = setNames(rows$label, rows$key)) +
    labs(title = "内存占用（辅证）", x = "GiB", y = NULL) +
    theme_pgsa(8)

  badges <- ggplot() +
    annotate("text", x = 0.02, y = 0.94, label = "对比结论", hjust = 0, size = 5, fontface = "bold", colour = palette$ink, family = "Arial Unicode MS") +
    annotate("label", x = 0.50, y = c(0.76, 0.56, 0.36, 0.16), label = c(
      sprintf("1.68x  串行：有符号优于无符号\n5.20 s → 3.09 s"),
      sprintf("4.67x  并行符号优于串行符号\n3.09 s → 662 ms"),
      sprintf("2.52x  同为 14 线程：有符号优于 direct\n1.67 s → 662 ms"),
      sprintf("7.85x  最佳路线相对串行 direct\n5.20 s → 662 ms")
    ), fill = "#F6FAF7", colour = palette$gain, label.size = 0.35, size = 3.2, family = "Arial Unicode MS") +
    coord_cartesian(xlim = c(0, 1), ylim = c(0, 1), expand = FALSE) +
    theme_void()

  header <- ggplot() +
    annotate("text", x = 0.02, y = 0.72, label = "四类刚度组装路线：时间优先，内存为辅", hjust = 0, size = 7.2, fontface = "bold", colour = palette$ink, family = "Arial Unicode MS") +
    annotate("text", x = 0.02, y = 0.28, label = "WindHub Tet4 / Apple M4 Max；total time includes symbolic/direct construction and numeric assembly", hjust = 0, size = 3.3, colour = palette$muted, family = "Arial Unicode MS") +
    theme_void()

  header / (direct_schematic() | two_stage_schematic()) / (timing | badges) / memory +
    plot_layout(heights = c(0.38, 1.35, 2.15, 1.12), widths = c(2.4, 1)) &
    plot_annotation(caption = "Source: curated WindHub / Apple M4 Max quadrant rows; direct/no-symbolic is contribution-list sort/reduce, not a dense matrix.")
}

save_plot <- function(plot, out_base, formats, width = 16, height = 9) {
  dir.create(dirname(out_base), recursive = TRUE, showWarnings = FALSE)
  for (fmt in formats) {
    target <- paste0(out_base, ".", fmt)
    if (fmt == "svg") {
      svglite::svglite(target, width = width, height = height)
      print(plot)
      dev.off()
    } else if (fmt == "pdf") {
      grDevices::cairo_pdf(target, width = width, height = height, family = "Arial Unicode MS")
      print(plot)
      dev.off()
    } else if (fmt == "png") {
      ragg::agg_png(target, width = width, height = height, units = "in", res = 300)
      print(plot)
      dev.off()
    } else {
      stop(sprintf("Unsupported format: %s", fmt))
    }
  }
}

write_source_copy <- function(source_csv, out_root) {
  source_dir <- file.path(out_root, "source_data")
  dir.create(source_dir, recursive = TRUE, showWarnings = FALSE)
  file.copy(source_csv, file.path(source_dir, "quadrant_selected_rows.csv"), overwrite = TRUE)
}

main <- function() {
  args <- parse_args()
  rows <- load_rows(args$source_csv)
  metrics <- metrics_from_rows(rows)
  out_dir <- file.path(args$out_root, "r")
  write_source_copy(args$source_csv, args$out_root)
  save_plot(main_plot(rows, metrics), file.path(out_dir, "assembly_quadrants_revised.r"), args$formats)
  save_plot(direct_schematic(), file.path(out_dir, "direct_assembly_schematic.r"), args$formats, width = 8, height = 3.6)
  save_plot(two_stage_schematic(), file.path(out_dir, "two_stage_assembly_schematic.r"), args$formats, width = 8, height = 3.6)
  cat(sprintf("R candidate written to %s\n", out_dir))
}

main()
