#!/usr/bin/env python3
"""
Compression Performance Analysis and Visualization Script

This script analyzes compression test results and generates meaningful visualizations
to compare different compression methods (gzip, brotli, zstd) across various metrics.
"""

import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path
import seaborn as sns
from typing import List, Dict, Any

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def load_results(file_path: str) -> List[Dict[str, Any]]:
    """Load compression results from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def prepare_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert results to a pandas DataFrame for easier analysis."""
    rows = []
    
    for file_data in results:
        file_name = Path(file_data['file']).name
        original_size = file_data['original_size']
        
        for result in file_data['results']:
            row = {
                'file': file_name,
                'original_size_kb': original_size / 1024,
                'method': result['method'],
                'level': result['level'],
                'compressed_size': result['compressed_size'],
                'compressed_size_kb': result['compressed_size'] / 1024,
                'ratio': result['ratio'],
                'time_ms': result['time_s'] * 1000,  # Convert to milliseconds
                'compression_percentage': (1 - result['ratio']) * 100,
                'available': result['available']
            }
            rows.append(row)
    
    return pd.DataFrame(rows)

def plot_compression_ratio_by_level(df: pd.DataFrame, save_path: str = None):
    """Plot compression ratio vs compression level for each method."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Compression Ratio vs Compression Level', fontsize=16, fontweight='bold')
    
    files = df['file'].unique()
    methods = ['gzip', 'br', 'zstd']
    
    # Find global y-axis range for consistency
    global_min_ratio = df['ratio'].min() * 0.95
    global_max_ratio = df['ratio'].max() * 1.05
    
    for i, method in enumerate(methods):
        ax = axes[i]
        method_data = df[df['method'] == method]
        
        for file in files:
            file_data = method_data[method_data['file'] == file]
            if not file_data.empty:
                ax.plot(file_data['level'], file_data['ratio'], 
                       marker='o', linewidth=2, markersize=6, label=file)
        
        ax.set_xlabel('Compression Level', fontweight='bold')
        ax.set_ylabel('Compression Ratio', fontweight='bold')
        ax.set_title(f'{method.upper()}', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Set consistent y-axis range and formatting
        ax.set_ylim(global_min_ratio, global_max_ratio)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.2f}'))
    
    plt.tight_layout()
    if save_path:
        plt.savefig(f"{save_path}_ratio_by_level.png", dpi=300, bbox_inches='tight')
    plt.show()

def plot_compression_time_by_level(df: pd.DataFrame, save_path: str = None):
    """Plot compression time vs compression level for each method."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Compression Time vs Compression Level', fontsize=16, fontweight='bold')
    
    files = df['file'].unique()
    methods = ['gzip', 'br', 'zstd']
    
    # Find global y-axis range for consistency (with some padding)
    global_min_time = df['time_ms'].min() * 0.5
    global_max_time = df['time_ms'].max() * 2
    
    for i, method in enumerate(methods):
        ax = axes[i]
        method_data = df[df['method'] == method]
        
        for file in files:
            file_data = method_data[method_data['file'] == file]
            if not file_data.empty:
                ax.plot(file_data['level'], file_data['time_ms'], 
                       marker='s', linewidth=2, markersize=6, label=file)
        
        ax.set_xlabel('Compression Level', fontweight='bold')
        ax.set_ylabel('Compression Time (ms)', fontweight='bold')
        ax.set_title(f'{method.upper()}', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Set consistent y-axis range with log scale and better formatting
        ax.set_yscale('log')
        ax.set_ylim(global_min_time, global_max_time)
        
        # Format y-axis to show readable time values
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.3f}' if y >= 0.001 else f'{y:.1e}'))
    
    plt.tight_layout()
    if save_path:
        plt.savefig(f"{save_path}_time_by_level.png", dpi=300, bbox_inches='tight')
    plt.show()

