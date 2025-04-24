import requests
import os
import time
from datetime import datetime
from typing import Dict
import pandas as pd

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
        # 确保windsurf文件夹存在
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
        repo_name = repo_data['full_name']
        repo_info = {
            'url': repo_data['html_url'],
            'description': repo_data.get('description', 'No description'),
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
        """Save the search results for a specific search type to an Excel file."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        excel_filename = os.path.join(self.output_dir, f'windsurf_{search_type}_{timestamp}.xlsx')
        
        # Convert dictionary to DataFrame
        data = []
        for repo_name, info in sorted(repos_dict.items(), key=lambda x: x[1]['found_by']):
            row = {'name': repo_name}
            row.update(info)
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_excel(excel_filename, index=False)
        
        print(f"\nResults for {search_type} saved to {excel_filename}")
        print(f"Total unique repositories found by {search_type}: {len(repos_dict)}")

    def search_repositories_by_description(self, query: str, is_current_search: bool = True) -> None:
        """Search repositories by description using time-based pagination."""
        url = f"{self.base_url}/search/repositories"
        
        # 定义时间范围列表
        time_ranges = [
            ("2024-11-01", "2024-11-30"),
            ("2024-12-01", "2024-12-31"),
            ("2025-01-01", "2025-01-31"),
            ("2025-02-01", "2025-02-28"),
            ("2025-03-01", "2025-03-15"),
            ("2025-03-16", "2025-03-31"),
            ("2025-04-01", "2025-04-15"),
            ("2025-04-16", "2025-04-30"),
        ]
        
        # 对每个时间范围进行搜索
        for start_date, end_date in time_ranges:
            time_filter = f"created:{start_date}..{end_date}"
            params = {
                'q': f"{query} in:description {time_filter}",
                'per_page': self.per_page,
                'sort': 'stars',
                'order': 'desc'
            }
            
            print(f"\nSearching repositories from {start_date} to {end_date}")
            data = self._make_request(url, params)
            total_count = data['total_count']
            
            for item in data['items']:
                self._add_repository(item, f"repo_description: {query} ({start_date} to {end_date})", is_current_search)
            
            print(f"Found {len(data['items'])} repositories in this time period")
            print(f"Current unique repositories collected: {len(self.current_search_repos if is_current_search else self.repos)}")
            
            # 添加短暂延迟以避免触发速率限制
            time.sleep(1)

    def save_results(self) -> None:
        """Save all search results to a combined Excel file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = os.path.join(self.output_dir, f'windsurf_all_repositories_{timestamp}.xlsx')
        
        # Convert dictionary to DataFrame
        data = []
        for repo_name, info in sorted(self.repos.items(), key=lambda x: x[1]['found_by']):
            row = {'name': repo_name}
            row.update(info)
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_excel(excel_filename, index=False)
        
        print(f"\nAll results saved to {excel_filename}")
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
    
    print("Starting search for Windsurf-related repositories...")
    
    # Search repositories by description
    searcher.search_repositories_by_description("Windsurf")
    
    # Save all results
    searcher.save_results()

if __name__ == "__main__":
    main() 