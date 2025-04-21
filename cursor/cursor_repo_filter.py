import pandas as pd
import os
import glob
import csv

def filter_csv_by_keywords():
    # Define the keywords to match
    keywords = [
        "Cursor IDE", "Cursor AI", 
        "using Cursor", "Cursor Agent", "use Cursor", "with Cursor", "by Cursor", "in Cursor", "through Cursor", "via Cursor",
        "claude", "sonnet 3.7", "deepseek", 
        "制作", "实现", "编写", "生成", "创建", "开发", 
        "built", "build", 
        "基于Cursor", "通过Cursor", "借助Cursor", "用cursor", "由cursor"
    ]
    
    # Define the exclusion keywords
    exclusion_keywords = [
        "test", "demo", "learn", "practice", "rule", "rules", "mouse", "pagination", 
        "a cursor", "重置", "无限试用", "curse", "3D cursor", "your cursor", 
        "custom cursor", "教程", "cursor navigation", "cursor move", "学习", 
        "资源", "会员", "付费", "订阅", "example", "教学", "指南", "练习", 
        "awesome", "示例", "movement", "keyboard", "custom", "position", "animation"
    ]
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find the input Excel file in the script's directory
    input_files = glob.glob(os.path.join(script_dir, "*.xlsx"))
    if not input_files:
        print("No Excel file found!")
        print(f"Looking in directory: {script_dir}")
        return
    
    input_file = input_files[0]
    print(f"Processing file: {input_file}")
    
    # Read the Excel file
    df = pd.read_excel(input_file)
    
    # Check if the required columns exist
    if len(df.columns) < 3:
        print("Error: Excel file does not have enough columns!")
        return
    
    # Get the description column (third column)
    description_col = df.columns[2]
    
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
    
    # Generate output filename
    output_file = os.path.join(script_dir, f"filtered_{os.path.basename(input_file)}")
    
    # Save the filtered results
    filtered_df.to_excel(output_file, index=False)
    print(f"Filtered results saved to: {output_file}")
    print(f"Original records: {len(df)}")
    print(f"Filtered records: {len(filtered_df)}")

if __name__ == "__main__":
    filter_csv_by_keywords()
