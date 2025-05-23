import re
import os
import json
from urllib.parse import urlparse
from collections import defaultdict

def extract_url_prefix(url):
    """
    Extract the domain prefix from a URL.
    
    Args:
        url (str): The URL to analyze
        
    Returns:
        str: The domain prefix (e.g., finance.yahoo.com)
    """
    try:
        # Parse URL and extract netloc (domain)
        parsed = urlparse(url)
        return parsed.netloc
    except Exception as e:
        print(f"Error parsing URL {url}: {e}")
        return None

def analyze_url_data(data_file):
    """
    Analyze URL data from a JSON file containing original and final URLs.
    
    Args:
        data_file (str): Path to the JSON file containing URL data
        
    Returns:
        dict: Dictionary with domain prefixes as keys and counts as values
    """
    # Check if file exists
    if not os.path.exists(data_file):
        print(f"File not found: {data_file}")
        return None
    
    try:
        # Load JSON data
        with open(data_file, 'r', encoding='utf-8') as f:
            url_data = json.load(f)
        
        # Initialize counters
        original_domains = defaultdict(int)
        final_domains = defaultdict(int)
        
        # Process each URL entry
        for entry in url_data:
            if 'original_url' in entry and entry['original_url']:
                original_prefix = extract_url_prefix(entry['original_url'])
                if original_prefix:
                    original_domains[original_prefix] += 1
            
            if 'final_url' in entry and entry['final_url']:
                final_prefix = extract_url_prefix(entry['final_url'])
                if final_prefix:
                    final_domains[final_prefix] += 1
        
        return {
            'original_domains': dict(original_domains),
            'final_domains': dict(final_domains)
        }
    except Exception as e:
        print(f"Error analyzing URL data: {e}")
        return None

def generate_url_prefix_report(data_file, output_file=None):
    """
    Generate a report of URL prefixes from a data file.
    
    Args:
        data_file (str): Path to the JSON file containing URL data
        output_file (str, optional): Path to save the report. If None, prints to console.
    """
    domains_data = analyze_url_data(data_file)
    
    if not domains_data:
        return
    
    # Create report content
    report = []
    report.append("=== Original URL Domains ===")
    for domain, count in sorted(domains_data['original_domains'].items(), key=lambda x: x[1], reverse=True):
        report.append(f"@https://{domain} ({count})")
    
    report.append("\n=== Final URL Domains (After Redirects) ===")
    for domain, count in sorted(domains_data['final_domains'].items(), key=lambda x: x[1], reverse=True):
        report.append(f"@https://{domain} ({count})")
    
    # Output report
    report_content = '\n'.join(report)
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"Report saved to {output_file}")
    else:
        print(report_content)

