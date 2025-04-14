import requests
import os
import time
import csv
from datetime import datetime
from typing import List, Dict, Set

class GitHubSearch:
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = "https://api.github.com"
        self.repos: Dict[str, Dict] = {}  # 存储所有搜索结果
        self.current_search_repos: Dict[str, Dict] = {}  # 存储当前搜索循环的结果
        self.per_page = 100
        self.max_results = 1000
        # 确保trae文件夹存在
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)

    def _check_rate_limit(self, response) -> bool:
        """Check GitHub API rate limit and wait if necessary."""
        rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
        
        if rate_limit_remaining <= 1:
            wait_time = max(rate_limit_reset - int(time.time()), 0) + 10
            print(f"\nRate limit reached. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            return True
        return False

    def _make_request(self, url: str, params: Dict) -> Dict:
        """Make a request with rate limit handling and pagination."""
        all_items = []
        total_count = 0
        page = 1
        
        while True:
            try:
                # Add page parameter
                params['page'] = page
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()
                
                if not self._check_rate_limit(response):
                    data = response.json()
                    if page == 1:
                        total_count = data['total_count']
                        print(f"Total repositories found: {total_count} repositories with query: {url}")
                    
                    items = data['items']
                    if not items:  # No more items
                        break
                        
                    all_items.extend(items)
                    print(f"Fetched page {page}, total items: {len(all_items)}")
                    
                    # Check if we've fetched all items or reached the maximum
                    if len(all_items) >= min(total_count, self.max_results):
                        break
                        
                    page += 1
                    # Add a small delay between pages to avoid rate limiting
                    time.sleep(1)
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    wait_time = max(int(e.response.headers.get('X-RateLimit-Reset', 0)) - int(time.time()), 0) + 10
                    print(f"Rate limit reached. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"HTTP error occurred: {e}")
                    break
            except requests.exceptions.RequestException as e:
                print(f"Request error occurred: {e}")
                break
        
        return {'items': all_items, 'total_count': total_count}

    def _add_repository(self, repo_data: Dict, found_by: str, is_current_search: bool = True) -> None:
        """Add a repository to the results or update its found_by information."""
        # Handle different response structures
        if 'repository' in repo_data:
            # For code search results
            repo = repo_data['repository']
        else:
            # For other search results
            repo = repo_data
            
        repo_name = repo['full_name']
        repo_info = {
            'url': repo['html_url'],
            'description': repo.get('description', 'No description'),
            'found_by': found_by
        }

        # Add to current search results
        if is_current_search:
            if repo_name not in self.current_search_repos:
                self.current_search_repos[repo_name] = repo_info
            else:
                if found_by not in self.current_search_repos[repo_name]['found_by']:
                    self.current_search_repos[repo_name]['found_by'] += f", {found_by}"

        # Add to all results
        if repo_name not in self.repos:
            self.repos[repo_name] = repo_info
        else:
            if found_by not in self.repos[repo_name]['found_by']:
                self.repos[repo_name]['found_by'] += f", {found_by}"

    def _save_search_results(self, search_type: str, repos_dict: Dict[str, Dict], timestamp: str = None) -> None:
        """Save the search results for a specific search type to a CSV file."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        csv_filename = os.path.join(self.output_dir, f'trae_{search_type}_{timestamp}.csv')
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'url', 'description', 'found_by']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for repo_name, info in sorted(repos_dict.items(), key=lambda x: x[1]['found_by']):
                row = {'name': repo_name}
                row.update(info)
                writer.writerow(row)
        
        print(f"\nResults for {search_type} saved to {csv_filename}")
        print(f"Total unique repositories found by {search_type}: {len(repos_dict)}")

    def search_code(self, query: str, sort_order: Dict[str, str], is_current_search: bool = True) -> None:
        """Search code content using GitHub's code search API."""
        url = f"{self.base_url}/search/code"
        params = {
            'q': query,
            'per_page': self.per_page,
            'sort': sort_order['sort'],
            'order': sort_order['order']
        }

        data = self._make_request(url, params)
        total_count = data['total_count']

        for item in data['items']:
            self._add_repository(item, f"code_search: {query} ({sort_order['sort']} {sort_order['order']})", 
                               is_current_search)
            
        print(f"Current unique repositories collected: {len(self.current_search_repos if is_current_search else self.repos)}")

    def search_commits(self, query: str, is_current_search: bool = True) -> None:
        """Search commit messages using GitHub's commit search API."""
        url = f"{self.base_url}/search/commits"
        params = {
            'q': query,
            'per_page': self.per_page
        }

        data = self._make_request(url, params)
        total_count = data['total_count']

        for item in data['items']:
            self._add_repository(item['repository'], f"commit_search: {query}", 
                               is_current_search)
            
        print(f"Current unique repositories collected: {len(self.current_search_repos if is_current_search else self.repos)}")

    def search_issues(self, query: str, is_current_search: bool = True) -> None:
        """Search issues and pull requests using GitHub's issue search API."""
        url = f"{self.base_url}/search/issues"
        
        # 定义时间范围列表，从2024年7月1日开始，每6个月为一个时间段
        time_ranges = [
            ("2024-07-01", "2024-12-31"),
            ("2025-01-01", "2025-06-30"),
        ]
        
        for start_date, end_date in time_ranges:
            time_filter = f"created:{start_date}..{end_date}"
            params = {
                'q': f"{query} {time_filter}",
                'per_page': self.per_page
            }
            
            print(f"\nSearching issues from {start_date} to {end_date}")
            data = self._make_request(url, params)
            total_count = data['total_count']
            
            for item in data['items']:
                # 从repository_url中提取仓库信息
                repo_url = item['repository_url']
                # 从URL中提取owner和repo name
                # URL格式类似：https://api.github.com/repos/owner/repo
                parts = repo_url.split('/')
                if len(parts) >= 5:
                    owner = parts[-2]
                    repo_name = parts[-1]
                    # 构建完整的仓库信息
                    repo_info = {
                        'full_name': f"{owner}/{repo_name}",
                        'html_url': f"https://github.com/{owner}/{repo_name}",
                        'description': ''  # 如果需要描述，可以再调用API获取
                    }
                    self._add_repository(repo_info, f"issue_search: {query} ({start_date} to {end_date})", is_current_search)
                else:
                    print(f"Warning: Invalid repository URL format: {repo_url}")
                
            print(f"Current unique repositories collected: {len(self.current_search_repos if is_current_search else self.repos)}")

    def save_results(self) -> None:
        """Save all search results to a combined CSV file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = os.path.join(self.output_dir, f'trae_all_repositories_{timestamp}.csv')
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'url', 'description', 'found_by']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for repo_name, info in sorted(self.repos.items(), key=lambda x: x[1]['found_by']):
                row = {'name': repo_name}
                row.update(info)
                writer.writerow(row)
        
        print(f"\nAll results saved to {csv_filename}")
        print(f"Total unique repositories found: {len(self.repos)}")

def main():
    # Get GitHub token from environment variable
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set")
        print("Please set your GitHub token as an environment variable:")
        print("export GITHUB_TOKEN='your_token_here'")
        return
    
    # Initialize GitHub search
    searcher = GitHubSearch(token)
    
    # Trae-related keywords
    trae_keywords = [
        "generated by Trae",
        "edited using Trae",
        "developed with Trae",
        "powered by Trae",
        "AI coding with Trae",
        "Trae suggestion",
        "applied Trae edit",
        "auto refactor by Trae",
        "refactored with Trae",
        "Trae-assisted change",
        "accept suggestion from Trae",
        "used Trae for this part",
        "Generated using Anysphere Trae",
        "Auto-generated with Trae AI"
    ]
    
    # Sort orders for code search
    sort_orders = [
        {'sort': 'indexed', 'order': 'desc'},
        {'sort': 'indexed', 'order': 'asc'}
    ]
    
    print("Starting search for Trae-related repositories...")
    
    # Search code content for keywords
    for keyword in trae_keywords:
        for sort_order in sort_orders:
            searcher.search_code(f'"{keyword}"', sort_order)
    searcher._save_search_results("code_keywords", searcher.current_search_repos)
    searcher.current_search_repos.clear()
    
    # Search commit messages
    for keyword in trae_keywords:
        searcher.search_commits(f'"{keyword}"')
    searcher._save_search_results("commit_messages", searcher.current_search_repos)
    searcher.current_search_repos.clear()
    
    # Search issues and PRs
    for keyword in trae_keywords:
        searcher.search_issues(f'"{keyword}"')
    searcher._save_search_results("issues_and_prs", searcher.current_search_repos)
    searcher.current_search_repos.clear()
    
    # Save all results
    searcher.save_results()

if __name__ == "__main__":
    main() 