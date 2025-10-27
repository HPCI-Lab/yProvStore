# Compression Performance Analysis

This directory contains scripts and results for analyzing compression performance across different methods and levels.

## Files

- `results.json` - Raw compression test results
- `analyze_compression_results.py` - Text-based analysis script (no dependencies)
- `plot_compression_results.py` - Full plotting script (requires matplotlib, pandas, seaborn)
- `compression_analysis.csv` - Exported data for external analysis
- `plot_requirements.txt` - Python packages needed for plotting

## Quick Analysis

Run the analysis script (no external dependencies required):

```bash
python analyze_compression_results.py
```

This will:
- Generate a detailed text-based performance report
- Export data to CSV for external analysis
- Provide recommendations for different use cases

## Visual Analysis

To generate graphs and charts, first install the required packages:

```bash
pip install -r plot_requirements.txt
```

Then run the plotting script:

```bash
python plot_compression_results.py
```

This will generate:
- Compression ratio vs level plots
- Compression time vs level plots
- Ratio vs time trade-off analysis
- Method comparison charts
- Efficiency heatmaps

## Key Findings

### Best Overall Performance
- **Maximum Compression**: Brotli Level 11 (75-95% space saved)
- **Fastest with Good Compression**: ZSTD Level 3-8 (0.01-0.7ms)
- **Most Balanced**: ZSTD Level 6 (good compression + reasonable speed)

### Recommendations by Use Case

1. **Real-time Applications**: ZSTD Level 3-6 or GZIP Level 1-3
2. **Storage Optimization**: Brotli Level 6-8
3. **Web Delivery**: ZSTD Level 6 or Brotli Level 4-6

### Method Comparison

- **BROTLI (br)**: Best compression ratios but slow at high levels
- **ZSTD**: Great balance of compression and speed, very consistent
- **GZIP**: Good compression, widely compatible, moderate speed

## External Analysis

The `compression_analysis.csv` file contains all test data and can be imported into:
- Excel for basic charts
- R for statistical analysis
- Tableau/Power BI for interactive dashboards
- Any plotting tool that accepts CSV input

### CSV Columns
- `file`: Test file name
- `original_size_bytes/kb`: Original file size
- `method`: Compression method (gzip, br, zstd)
- `level`: Compression level
- `compressed_size/kb`: Resulting compressed size
- `ratio`: Compression ratio (compressed/original)
- `time_ms`: Compression time in milliseconds
- `space_saved_percent`: Percentage of space saved
- `available`: Whether the method/level is available