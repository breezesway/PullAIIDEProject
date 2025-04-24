import pandas as pd
import os
import glob
import csv
import requests
from tqdm import tqdm
import time

def get_github_stats(repo_url, github_token=None):
    """
    Get repository statistics from GitHub API
    """
    # Convert GitHub URL to API URL
    if 'github.com' not in repo_url:
        return None
    
    # Extract owner and repo name from URL
    parts = repo_url.strip('/').split('/')
    if len(parts) < 5:
        return None
    
    owner = parts[-2]
    repo = parts[-1]
    
    # Prepare headers with token if provided
    headers = {}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    try:
        # Get basic repo info
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(repo_url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching {repo_url}: {response.status_code}")
            if response.status_code == 403:
                print("Rate limit exceeded. Please provide a GitHub token to increase the limit.")
            if response.status_code == 409:
                print(f"Repository {repo_url} is empty or in conflict (Status 409)")
            return None, response.status_code
        
        repo_data = response.json()
        stars = repo_data.get('stargazers_count', 0)
        
        # Get commit count
        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
        response = requests.get(commits_url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching commits for {repo_url}: {response.status_code}")
            return None, response.status_code
        
        # Get total commit count from the Link header
        commit_count = 0
        if 'Link' in response.headers:
            links = response.headers['Link'].split(',')
            for link in links:
                if 'rel="last"' in link:
                    # Extract the page number from the URL
                    try:
                        last_page_url = link.split(';')[0].strip('<>')
                        last_page = int(last_page_url.split('page=')[2].split('&')[0])
                        commit_count = last_page
                    except (IndexError, ValueError):
                        print(f"Warning: Could not parse commit count from {link}")
                        commit_count = 0
        
        # # Get repository contents recursively
        # contents_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
        # response = requests.get(contents_url, headers=headers)
        # if response.status_code != 200:
        #     # Try master branch if main doesn't exist
        #     contents_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
        #     response = requests.get(contents_url, headers=headers)
        #     if response.status_code != 200:
        #         print(f"Error fetching contents for {repo_url}: {response.status_code}")
        #         return None
        
        # contents_data = response.json()
        # file_count = 0
        # total_lines = 0
        
        # # Count files and get their sizes
        # for item in contents_data.get('tree', []):
        #     if item['type'] == 'blob':  # It's a file
        #         file_count += 1
        #         # Get file content to count lines
        #         file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{item['path']}"
        #         file_response = requests.get(file_url, headers=headers)
        #         if file_response.status_code == 200:
        #             file_data = file_response.json()
        #             if 'content' in file_data:
        #                 content = file_data['content']
        #                 # Count lines in the content
        #                 total_lines += len(content.split('\n'))
        
        return {
            'stars': stars,
            'commit_count': commit_count,
            # 'file_count': file_count,
            # 'total_lines': total_lines
        }, response.status_code
    except Exception as e:
        print(f"Error processing {repo_url}: {str(e)}")
        return None, None

def analyze_repo_stats(df):
    """
    Analyze repository statistics and print distributions
    """
    print("\nRepository Statistics Analysis:")
    print("=" * 50)
    
    # Stars distribution
    if 'stars' in df.columns:
        print("\nStars Distribution:")
        print(df['stars'].describe())
        print("\nStars Range Counts:")
        bins = [0, 10, 100, 1000, 10000, float('inf')]
        labels = ['0-10', '11-100', '101-1000', '1001-10000', '10000+']
        print(pd.cut(df['stars'], bins=bins, labels=labels).value_counts().sort_index())
    
    # Commit count distribution
    if 'commit_count' in df.columns:
        print("\nCommit Count Distribution:")
        print(df['commit_count'].describe())
        print("\nCommit Count Range Counts:")
        bins = [0, 10, 100, 1000, 10000, float('inf')]
        labels = ['0-10', '11-100', '101-1000', '1001-10000', '10000+']
        print(pd.cut(df['commit_count'], bins=bins, labels=labels).value_counts().sort_index())
    
    # # File count distribution
    # if 'file_count' in df.columns:
    #     print("\nFile Count Distribution:")
    #     print(df['file_count'].describe())
    #     print("\nFile Count Range Counts:")
    #     bins = [0, 10, 100, 1000, 10000, float('inf')]
    #     labels = ['0-10', '11-100', '101-1000', '1001-10000', '10000+']
    #     df['files_range'] = pd.cut(df['file_count'], bins=bins, labels=labels)
    #     print(df['files_range'].value_counts().sort_index())
    
    # # Total lines distribution
    # if 'total_lines' in df.columns:
    #     print("\nTotal Lines of Code Distribution:")
    #     print(df['total_lines'].describe())
    #     print("\nTotal Lines Range Counts:")
    #     bins = [0, 1000, 10000, 100000, 1000000, float('inf')]
    #     labels = ['0-1K', '1K-10K', '10K-100K', '100K-1M', '1M+']
    #     df['lines_range'] = pd.cut(df['total_lines'], bins=bins, labels=labels)
    #     print(df['lines_range'].value_counts().sort_index())

def filter_csv_by_keywords():
    # Define the keywords to match
    keywords = [
        "Void IDE", "Void AI", 
        "using Void", "Void Agent", "use Void", "with Void", "by Void", "in Void", "through Void", "via Void",
        "claude", "sonnet 3.7", "deepseek", 
        "制作", "实现", "编写", "生成", "创建", "开发", 
        "built", "build", 
        "基于Void", "通过Void", "借助Void", "用void", "由void"
    ]
    
    # Define the exclusion keywords
    exclusion_keywords = [
        "test", "demo", "learn", "practice", "practical", "rule", "rules", "mouse", "pagination", 
        "a void", "重置", "无限试用", "curse", "3D void", "your void", 
        "custom void", "教程", "void navigation", "navigation", "void move", "学习", 
        "资源", "会员", "付费", "订阅", "example", "教学", "课程", "指南", "练习", 
        "awesome", "示例", "movement", "keyboard", "custom", "position", "animat", "pointer", 
        "theme", "attempt", "moving", "move", "Paginate", "Trying", "try", "simple", "quick", 
        "oracle", "store procedure", "mysql", "sql server", "void library", "Drawing", "draw", 
        "prompt", "collection", "hand gesture", "canvas", "click", "void array", "SQL", 
        "experiment", "scrollbar", "Portfolio", "template", "course", "tutorial", "toy", "玩具", 
        "实验", "live void", "guideline", "quiz", "small", "exploring", "realtime", "real-time"
    ]
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the specific input file name
    input_file = os.path.join(script_dir, "void_all_repo.xlsx")
    
    # Check if the file exists
    if not os.path.exists(input_file):
        print(f"Error: File 'filtered_void_repo.xlsx' not found!")
        print(f"Looking in directory: {script_dir}")
        return
    
    print(f"Processing file: {input_file}")
    
    # Read the Excel file
    df = pd.read_excel(input_file)
    
    # Check if the required columns exist
    if len(df.columns) < 2:
        print("Error: Excel file does not have enough columns!")
        return
    
    # Get the description column (second column)
    description_col = df.columns[1]
    
    # Create a function to check if any keyword exists in the description
    def contains_keyword(text):
        if pd.isna(text):
            return False
        return any(keyword.lower() in str(text).lower() for keyword in keywords)
    
    # Create a function to check if any exclusion keyword exists in the description
    def contains_exclusion_keyword(text):
        if pd.isna(text):
            return False
        return any(keyword.lower() in str(text).lower() for keyword in exclusion_keywords)
    
    # Filter the dataframe - first include records with keywords, then exclude records with exclusion keywords
    filtered_df = df[df[description_col].apply(contains_keyword)]
    filtered_df = filtered_df[~filtered_df[description_col].apply(contains_exclusion_keyword)]
    
    # Get GitHub token from environment variable
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("\nWarning: No GitHub token found. API requests will be limited.")
        print("To increase the rate limit, set the GITHUB_TOKEN environment variable.")
        print("You can create a token at: https://github.com/settings/tokens")
    
    # Get GitHub statistics for each repository
    print("\nFetching GitHub statistics for repositories...")
    stats_data = []
    status_codes = []  # 用于存储每个仓库的状态码
    
    for url in tqdm(filtered_df['url']):
        stats, status_code = get_github_stats(url, github_token)
        if stats:
            stats_data.append(stats)
        else:
            stats_data.append({'stars': None, 'commit_count': None})  # 添加空数据
        status_codes.append(status_code)  # 记录状态码
        time.sleep(1)  # Rate limiting
    
    # 添加状态码列
    filtered_df['status_code'] = status_codes
    
    # Add statistics to the dataframe
    if stats_data:
        stats_df = pd.DataFrame(stats_data)
        # 检查行数是否匹配
        if len(stats_df) != len(filtered_df):
            print(f"\nError: Number of rows mismatch!")
            print(f"Filtered DataFrame rows: {len(filtered_df)}")
            print(f"Stats DataFrame rows: {len(stats_df)}")
            print("Please check the data consistency.")
            return
        filtered_df = pd.concat([filtered_df.reset_index(drop=True), stats_df], axis=1)
    
    # Analyze and print statistics
    analyze_repo_stats(filtered_df)
    
    # Generate output filename
    output_file = os.path.join(script_dir, f"filtered_{os.path.basename(input_file)}")
    
    # Save the filtered results
    filtered_df.to_excel(output_file, index=False)
    print(f"\nFiltered results saved to: {output_file}")
    print(f"Original records: {len(df)}")
    print(f"Filtered records: {len(filtered_df)}")

if __name__ == "__main__":
    filter_csv_by_keywords()