def analyze_news_article_files(news_dir="aapl_news_articles"):
    """
    Analyze URL prefixes from news article text files.
    
    Args:
        news_dir (str): Directory containing news article files
        
    Returns:
        dict: Dictionary with URL prefix analysis
    """
    original_domains = defaultdict(int)
    final_domains = defaultdict(int)
    redirects = []
    processed_files = 0
    error_files = []
    
    # Compile regex patterns for extracting URLs - updated to match both formats
    original_url_pattern = re.compile(r'^原始URL:\s*(https?://[^\r\n]+)', re.MULTILINE)
    # Match both "最終URL:" and "重定向URL:" formats
    final_url_pattern = re.compile(r'^(?:最終URL|重定向URL):\s*(https?://[^\r\n]+)', re.MULTILINE)
    
    print(f"Starting analysis of news articles in {news_dir}")
    
    # Walk through all subdirectories and files
    for root, dirs, files in os.walk(news_dir):
        for file in files:
            if file.endswith('.txt'):
                file_path = os.path.join(root, file)
                try:
                    print(f"Processing file: {file_path}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract URLs with improved patterns
                    original_url_match = original_url_pattern.search(content)
                    final_url_match = final_url_pattern.search(content)
                    
                    if original_url_match or final_url_match:
                        processed_files += 1
                    
                    # Process original URL
                    if original_url_match:
                        original_url = original_url_match.group(1).strip()
                        original_domain = extract_url_prefix(original_url)
                        if original_domain:
                            original_domains[original_domain] += 1
                            print(f"Found original domain: {original_domain}")
                    else:
                        print(f"No original URL found in {file}")
                    
                    # Process final URL
                    if final_url_match:
                        final_url = final_url_match.group(1).strip()
                        final_domain = extract_url_prefix(final_url)
                        if final_domain:
                            final_domains[final_domain] += 1
                            print(f"Found final domain: {final_domain}")
                    else:
                        print(f"No final URL found in {file}")
                    
                    # Track redirects
                    if original_url_match and final_url_match:
                        original_url = original_url_match.group(1).strip()
                        final_url = final_url_match.group(1).strip()
                        if original_url != final_url:
                            original_domain = extract_url_prefix(original_url)
                            final_domain = extract_url_prefix(final_url)
                            if original_domain and final_domain and original_domain != final_domain:
                                redirects.append((original_domain, final_domain))
                                print(f"Found redirect: {original_domain} -> {final_domain}")
                
                except Exception as e:
                    error_files.append((file_path, str(e)))
                    print(f"Error processing {file_path}: {e}")
    
    print(f"\nAnalysis complete:")
    print(f"Processed files: {processed_files}")
    print(f"Files with errors: {len(error_files)}")
    if error_files:
        print("\nError details:")
        for file_path, error in error_files:
            print(f"- {file_path}: {error}")
    
    return {
        'original_domains': dict(original_domains),
        'final_domains': dict(final_domains),
        'redirects': redirects,
        'processed_files': processed_files,
        'error_files': error_files
    }

def generate_news_url_report(output_file=None):
    """
    Generate a report of URL prefixes from news article files.
    
    Args:
        output_file (str, optional): Path to save the report. If None, prints to console.
    """
    print("Analyzing news article files for URL prefixes...")
    url_data = analyze_news_article_files()
    
    if not url_data['original_domains'] and not url_data['final_domains']:
        print("Warning: No URLs were found in any of the processed files!")
        if url_data['error_files']:
            print("\nErrors occurred while processing files:")
            for file_path, error in url_data['error_files']:
                print(f"- {file_path}: {error}")
        return
    
    # Create report content
    report = []
    
    # Summary section
    report.append("=== Analysis Summary ===")
    report.append(f"Total files processed: {url_data['processed_files']}")
    report.append(f"Files with errors: {len(url_data['error_files'])}")
    report.append("")
    
    # Original domains report
    report.append("=== Original URL Domains ===")
    for domain, count in sorted(url_data['original_domains'].items(), key=lambda x: (-x[1], x[0])):
        report.append(f"@https://{domain} ({count})")
    
    # Final domains report
    report.append("\n=== Final URL Domains (After Redirects) ===")
    for domain, count in sorted(url_data['final_domains'].items(), key=lambda x: (-x[1], x[0])):
        report.append(f"@https://{domain} ({count})")
    
    # Redirects report (unique domain pairs)
    if url_data['redirects']:
        unique_redirects = set(url_data['redirects'])
        report.append("\n=== Domain Redirects ===")
        for orig_domain, final_domain in sorted(unique_redirects):
            report.append(f"{orig_domain} -> {final_domain}")
    
    # Error report
    if url_data['error_files']:
        report.append("\n=== Processing Errors ===")
        for file_path, error in url_data['error_files']:
            report.append(f"- {file_path}: {error}")
    
    # Output report
    report_content = '\n'.join(report)
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"Report saved to {output_file}")
    else:
        print(report_content)

def analyze_urls_from_crawl():
    """
    Extract URL prefixes from crawl data and organize them by domain.
    This function analyzes stored URLs from previous crawls.
    """
    # Dictionary to store URLs by domain
    domains = defaultdict(list)
    redirects = {}
    
    # Look for relevant data files
    data_dir = "."  # Current directory or specify another path
    
    print("Searching for crawl output files...")
    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            try:
                file_path = os.path.join(data_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        # Check if this file contains URL data
                        if isinstance(data, list) and data and 'url' in data[0]:
                            print(f"Found URL data in {filename}")
                            for item in data:
                                original_url = item.get('url')
                                final_url = item.get('final_url', original_url)
                                
                                if original_url:
                                    original_domain = extract_url_prefix(original_url)
                                    if original_domain:
                                        domains[original_domain].append(original_url)
                                
                                if final_url and final_url != original_url:
                                    final_domain = extract_url_prefix(final_url)
                                    if final_domain:
                                        redirects[original_url] = final_url
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    # Generate report
    report = ["=== URL Domain Analysis ==="]
    report.append(f"Found {len(domains)} unique domains")
    
    # Report domains sorted by frequency
    sorted_domains = sorted(domains.items(), key=lambda x: len(x[1]), reverse=True)
    
    for domain, urls in sorted_domains:
        report.append(f"\n@https://{domain} ({len(urls)})")
    
    # Report redirects
    if redirects:
        report.append("\n=== URL Redirections ===")
        for orig, final in redirects.items():
            orig_domain = extract_url_prefix(orig)
            final_domain = extract_url_prefix(final)
            if orig_domain != final_domain:
                report.append(f"{orig_domain} -> {final_domain}")
    
    print('\n'.join(report))

if __name__ == "__main__":
    # Check for command line arguments
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "news":
        # Analyze news article files
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        generate_news_url_report(output_path)
    elif len(sys.argv) > 1:
        # If a file is provided as argument
        file_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        generate_url_prefix_report(file_path, output_path)
    else:
        # Otherwise analyze crawled URLs
        analyze_urls_from_crawl() 