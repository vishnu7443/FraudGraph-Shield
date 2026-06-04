import os

def find_file(filename_query, start_dir="d:\\"):
    print(f"Searching for '{filename_query}' starting from '{start_dir}'...")
    matches = []
    
    ignore_dirs = {
        'venv', '.venv', 'node_modules', '.git', '.idea', '__pycache__', 
        'appdata', 'site-packages', 'dist', 'build', 'temp', 'tmp'
    }
    
    for root, dirs, files in os.walk(start_dir):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d.lower() not in ignore_dirs and not d.startswith('.')]
        
        for file in files:
            if filename_query.lower() in file.lower():
                full_path = os.path.join(root, file)
                print(f"Found match: {full_path} ({os.path.getsize(full_path)} bytes)")
                matches.append(full_path)
    
    return matches

if __name__ == "__main__":
    # Let's search D:\
    find_file("DataSet.csv", "d:\\")
    find_file("DataSet.csv", "c:\\Users\\vishnu vardhan")
