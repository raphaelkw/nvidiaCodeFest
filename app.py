import streamlit as st
import openai
import os 


import nest_asyncio
nest_asyncio.apply()
from llama_parse import LlamaParse
from openai import OpenAI

os.environ["LLAMA_CLOUD_API_KEY"] = "llx-oi3ZbThAISM1BqeRNdQl8tpSP2hzoBPuSJRvku2BcvJ0w4m4"

parsing_instruction = """
You are parsing a report. Follow these strict rules:
- Do not edit, modify, or correct any content
- Preserve all original text exactly as it appears
- YOU should identify and note text formatting like:
  * Bold text (**text** or __text__)
  * Italic text (*text* or _text_)
  * Bold and italic text (***text*** or ___text___)
  * Strikethrough text (~~text~~)
  * Code formatting (`text`)
- Maintain the original case/capitalization of all letters and words
- Keep all original spacing and formatting
- Do not fix any spelling or grammar
- Do not add or remove any characters
- Parse and extract content only, with no modifications
"""

parser = LlamaParse(
    api_key=os.environ["LLAMA_CLOUD_API_KEY"], 
    result_type="markdown",  # "markdown" and "text" are available
    num_workers=4,  
    verbose=True,
    parsing_instruction = parsing_instruction,
    language="en"
)

SYSTEM_PROMPT = """
You are a specialized report validator that analyzes report for compliance with predefined criteria. You will receive report in markdown format and evaluate them against relevant criteria from this list:

{criteria_list}

Important guidelines:
- Do not flag missing criteria checks when the section does not contain relevant content to evaluate
- Provide specific examples and locations when flagging non-compliance
- If a criterion requires cross-referencing with other sections (e.g., table calculations), note that validation is pending until all relevant sections are available
- Focus on constructive feedback and suggest corrections when possible
- You must check the entire report

For each validation, respond with:
1. The section CHECKED, not the criteria
2. Only Specific details for any failures
3. Suggestions for corrections
"""

def format_criteria_list(criteria_list):
    return "\n".join(f"{i+1}. {criteria}" for i, criteria in enumerate(criteria_list))


def parse_docx_to_markdown(file_object, file_name):
    print(f"Processing file: {file_name}")
    extra_info = {"file_name": file_name}
   
    # must provide extra_info with file_name key with passing file object
    documents = parser.load_data(file_object, extra_info=extra_info)

    contents = ' '.join(doc.text for doc in documents)

    # print('Contents: ', contents)
    return contents


# Function to call the LLM
def analyze_document(markdown_contents, checks):
    final_system_prompt = SYSTEM_PROMPT.format(criteria_list=checks)

    client = OpenAI(
      base_url = "http://localhost:11235/v1",
      api_key = "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"
    )
    # Create a Streamlit placeholder for the streaming response
    response_placeholder = st.empty()
    full_response = ""

    # Use stream=True parameter
    stream = client.chat.completions.create(
        model="nvidia/llama-3.1-nemotron-70b-instruct",
        messages=[
            {"role": "system", "content": f"{final_system_prompt}"},
            {
                "role": "user",
                "content": f"Document: {markdown_contents}"
            }
        ],
        temperature=0.0001,
        stream=True
    )

    # Process the streaming response
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            # Convert markdown to HTML and display
            response_placeholder.markdown(full_response)

    return full_response

# Streamlit App
st.title("AOR Validator App")

# Step 1: Input Text
st.subheader("Step 1: Upload an AOR Document or Enter Text")
uploaded_file = st.file_uploader("Upload a .docx file", type=["docx"])


if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name
    file_contents = parse_docx_to_markdown(file_object=file_bytes, file_name=file_name)
    st.success("Markdown extracted from the uploaded document!")
else:
    file_contents = None

# Step 2: Specify Checks
st.subheader("Step 2: Specify the Checks")

default_checks = [
    "Table of Contents includes annexes and section headers",
    "The headers should be capitalized and BOLDED",
    "Decimal points are round off to whole number in Cost figures",
    "Non-cost related figures MUST BE rounded off to 2 decimal places",
    "Datetime Format MUST follow ISO standard",
    "Grammar check",
    "Sentence Structure check", 
    "Relevant sections included based on Report Title (Include Basic AOR Information if Supplementary AOR Submission)",
    "Approving Authority in Para 1 and ARO banner matches AOR type (Cat 1A,1B, 1C, 2, 3). GST included for Cat 1C",
    "Section Typography (Bold, Underline, Italic, Strikethrough, Size)",
    "Diagrams labeled correctly and chronologically (Figure 1.0, 1.2)",
    "Tables labeled correctly and chronologically (Table 1.0, 1.2)", 
    "Spot check calculations for numbers across 2 different tables"
]
selected_checks = st.multiselect(
    "Select checks you want to perform:",
    options=default_checks,
    default=default_checks  # This makes all checks selected by default
)
custom_check = st.text_area("Or, specify your own checks")

# Combine selected and custom checks
if custom_check:
    selected_checks.append(custom_check)

checks = ", ".join(selected_checks)

# Step 3: Analyze with LLM
st.subheader("Step 3: Analyze the Report")
if st.button("Run Analysis"):
    if file_contents and checks:
        with st.spinner("Analyzing..."):
            result = analyze_document(file_contents, checks)
        st.success("Analysis Complete!")
        # st.text_area("Results:", result, height=300)
    else:
        st.error("Please provide input text and specify checks.")