def plot_ratio_vs_time_tradeoff(df: pd.DataFrame, save_path: str = None):
    """Plot compression ratio vs time trade-off for different methods."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Compression Ratio vs Time Trade-off', fontsize=16, fontweight='bold')
    
    files = df['file'].unique()
    
    # Find global axis ranges for consistency
    global_min_ratio = df['ratio'].min() * 0.95
    global_max_ratio = df['ratio'].max() * 1.05
    global_min_time = df['time_ms'].min() * 0.5
    global_max_time = df['time_ms'].max() * 2
    
    for i, file in enumerate(files):
        ax = axes[i]
        file_data = df[df['file'] == file]
        
        methods = ['gzip', 'br', 'zstd']
        method_colors = {'gzip': 'red', 'br': 'blue', 'zstd': 'green'}
        
        for method in methods:
            method_data = file_data[file_data['method'] == method]
            if not method_data.empty:
                scatter = ax.scatter(method_data['time_ms'], method_data['ratio'], 
                                   c=method_colors[method], label=method, 
                                   alpha=0.7, s=60, edgecolors='black', linewidth=0.5)
                
                # Add level annotations for some points
                for _, row in method_data.iterrows():
                    if row['level'] in [1, 5, 9, 11]:  # Annotate key levels
                        ax.annotate(f"{method}-{row['level']}", 
                                  (row['time_ms'], row['ratio']),
                                  xytext=(5, 5), textcoords='offset points',
                                  fontsize=8, alpha=0.7)
        
        ax.set_xlabel('Compression Time (ms)', fontweight='bold')
        ax.set_ylabel('Compression Ratio', fontweight='bold')
        ax.set_title(f'{file}', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Set consistent axis ranges
        ax.set_xscale('log')
        ax.set_xlim(global_min_time, global_max_time)
        ax.set_ylim(global_min_ratio, global_max_ratio)
        
        # Format x-axis to show readable time values
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.3f}' if x >= 0.001 else f'{x:.1e}'))
    
    plt.tight_layout()
    if save_path:
        plt.savefig(f"{save_path}_ratio_vs_time.png", dpi=300, bbox_inches='tight')
    plt.show()

def plot_best_methods_comparison(df: pd.DataFrame, save_path: str = None):
    """Compare the best compression methods for each file."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Best Compression Methods Comparison', fontsize=16, fontweight='bold')
    
    # Find best compression ratio for each file and method (handle duplicates)
    best_ratio_idx = df.groupby(['file', 'method'])['ratio'].idxmin()
    best_ratio_data = df.loc[best_ratio_idx].reset_index(drop=True)
    
    # Find fastest compression for each file and method (handle duplicates)
    best_time_idx = df.groupby(['file', 'method'])['time_ms'].idxmin()
    best_time_data = df.loc[best_time_idx].reset_index(drop=True)
    
    # Plot 1: Best compression ratios
    pivot_ratio = best_ratio_data.pivot(index='file', columns='method', values='ratio')
    pivot_ratio.plot(kind='bar', ax=ax1, width=0.8)
    ax1.set_title('Best Compression Ratio by Method', fontweight='bold')
    ax1.set_ylabel('Compression Ratio', fontweight='bold')
    ax1.set_xlabel('File', fontweight='bold')
    ax1.legend(title='Method')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot 2: Best compression times
    pivot_time = best_time_data.pivot(index='file', columns='method', values='time_ms')
    pivot_time.plot(kind='bar', ax=ax2, width=0.8)
    ax2.set_title('Fastest Compression Time by Method', fontweight='bold')
    ax2.set_ylabel('Compression Time (ms)', fontweight='bold')
    ax2.set_xlabel('File', fontweight='bold')
    ax2.legend(title='Method')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    # Use linear scale and format time values nicely
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.3f}' if y >= 0.001 else f'{y:.1e}'))
    
    # Plot 3: Compression percentage savings
    pivot_savings = best_ratio_data.pivot(index='file', columns='method', values='compression_percentage')
    pivot_savings.plot(kind='bar', ax=ax3, width=0.8)
    ax3.set_title('Space Savings by Method (%)', fontweight='bold')
    ax3.set_ylabel('Space Savings (%)', fontweight='bold')
    ax3.set_xlabel('File', fontweight='bold')
    ax3.legend(title='Method')
    ax3.grid(True, alpha=0.3)
    ax3.tick_params(axis='x', rotation=45)
    
    # Plot 4: File size comparison
    file_sizes = df.groupby('file')['original_size_kb'].first()
    file_sizes.plot(kind='bar', ax=ax4, color='skyblue', width=0.8)
    ax4.set_title('Original File Sizes', fontweight='bold')
    ax4.set_ylabel('File Size (KB)', fontweight='bold')
    ax4.set_xlabel('File', fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    if save_path:
        plt.savefig(f"{save_path}_best_methods.png", dpi=300, bbox_inches='tight')
    plt.show()

def plot_efficiency_matrix(df: pd.DataFrame, save_path: str = None):
    """Create a heatmap showing compression efficiency across methods and levels."""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle('Compression Efficiency Matrix (Lower is Better)', fontsize=16, fontweight='bold')
    
    files = df['file'].unique()
    
    for i, file in enumerate(files):
        ax = axes[i]
        file_data = df[df['file'] == file]
        
        # Create efficiency metric: ratio * time (lower is better)
        file_data = file_data.copy()
        file_data['efficiency'] = file_data['ratio'] * file_data['time_ms']
        
        # Pivot for heatmap
        heatmap_data = file_data.pivot(index='method', columns='level', values='efficiency')
        
        # Create heatmap
        sns.heatmap(heatmap_data, annot=True, fmt='.3f', cmap='RdYlBu_r', 
                   ax=ax, cbar_kws={'label': 'Efficiency (ratio × time)'})
        ax.set_title(f'{file}', fontweight='bold')
        ax.set_xlabel('Compression Level', fontweight='bold')
        ax.set_ylabel('Method', fontweight='bold')
    
    plt.tight_layout()
    if save_path:
        plt.savefig(f"{save_path}_efficiency_matrix.png", dpi=300, bbox_inches='tight')
    plt.show()

def generate_summary_statistics(df: pd.DataFrame):
    """Generate and print summary statistics."""
    print("=" * 60)
    print("COMPRESSION PERFORMANCE SUMMARY")
    print("=" * 60)
    
    for file in df['file'].unique():
        file_data = df[df['file'] == file]
        original_size = file_data['original_size_kb'].iloc[0]
        
        print(f"\nFile: {file} (Original size: {original_size:.2f} KB)")
        print("-" * 50)
        
        for method in ['gzip', 'br', 'zstd']:
            method_data = file_data[file_data['method'] == method]
            if not method_data.empty:
                best_ratio = method_data.loc[method_data['ratio'].idxmin()]
                fastest = method_data.loc[method_data['time_ms'].idxmin()]
                
                print(f"{method.upper()}:")
                print(f"  Best compression: {best_ratio['compression_percentage']:.1f}% "
                      f"(level {best_ratio['level']}, {best_ratio['time_ms']:.3f}ms)")
                print(f"  Fastest: {fastest['time_ms']:.3f}ms "
                      f"(level {fastest['level']}, {fastest['compression_percentage']:.1f}%)")
    
    print("\n" + "=" * 60)

def main():
    """Main function to run all analyses."""
    # Load data
    results_file = Path(__file__).parent / "results.json"
    results = load_results(results_file)
    df = prepare_dataframe(results)
    
    # Create output directory for plots
    output_dir = Path(__file__).parent / "plots"
    output_dir.mkdir(exist_ok=True)
    save_path = output_dir / "compression_analysis"
    
    print("Generating compression performance analysis plots...")
    
    # Generate all plots
    plot_compression_ratio_by_level(df, str(save_path))
    plot_compression_time_by_level(df, str(save_path))
    plot_ratio_vs_time_tradeoff(df, str(save_path))
    plot_best_methods_comparison(df, str(save_path))
    plot_efficiency_matrix(df, str(save_path))
    
    # Generate summary statistics
    generate_summary_statistics(df)
    
    print(f"\nAll plots saved to: {output_dir}")
    print("Analysis complete!")

if __name__ == "__main__":
    main()