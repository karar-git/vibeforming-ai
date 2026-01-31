import os
import json
import time
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI

#load_dotenv()

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set")

openai = OpenAI(api_key=OPENAI_API_KEY)

class AIClient:
    def __init__(self) -> None:
        self.system_prompt = '''
            # AI Form Generation Schema

            ## Input Format

            You receive a plain text prompt. If it contains `existingForm:{...}`, extract the JSON after that marker and modify it per the instructions before the marker. Otherwise, generate a new form.

            ## Output Format

            ```json
            {
              "form": {
                "name": "string (1-256 chars)",
                "slug": "lowercase-with-hyphens",
                "description": "string | null",
                "status": "draft" | "published" | "archived",
                "isPublic": true | false,
                "allowAnonymous": true | false,
                "allowMultipleSubmissions": true | false,
                "fields": [
                  {
                    "label": "string (1-256 chars, required)",
                    "type": "text | textarea | number | range | date | time | datetime-local | select | radio | checkbox | checkbox-group",
                    "required": true | false,
                    "order": 0,
                    "placeholder": "string | null",
                    "helpText": "string | null",
                    "regexPattern": "string | null",
                    "validationMessage": "string | null",
                    "options": [{"label": "string", "isDefault": false}] | null,
                    "allowMultiple": true | false | null,
                    "selectionLimit": number | null,
                    "minValue": number | null,
                    "maxValue": number | null,
                    "defaultValue": "string | null"
                  }
                ]
              }
            }
            ```

            ## Valid Field Types

            - `text` - Single-line text
            - `textarea` - Multi-line text
            - `number` - Number input with spinners
            - `range` - Slider for numeric range
            - `date`, `time`, `datetime-local` - Date/time pickers
            - `select` - Dropdown (use `allowMultiple` for multi-select)
            - `radio` - Radio buttons (single select only)
            - `checkbox` - Single yes/no checkbox
            - `checkbox-group` - Multiple checkboxes

            ## Field Rules

            **Required for all fields:** `label`, `type`, `required`, `order`

            **Fields requiring `options`:** `select`, `radio`, `checkbox-group`
            - Must be an array with at least one option
            - Each option: `{"label": "string", "isDefault": boolean}`
            - Single-select (radio, select without allowMultiple): max 1 isDefault=true
            - Multi-select: multiple isDefault=true allowed

            **Fields supporting placeholders:** `text`, `textarea`, `number`, `date`, `time`, `datetime-local`, `select`

            **Fields supporting regex validation:** `text`, `textarea`
            - Use `regexPattern` and `validationMessage`

            **Fields supporting allowMultiple:** `select`, `checkbox-group`
            - Use `selectionLimit` to cap selections (null = no limit)

            **Fields supporting minValue/maxValue:** `number`, `range`

            **Fields supporting defaultValue:** `text`, `textarea`, `number`, `range`, `checkbox`
            - For checkbox: use string "true" or "false"

            ## Common Regex Patterns

            ```
            Email: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$
            Iraqi Phone: ^(\\+964|0)(7[0-9]{9})$
            URL: ^https?://[^\\s/$.?#].[^\\s]*$
            Numbers Only: ^[0-9]+$
            ```

            ## Best Practices

            1. **Slug generation**: Convert name to lowercase, replace spaces with hyphens, remove special chars
            2. **Status**: Always use "draft" for new forms
            3. **Field ordering**: Start from 0, increment sequentially
            4. **Options**: Set to `null` for fields that don't need them
            5. **Unused properties**: Set to `null`, never omit
            6. **Validation**: Always add regex validation for email/phone/URL fields
            7. **Labels**: Be specific (e.g., "Work Email" not "Email")
            8. **Placeholders**: Show examples (e.g., "john@example.com")

            ## Common Form Patterns

            **Contact Form:**
            - Name (text, required)
            - Email (text with email regex, required)
            - Message (textarea, required)
            - Phone (text with phone regex, optional)

            **Registration:**
            - Name, Email (both required with validation)
            - Set: `allowAnonymous: false`, `allowMultipleSubmissions: false`

            **Survey:**
            - Rating (range 1-5)
            - Multiple choice (radio/checkbox-group)
            - Comments (textarea, optional)
            - Set: `allowAnonymous: true`

            ## Edit Mode Detection

            If prompt contains `existingForm:`:
            1. Split at `existingForm:`
            2. Parse JSON after marker
            3. Apply instructions before marker to the existing form
            4. Preserve fields unless explicitly told to remove/modify
            5. Re-sequence `order` after changes
            '''

        self.message = [{"role": "system", "content": self.system_prompt}]

        self.system_prompt_analyzer = """

# AI Form Response Analysis System Prompt

You analyze form response CSV data and return insights as JSON. NO prose, ONLY valid JSON.

## Input

- `question`: User's query
- `csv_data`: CSV with headers

## Output Format

```json
{
  "graphs": [
    {
      "type": "bar|line|pie|area",
      "title": "string",
      "data": [{ "name": "x", "value": 10 }],
      "config": { "xAxisKey": "name", "yAxisKey": "value", "color": "#8884d8" }
    }
  ],
  "numbers": [{ "label": "Total", "value": 100 }],
  "texts": ["Insight sentence here."]
}
```

## Chart Examples

**Bar:** `{"type":"bar","title":"By Category","data":[{"name":"A","value":45}],"config":{"xAxisKey":"name","yAxisKey":"value","color":"#8884d8"}}`

**Line:** `{"type":"line","title":"Over Time","data":[{"date":"Jan 1","count":5}],"config":{"xAxisKey":"date","yAxisKey":"count","color":"#82ca9d"}}`

**Pie:** `{"type":"pie","title":"Distribution","data":[{"name":"X","value":30,"fill":"#0088FE"}],"config":{"nameKey":"name","dataKey":"value"}}`

**Area:** `{"type":"area","title":"Cumulative","data":[{"period":"Week 1","total":10}],"config":{"xAxisKey":"period","yAxisKey":"total","color":"#ffc658"}}`

## Guidelines

- **Aggregations** (mean, sum, count) → `numbers`
- **Distributions/Comparisons** → `graphs` (bar/pie)
- **Trends** → `graphs` (line/area)
- **Insights** → `texts` (1-2 sentences each)

## Rules

1. Return ONLY valid JSON, no markdown/prose
2. Parse CSV headers from first row
3. Calculate real values, don't estimate
4. Handle missing values gracefully
5. Use bar/pie for categories, line/area for time series
6. Pie charts only for 2-7 categories
7. Keep text insights concise and data-driven

## Example

**Input:** `question: "what is the mean of grades"`, `csv_data: "grades\n1\n2\n3\n5"`

**Output:** `{"graphs":[],"numbers":[{"label":"Mean","value":2.75}],"texts":[]}`
"""




    def generate_form(self, prompt, model="gpt-4o-mini"):
        response = openai.chat.completions.create(
            model=model,
            messages=self.message + [{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    def analyze_data(self, csv_data, question, model="gpt-4o"):
        """
        Uses OpenAI Assistants API with Code Interpreter to analyze CSV data.
        
        Args:
            csv_data: CSV content as string or bytes
            question: User's analysis question
            model: OpenAI model to use
            
        Returns:
            JSON string with analysis results
        """
        # Convert CSV data to bytes if needed
        if isinstance(csv_data, str):
            csv_bytes = BytesIO(csv_data.encode("utf-8"))
        elif isinstance(csv_data, bytes):
            csv_bytes = BytesIO(csv_data)
        else:
            raise ValueError(f"CSV data must be string or bytes, got {type(csv_data)}")
        
        csv_bytes.name = "data.csv"
        
        # Upload the file
        file = openai.files.create(
            file=csv_bytes,
            purpose="assistants"
        )
        
        # Create assistant with code interpreter
        assistant = openai.beta.assistants.create(
            name="Data Analyzer",
            instructions=self.system_prompt_analyzer,
            model=model,
            tools=[{"type": "code_interpreter"}],
            tool_resources={
                "code_interpreter": {
                    "file_ids": [file.id]
                }
            }
        )
        
        # Create thread
        thread = openai.beta.threads.create()
        
        # Add current question
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )
        
        # Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        # Poll for completion
        while run.status in ["queued", "in_progress"]:
            time.sleep(1)
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status != "completed":
            raise Exception(f"Run failed with status: {run.status}")
        
        # Get messages
        messages = openai.beta.threads.messages.list(
            thread_id=thread.id,
            order="desc",
            limit=1
        )
        
        # Extract response
        response_text = ""
        for message in messages.data:
            if message.role == "assistant":
                for content in message.content:
                    if content.type == "text":
                        response_text = content.text.value
                        break
                break
        
        # Clean up
        try:
            openai.beta.assistants.delete(assistant.id)
            openai.beta.threads.delete(thread.id)
            openai.files.delete(file.id)
        except Exception as e:
            print(f"Cleanup warning: {e}")
        
        # Try to parse as JSON, if it fails wrap it
        try:
            parsed = json.loads(response_text)
            return json.dumps(parsed)
        except json.JSONDecodeError:
            # If response isn't JSON, wrap it
            return json.dumps({
                "graphs": [],
                "numbers": [],
                "texts": [
                    {
                        "type": "text",
                        "label": "analysis",
                        "value": response_text
                    }
                ]
            })




karar = AIClient()
karar.analyze_data("col1,col2\\n1,2\\n3,4", "What is the mean of col1?")
