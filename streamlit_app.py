import streamlit as st
import pandas as pd
import re

# Initialize session state for delete values, file list input, and default delete values
if 'delete_values' not in st.session_state:
    st.session_state.delete_values = []

if 'file_list_input' not in st.session_state:
    st.session_state.file_list_input = ""

if 'result_text_global' not in st.session_state:
    st.session_state.result_text_global = ""

if 'default_values' not in st.session_state:
    st.session_state.default_values = []

# Function to display help content based on uploaded files
def open_help_window(help_type, help_files):
    help_file_names = {
        "triage": "how-to-triage.txt",
        "workbench": "how-to-use-workbench.txt",
        "reorder": "how-to-reorder.png",
        "userids": "userids-to-writer-names.txt"
    }

    if help_files:
        for file in help_files:
            if file.name == help_file_names[help_type]:
                if file.name.endswith(".png"):
                    st.image(file, caption=file.name)
                else:
                    content = file.read().decode('utf-8')
                    st.markdown(content)
                return
        st.error(f"Help file '{help_file_names[help_type]}' not found.")
    else:
        st.error("Upload help files.")

# Function to handle the exclusion of writer blocks and lines
def exclude_items(file_list_text, delete_values):
    lines = file_list_text.strip().split("\n")
    updated_list = []
    excluded_lines = []
    skip_until_next_writer = False
    writer_date_pattern = re.compile(r"^(.+), Date: \d{4}-\d{2}-\d{2}")
    temp_writer_line = None
    writer_block = []

    delete_values = [val.strip().strip("'") for val in delete_values]

    for line in lines:
        writer_match = writer_date_pattern.match(line)
        if writer_match:
            if temp_writer_line and writer_block:
                updated_list.append(temp_writer_line)
                updated_list.extend(writer_block)
            temp_writer_line = line
            writer_block = []
            skip_until_next_writer = False
            continue

        if skip_until_next_writer:
            continue

        exclude_line = False
        for del_value in delete_values:
            clean_del_value = del_value.strip('-')

            if del_value.startswith('-') and del_value.endswith('-'):
                if temp_writer_line and re.search(rf"\b{re.escape(clean_del_value)}\b", temp_writer_line, re.IGNORECASE):
                    skip_until_next_writer = True
                    excluded_lines.append(temp_writer_line)
                    excluded_lines.extend(writer_block)
                    temp_writer_line = None
                    writer_block = []
                    exclude_line = True
                    break

            if clean_del_value in line:
                exclude_line = True
                excluded_lines.append(line)
                break

        if not exclude_line:
            writer_block.append(line)

    if temp_writer_line and writer_block:
        updated_list.append(temp_writer_line)
        updated_list.extend(writer_block)

    return "\n".join(updated_list), "\n".join(excluded_lines)

# Function to reorder results by the most recent activity per writer
def reorder_results(result_text):
    lines = result_text.strip().split("\n")
    writer_blocks = {}
    current_writer = None

    for line in lines:
        if line.strip() == "":
            continue
        if '-' not in line:
            current_writer = line.strip()
            writer_blocks[current_writer] = []
        else:
            writer_blocks[current_writer].append(line.strip())

    writer_file_data = []

    for writer, files in writer_blocks.items():
        sorted_files = sorted(files, key=lambda x: x.split(" - ")[0], reverse=True)
        most_recent_date = sorted_files[0].split(" - ")[0]
        writer_file_data.append({
            "writer": writer,
            "files": sorted_files,
            "most_recent_date": most_recent_date
        })

    writer_file_data.sort(key=lambda x: x['most_recent_date'], reverse=True)

    sorted_result_text = ""
    for writer_data in writer_file_data:
        sorted_result_text += writer_data["writer"] + "\n"
        for file in writer_data["files"]:
            sorted_result_text += file + "\n"
        sorted_result_text += "\n"

    return sorted_result_text

# Function to reorder results by file, then date, then writer
def reorder_file_date_writer(result_text):
    lines = result_text.strip().split("\n")
    writer_blocks = []
    current_writer = None

    for line in lines:
        if line.strip() == "":
            continue
        if '-' not in line:
            current_writer = line.strip()
        else:
            writer_blocks.append((current_writer, line.strip()))

    writer_blocks.sort(key=lambda x: (x[1].split(" - ")[1], x[1].split(" - ")[0], x[0]))

    sorted_result_text = ""
    current_writer = None
    for writer, file in writer_blocks:
        if writer != current_writer:
            if current_writer is not None:
                sorted_result_text += "\n"
            sorted_result_text += writer + "\n"
            current_writer = writer
        sorted_result_text += file + "\n"
    return sorted_result_text

# Function to reorder results by date, then file, then writer
def reorder_date_file_writer(result_text):
    lines = result_text.strip().split("\n")
    writer_blocks = []
    current_writer = None

    for line in lines:
        if line.strip() == "":
            continue
        if '-' not in line:
            current_writer = line.strip()
        else:
            writer_blocks.append((current_writer, line.strip()))

    writer_blocks.sort(key=lambda x: (x[1].split(" - ")[0], x[1].split(" - ")[1], x[0]), reverse=True)

    sorted_result_text = ""
    current_writer = None
    for writer, file in writer_blocks:
        if writer != current_writer:
            if current_writer is not None:
                sorted_result_text += "\n"
            sorted_result_text += writer + "\n"
            current_writer = writer
        sorted_result_text += file + "\n"
    return sorted_result_text

