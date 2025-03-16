from colorama import init, Fore
import re
import os
import json, argparse
from pathlib import Path


def try_find_path_utf8(content: bytes, extension: str):
    # Replace SOH and NUL bytes with an empty byte string
    cleaned_content = content.replace(
        b'\x01', b'').replace(b'\x00', b'')

    # The regex pattern for a Windows file path with the actual file extension
    pattern = rb'[A-Z]:\\[^:]*\.' + extension.encode()

    # Search for the pattern in the cleaned content
    match = re.search(pattern, cleaned_content)
    if match:
        # Convert the binary match to a readable string path
        original_location = match.group(0).decode("utf-8")
        return original_location
    else:
        return None

def get_original_location(broken_file_path, extension: str, errs: dict):
    """
    This function reads the binary content of a broken file, removes SOH and NUL bytes,
    and searches for the original file location based on a regex pattern.
    """
    try:
        with open(broken_file_path, 'rb') as f:
            content = f.read()  # Read the entire binary content of the file

            pc = content.decode("utf-16le", errors="ignore")

            # The regex pattern for a Windows file path with the actual file extension
            pattern = r'[A-Z]:\\[^:]*\.' + extension

            # Search for the pattern in the cleaned content
            match = re.search(pattern, pc)

            if match:
                original_location = match.group(0)
                return original_location
            else:
                up = try_find_path_utf8(content, extension)
                if up:
                    return up
                err = [f"Original location not found in: {broken_file_path}"]
                errs["errors"] = err
                return None
    except Exception as e:
        err = [f"Error reading broken file {broken_file_path}: {e}"]
        errs["errors"] = err
        return None


def find_file_and_folder_pairs_with_original_location(current_directory=os.getcwd()):
    # Dictionaries to hold actual and broken files/folders
    actual_items = {}
    broken_items = {}

    # Traverse the directory and gather both files and folders
    for root, dirs, files in os.walk(current_directory):
        # Process directories
        for dir_name in dirs:
            if dir_name.startswith('$R') and len(dir_name) > 2:
                item_id = dir_name[2:]  # Extract the folder ID after $R
                actual_items[item_id] = os.path.join(root, dir_name)
            elif dir_name.startswith('$I') and len(dir_name) > 2:
                item_id = dir_name[2:]  # Extract the folder ID after $I
                broken_items[item_id] = os.path.join(root, dir_name)

        # Process files
        for file_name in files:
            if file_name.startswith('$R') and len(file_name) > 2:
                item_id = file_name[2:]  # Extract the file ID after $R
                actual_items[item_id] = os.path.join(root, file_name)
            elif file_name.startswith('$I') and len(file_name) > 2:
                item_id = file_name[2:]  # Extract the file ID after $I
                broken_items[item_id] = os.path.join(root, file_name)

    # Pair the actual items with their corresponding broken items and find original locations
    item_pairs = {}
    missing_broken = []
    missing_actual = []

    for item_id, actual_item_path in actual_items.items():
        if item_id in broken_items:
            broken_item_path = broken_items[item_id]
            # Get the file extension from the actual file path (e.g., 'json' for file.json)
            # Extract the extension without the dot
            extension = os.path.splitext(actual_item_path)[1][1:]
            errors = {}
            original_location = get_original_location(
                broken_item_path, extension, errors)
            item_pairs[actual_item_path] = {
                'broken': broken_item_path,
                'original_location': original_location,
                # Check if it's a directory
                'is_directory': os.path.isdir(actual_item_path),
                "errors": errors.get("errors", [])
            }
        else:
            missing_broken.append(actual_item_path)

    # Check for missing actual items
    for item_id, broken_item_path in broken_items.items():
        if item_id not in actual_items:
            missing_actual.append(broken_item_path)

    return item_pairs, missing_broken, missing_actual


def write_json(items, missing_broken, missing_actual, short: bool):
    return json.dumps({
            "items": items,
            "missing_broken": missing_broken,
            "missing_actual": missing_actual
        }, indent=0 if short else 2, ensure_ascii=False)


def print_data(item_pairs: dict, missing_broken: list, missing_actual: list):
    for actual_item, data in item_pairs.items():
        broken = data["broken"]
        loc = data["original_location"]
        is_directory = data['is_directory']

        if loc is None:
            print(Fore.RED + "MISSING LOC:")
        else:
            # Append "(DIR)" in light blue if it's a directory
            location_output = (Fore.LIGHTBLUE_EX + "(DIR) " if is_directory else "") + \
                f"{Fore.LIGHTGREEN_EX}{loc}"
            print(location_output)

        print(Fore.LIGHTRED_EX + "\tRemoved: " + actual_item)
        print(Fore.LIGHTYELLOW_EX + "\tInfo: " + broken)
        for err in data["errors"]:
            print(f"\tE: {err}")

    # Print missing files and folders
    if missing_broken:
        print(Fore.RED + "Missing info files:")
        for missing in missing_broken:
            print(Fore.RED + "\tfor actual " + missing)

    if missing_actual:
        print(Fore.YELLOW + "Missing actual files:")
        for missing in missing_actual:
            print(Fore.YELLOW + "\tfor info " + missing)

def main():
    parser = argparse.ArgumentParser(
        description="Collects info about files in recycle bin")

    # First required argument: directory path
    parser.add_argument('folder', type=Path, help='Path to recycle bin folder')

    # Second optional argument: file path
    parser.add_argument('export', type=Path, nargs='?',
                        default=Path("data.json"), help='Optional path where to export')

    parser.add_argument("--raw", action="store_true",
                        default=False, help="Set for export to stdout")

    args = parser.parse_args()

    item_pairs, missing_broken, missing_actual = find_file_and_folder_pairs_with_original_location(args.folder)
    if args.raw:
        t = write_json(item_pairs, missing_broken, missing_actual, True)
        print(t)
        pass
    else:
        init(autoreset=True)
        print_data(item_pairs, missing_broken, missing_actual)
        print("== Writing Json == ")
        jfile = args.export
        with open(jfile, "w", encoding="utf-8") as f:
            t = write_json(item_pairs, missing_broken, missing_actual, False)
            f.write(t)
        print(f"Written to {jfile}")

if __name__ == "__main__":
    main()