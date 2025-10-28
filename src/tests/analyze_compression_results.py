#!/usr/bin/env python3
"""
Compression Performance Analysis Script (Minimal Dependencies)

This script analyzes compression test results and generates meaningful visualizations.
If matplotlib is not available, it will output text-based analysis.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any

def load_results(file_path: str) -> List[Dict[str, Any]]:
    """Load compression results from JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def analyze_results(results: List[Dict[str, Any]]):
    """Analyze compression results and generate text-based report."""
    print("=" * 80)
    print("COMPRESSION PERFORMANCE ANALYSIS REPORT")
    print("=" * 80)
    
    for file_data in results:
        file_name = Path(file_data['file']).name
        original_size = file_data['original_size']
        
        print(f"\nFile: {file_name}")
        print(f"Original size: {original_size:,} bytes ({original_size/1024:.2f} KB)")
        print("-" * 60)
        
        # Group by method
        methods = {}
        for result in file_data['results']:
            method = result['method']
            if method not in methods:
                methods[method] = []
            methods[method].append(result)
        
        # Analyze each method
        for method, method_results in methods.items():
            print(f"\n{method.upper()} Compression:")
            
            # Find best compression and fastest time
            best_compression = min(method_results, key=lambda x: x['ratio'])
            fastest_time = min(method_results, key=lambda x: x['time_s'])
            
            print(f"  Levels tested: {min(r['level'] for r in method_results)} - {max(r['level'] for r in method_results)}")
            print(f"  Best compression: Level {best_compression['level']} - {(1-best_compression['ratio'])*100:.1f}% space saved")
            print(f"    Compressed size: {best_compression['compressed_size']:,} bytes")
            print(f"    Time: {best_compression['time_s']*1000:.3f} ms")
            print(f"  Fastest: Level {fastest_time['level']} - {fastest_time['time_s']*1000:.3f} ms")
            print(f"    Space saved: {(1-fastest_time['ratio'])*100:.1f}%")
            
            # Show progression
            print(f"  Level progression:")
            for result in sorted(method_results, key=lambda x: x['level']):
                space_saved = (1 - result['ratio']) * 100
                time_ms = result['time_s'] * 1000
                print(f"    L{result['level']:2d}: {space_saved:5.1f}% saved, {time_ms:8.3f} ms")
    
    print("\n" + "=" * 80)
    print("METHOD COMPARISON SUMMARY")
    print("=" * 80)
    
    # Compare best results across methods
    for file_data in results:
        file_name = Path(file_data['file']).name
        print(f"\n{file_name}:")
        
        methods_best = {}
        for result in file_data['results']:
            method = result['method']
            if method not in methods_best or result['ratio'] < methods_best[method]['ratio']:
                methods_best[method] = result
        
        # Sort by compression ratio
        sorted_methods = sorted(methods_best.items(), key=lambda x: x[1]['ratio'])
        
        print("  Best compression ratio by method:")
        for i, (method, result) in enumerate(sorted_methods, 1):
            space_saved = (1 - result['ratio']) * 100
            time_ms = result['time_s'] * 1000
            print(f"    {i}. {method.upper()}: {space_saved:.1f}% saved (Level {result['level']}, {time_ms:.3f} ms)")

def export_to_csv(results: List[Dict[str, Any]], output_path: str):
    """Export results to CSV for external analysis."""
    csv_path = Path(output_path) / "compression_results.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['file', 'original_size_bytes', 'original_size_kb', 'method', 'level', 
                     'compressed_size', 'compressed_size_kb', 'ratio', 'time_ms', 
                     'space_saved_percent', 'available']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for file_data in results:
            file_name = Path(file_data['file']).name
            original_size = file_data['original_size']
            
            for result in file_data['results']:
                row = {
                    'file': file_name,
                    'original_size_bytes': original_size,
                    'original_size_kb': original_size / 1024,
                    'method': result['method'],
                    'level': result['level'],
                    'compressed_size': result['compressed_size'],
                    'compressed_size_kb': result['compressed_size'] / 1024,
                    'ratio': result['ratio'],
                    'time_ms': result['time_s'] * 1000,
                    'space_saved_percent': (1 - result['ratio']) * 100,
                    'available': result['available']
                }
                writer.writerow(row)
    
    print(f"Results exported to: {csv_path}")

def create_plotting_script():
    """Create instructions for plotting with external tools."""
    instructions = """
PLOTTING INSTRUCTIONS
====================

To create visualizations, you can:

1. Install matplotlib and pandas:
   pip install matplotlib pandas seaborn numpy

2. Then run the full plotting script:
   python plot_compression_results.py

3. Or use external tools like Excel, R, or online plotting tools with the CSV export.

Key metrics to plot:
- Compression ratio vs level for each method
- Compression time vs level for each method  
- Compression ratio vs time trade-offs
- Method comparison charts

The CSV file contains all data needed for external analysis.
"""
    print(instructions)

def main():
    """Main function to run the analysis."""
    # Load data
    results_file = Path(__file__).parent / "results.json"
    
    if not results_file.exists():
        print(f"Error: {results_file} not found!")
        return
    
    results = load_results(results_file)
    
    # Create output directory
    output_dir = Path(__file__).parent / "analysis_output"
    output_dir.mkdir(exist_ok=True)
    
    # Run analysis
    analyze_results(results)
    
    # Export to CSV
    export_to_csv(results, output_dir)
    
    # Check if we can do plotting
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        import seaborn as sns
        print(f"\n{'='*60}")
        print("PLOTTING LIBRARIES AVAILABLE - Running full analysis...")
        print(f"{'='*60}")
        
        # Import and run the full plotting script functions
        exec(open(Path(__file__).parent / "plot_compression_results.py").read())
        
    except ImportError as e:
        print(f"\n{'='*60}")
        print(f"Plotting libraries not available: {e}")
        print("Running text-based analysis only.")
        print(f"{'='*60}")
        create_plotting_script()

if __name__ == "__main__":
    main()