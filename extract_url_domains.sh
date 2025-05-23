#!/bin/bash

# Extract URL domains from news articles
# This script runs the url_analyzer.py script to analyze URL prefixes

# Output file (optional)
OUTPUT_FILE="url_domains_report.txt"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found."
    exit 1
fi

# Print help if requested
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: $0 [news|json_file] [output_file]"
    echo ""
    echo "Options:"
    echo "  news        Analyze news article files in aapl_news_articles directory"
    echo "  json_file   Path to a JSON file containing URL data"
    echo "  output_file Path to save the report (optional)"
    echo ""
    echo "Examples:"
    echo "  $0 news url_report.txt      # Analyze news files and save report to url_report.txt"
    echo "  $0 data.json                # Analyze URL data from data.json and print to console"
    exit 0
fi

# Run the Python script with appropriate arguments
if [ -z "$1" ]; then
    # No arguments, analyze URLs from all JSON files
    echo "Analyzing URLs from crawled data..."
    python3 url_analyzer.py
elif [ "$1" == "news" ]; then
    # Analyze news article files
    echo "Analyzing URLs from news articles..."
    if [ -z "$2" ]; then
        python3 url_analyzer.py news
    else
        python3 url_analyzer.py news "$2"
        echo "Report saved to $2"
    fi
else
    # Use the provided JSON file
    if [ ! -f "$1" ]; then
        echo "Error: File '$1' not found!"
        exit 1
    fi
    
    echo "Analyzing URLs from $1..."
    if [ -z "$2" ]; then
        python3 url_analyzer.py "$1"
    else
        python3 url_analyzer.py "$1" "$2"
        echo "Report saved to $2"
    fi
fi 