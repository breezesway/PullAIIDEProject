#!/usr/bin/env python3
import os
import csv
import glob
import sys
from datetime import datetime

def process_csv_files():
    """
    读取当前目录下的所有CSV文件，删除match_location列，合并数据并去重，
    然后将结果保存到一个新的CSV文件中。
    """
    # 增加CSV字段大小限制
    csv.field_size_limit(sys.maxsize)
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取当前目录下的所有CSV文件
    csv_files = glob.glob(os.path.join(script_dir, '*.csv'))
    if not csv_files:
        print(f"在目录 {script_dir} 下没有找到CSV文件")
        return
    
    print(f"找到以下CSV文件: {csv_files}")
    
    # 存储所有的行，使用仓库名称作为key来去重
    repo_data = {}
    fieldnames = []
    
    # 读取所有CSV文件并合并数据
    for csv_file in csv_files:
        print(f"正在处理文件: {csv_file}")
        try:
            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                # 检查是否有列名
                if not fieldnames:
                    # 移除不需要的列
                    fieldnames = [field for field in reader.fieldnames if field not in ['match_location', 'stars']]
                
                # 读取数据，排除不需要的列
                for row in reader:
                    try:
                        # 检查必要的字段是否存在
                        if 'name' not in row or not row['name']:
                            print(f"警告: 跳过缺少name字段的行: {row}")
                            continue
                            
                        # 使用仓库名称作为key
                        repo_name = row['name']
                        
                        # 如果这个仓库已经存在，检查是否需要更新found_by字段
                        if repo_name in repo_data:
                            # 如果有新的found_by信息，合并它
                            existing_found_by = repo_data[repo_name]['found_by']
                            new_found_by = row.get('found_by', '')
                            
                            # 合并found_by字段，避免重复
                            found_by_items = set(existing_found_by.split(", "))
                            found_by_items.update(new_found_by.split(", "))
                            
                            repo_data[repo_name]['found_by'] = ", ".join(found_by_items)
                            
                            # 更新其他字段
                            for field in fieldnames:
                                if field != 'found_by':
                                    repo_data[repo_name][field] = row.get(field, '')
                        else:
                            # 创建新记录，不包含不需要的字段
                            repo_data[repo_name] = {field: row.get(field, '') for field in fieldnames}
                    except Exception as e:
                        print(f"处理行时出错: {str(e)}")
                        print(f"问题行数据: {row}")
                        continue
                        
        except Exception as e:
            print(f"处理文件 {csv_file} 时出错: {str(e)}")
            continue
    
    # 检查是否有数据
    if not repo_data:
        print("没有找到有效的数据")
        return
    
    # 创建输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(script_dir, f'cursor_merged_repos_{timestamp}.csv')
    
    # 写入新的CSV文件
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(repo_data.values())
    
    print(f"成功将{len(repo_data)}个去重后的仓库信息写入到 {output_file}")

if __name__ == "__main__":
    process_csv_files() 