# Function to perform the search
def perform_search(file_list_text, search_term):
    lines = file_list_text.strip().split("\n")
    parsed_data = []
    current_author = None
    current_date = None

    for line in lines:
        if 'Date:' in line:
            author_date_match = re.match(r"(.+), Date: (.+)", line)
            if author_date_match:
                current_author = author_date_match.group(1)
                current_date = author_date_match.group(2)
        else:
            parsed_data.append([current_author, current_date, line])

    df = pd.DataFrame(parsed_data, columns=['author', 'date', 'file'])
    file_list = df['file'].dropna().tolist()

    matches = []
    for file_name in file_list:
        if search_term.lower() in file_name.lower():
            matches.append(file_name)

    if matches:
        unique_writers = {}
        for file_name in matches:
            writer_info = df[df['file'] == file_name].iloc[0]
            author = writer_info['author']
            date = writer_info['date']
            if author not in unique_writers:
                unique_writers[author] = set()
            unique_writers[author].add((date, file_name))

        result_text = ""
        for author, files in unique_writers.items():
            result_text += f"{author}\n"
            for file_info in files:
                result_text += f"{file_info[0]} - {file_info[1]}\n"
            result_text += "\n"
    else:
        result_text = "No matches found\n"

    return result_text

# Streamlit App layout
st.title("Triaging Workbench")

# Upload multiple help files and default-delete-values file
uploaded_help_files = st.file_uploader(
    "Upload help files",
    accept_multiple_files=True,
    type=['txt', 'png', 'jpg', 'jpeg'],
    key='help_files'
)

# Process the 'default-delete-values.txt' file if uploaded
if uploaded_help_files:
    for file in uploaded_help_files:
        if file.name == 'default-delete-values.txt':
            default_content = file.read().decode('utf-8')
            st.session_state.default_values = [val.strip() for val in default_content.splitlines() if val.strip()]
            st.success(f"Default delete values loaded: {', '.join(st.session_state.default_values)}")

# Help buttons in a vertical column
st.write("## Help")
if st.button("How to triage"):
    open_help_window("triage", uploaded_help_files)
if st.button("How to use workbench"):
    open_help_window("workbench", uploaded_help_files)
if st.button("How to re-order results"):
    open_help_window("reorder", uploaded_help_files)
if st.button("User IDs / writers"):
    open_help_window("userids", uploaded_help_files)

# Step 1: Dataset and exclude values
st.header("Step 1: Add dataset and exclude values")
branch_name = st.text_input("1.1 Enter dataset branch name (Optional)")
file_list_input = st.text_area(
    "1.2 Paste in a dataset",
    value=st.session_state.file_list_input,
    height=200
)

# Display default delete values if available
exclude_values_input = st.text_input(
    "1.3 Edit 'exclude' values (optional)",
    ','.join(st.session_state.delete_values or st.session_state.default_values)
)

if st.button("1.4 Save 'exclude' values"):
    st.session_state.delete_values = [
        value.strip() for value in exclude_values_input.split(',') if value.strip()
    ]
    st.success("Exclude values were updated")
    st.text_area("Current Exclude Values", value='\n'.join(st.session_state.delete_values), height=100)

if st.button("1.5 Exclude values from dataset"):
    updated_dataset, excluded_lines = exclude_items(file_list_input, st.session_state.delete_values)
    st.session_state.file_list_input = updated_dataset
    st.text_area("Updated Dataset", value=updated_dataset, height=300)
    st.text_area("Excluded Lines", value=excluded_lines, height=300)

# Step 2: Search the dataset
st.header("Step 2: Search the dataset")
search_term = st.text_input("2.1 Enter filepath substring to search for")

if st.button("2.2 Click to search"):
    st.session_state.result_text_global = perform_search(st.session_state.file_list_input, search_term)
    st.text_area("Search Results", value=st.session_state.result_text_global, height=300)

# Step 3: Review search results
st.header("Step 3: Review search results")

if st.button("Writer-Date-File"):
    sorted_result_text = reorder_results(st.session_state.result_text_global)
    st.text_area("Sorted by Writer-Date-File", value=sorted_result_text, height=300)

if st.button("Date-File-Writer"):
    sorted_result_text = reorder_date_file_writer(st.session_state.result_text_global)
    st.text_area("Sorted by Date-File-Writer", value=sorted_result_text, height=300)

if st.button("File-Date-Writer"):
    sorted_result_text = reorder_file_date_writer(st.session_state.result_text_global)
    st.text_area("Sorted by File-Date-Writer", value=sorted_result_text, height=300)

# Clear results button
if st.button("Clear results"):
    st.session_state.result_text_global = ""
    st.text_area("Results cleared", value="", height=300)
