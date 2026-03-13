import json
import os
from typing import Dict, List, Tuple
from openai import AzureOpenAI
import config
from inventory.excel_handler import (
    load_inventory, search_records, get_summary,
    find_low_stock, find_duplicates, update_record,
    add_record, format_records,
)

SYSTEM_PROMPT = """You are an AI Inventory Assistant working with an Excel inventory file that has MULTIPLE worksheet tabs.
Your job is to help understand, search, analyze, and update information from ALL sheets through natural conversation.

IMPORTANT: The Excel file has multiple worksheet tabs. Every record has a "_sheet_name" field that tells you which tab it came from. When presenting results:
- ALWAYS mention which sheet/tab the data was found in.
- If the user asks about a specific tab, filter by _sheet_name.
- When searching, search across ALL tabs unless the user specifies one.
- Group results by sheet name when showing data from multiple tabs.

Your responsibilities:
1. Answer questions about the inventory accurately, always stating which sheet the data is from.
2. Search and filter records across all sheets based on user queries.
3. Summarize inventory information when requested.
4. Identify patterns such as low stock, duplicates, or missing data.
5. Update information if the user provides corrected values.
6. Add new records if the user provides complete details.

Rules:
- Only use information from the Excel file. Never invent data.
- When multiple rows match, summarize results clearly and group by sheet.
- If a request is unclear, ask a follow-up question.
- For updates: show current value, proposed new value, sheet name, and ask for confirmation.
- For adding records: confirm all required fields including which sheet before adding.
- Be concise. Use bullet points or tables when helpful.
- Highlight important info like low stock or discrepancies.
- If a question is unrelated to inventory, politely redirect.

Worksheet tabs in this file: {sheet_names}
Available columns across all sheets: {columns}
Total records across all sheets: {total_records}
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_inventory",
            "description": "Search and filter inventory records by column values across ALL worksheet tabs. Use this to find specific items, hostnames, IPs, or any value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Key-value pairs where key is column name and value is search term. Use special key '_any' to search across ALL columns. Examples: {\"_any\": \"SHDPC0165\"} to find a hostname in any column, {\"_sheet_name\": \"VM\", \"_any\": \"SHDPC0165\"} to search in a specific tab, {\"Category\": \"Laptop\"} for column-specific search.",
                        "additionalProperties": {"type": "string"},
                    }
                },
                "required": ["filters"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_summary",
            "description": "Get a statistical summary of the entire inventory including counts, ranges, and top values per column.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_low_stock_items",
            "description": "Find items where a quantity/stock column value is below a threshold.",
            "parameters": {
                "type": "object",
                "properties": {
                    "quantity_column": {
                        "type": "string",
                        "description": "The column name that holds quantity/stock values.",
                    },
                    "threshold": {
                        "type": "integer",
                        "description": "Items with quantity below this value are considered low stock. Default 10.",
                        "default": 10,
                    },
                },
                "required": ["quantity_column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_duplicate_entries",
            "description": "Find duplicate entries in the inventory based on a specific column.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {
                        "type": "string",
                        "description": "The column name to check for duplicates.",
                    }
                },
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_inventory_record",
            "description": "Update a specific field in an inventory record. Use only after confirming with the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_number": {
                        "type": "integer",
                        "description": "The Excel row number of the record to update.",
                    },
                    "column": {
                        "type": "string",
                        "description": "The column name to update.",
                    },
                    "new_value": {
                        "type": "string",
                        "description": "The new value to set.",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "The worksheet tab name where the record is located.",
                    },
                },
                "required": ["row_number", "column", "new_value", "sheet_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_inventory_record",
            "description": "Add a new record to a specific worksheet tab. Use only after confirming all fields with the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "record": {
                        "type": "object",
                        "description": "Key-value pairs for the new record. Keys must match existing column names.",
                        "additionalProperties": {"type": "string"},
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "The worksheet tab name to add the record to.",
                    },
                },
                "required": ["record", "sheet_name"],
            },
        },
    },
]


class InventoryAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
        )
        self.sessions: Dict[str, List[dict]] = {}
        self.file_data: Dict[str, Tuple[List[str], List[dict]]] = {}

    def _get_data(self, filepath: str) -> Tuple[List[str], List[dict]]:
        """Load and cache inventory data."""
        if filepath not in self.file_data:
            self.file_data[filepath] = load_inventory(filepath)
        return self.file_data[filepath]

    def reload_file(self, filepath: str):
        """Force reload of a file (after updates)."""
        if filepath in self.file_data:
            del self.file_data[filepath]

    def _execute_tool(self, name: str, args: dict, filepath: str) -> str:
        """Execute a tool call and return the result as a string."""
        try:
            headers, data = self._get_data(filepath)

            if name == "search_inventory":
                filters = args.get("filters", args)
                if not isinstance(filters, dict):
                    filters = args
                results = search_records(data, filters)
                return format_records(results)

            elif name == "get_inventory_summary":
                summary = get_summary(headers, data)
                return json.dumps(summary, indent=2, default=str)

            elif name == "find_low_stock_items":
                threshold = args.get("threshold", 10)
                results = find_low_stock(data, args["quantity_column"], threshold)
                return format_records(results)

            elif name == "find_duplicate_entries":
                dupes = find_duplicates(data, args["column"])
                if not dupes:
                    return "No duplicates found."
                result = {}
                for val, rows in dupes.items():
                    result[val] = [
                        {k: v for k, v in r.items() if k != "_row_number"}
                        for r in rows
                    ]
                return json.dumps(result, indent=2, default=str)

            elif name == "update_inventory_record":
                result = update_record(filepath, args["row_number"], args["column"], args["new_value"], args.get("sheet_name"))
                self.reload_file(filepath)
                return json.dumps(result, default=str)

            elif name == "add_inventory_record":
                result = add_record(filepath, args["record"], args.get("sheet_name"))
                self.reload_file(filepath)
                return json.dumps(result, default=str)

            return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def chat(self, session_id: str, user_message: str, filepath: str) -> str:
        """Process a user message and return the assistant's response."""
        headers, data = self._get_data(filepath)

        # Get unique sheet names from data
        sheet_names = sorted(set(r.get("_sheet_name", "Unknown") for r in data))

        # Build system prompt with file context
        system = SYSTEM_PROMPT.format(
            columns=", ".join(h for h in headers if not h.startswith("_")),
            total_records=len(data),
            sheet_names=", ".join(sheet_names),
        )

        # Get or create session history
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        history = self.sessions[session_id]

        # Trim history to last 20 messages to save tokens
        if len(history) > 20:
            history = history[-20:]
            self.sessions[session_id] = history

        messages = [{"role": "system", "content": system}] + history + [
            {"role": "user", "content": user_message}
        ]

        # Call Azure OpenAI
        response = self.client.chat.completions.create(
            model=config.AZURE_OPENAI_DEPLOYMENT,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",

            temperature=0.1,
            max_tokens=4000,
        )

        msg = response.choices[0].message

        # Handle tool calls (may need multiple rounds)
        max_rounds = 5
        rounds = 0
        while msg.tool_calls and rounds < max_rounds:
            rounds += 1
            # Add assistant message with tool calls
            messages.append(msg.model_dump())

            # Execute each tool call
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                result = self._execute_tool(fn_name, fn_args, filepath)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            # Get next response
            response = self.client.chat.completions.create(
                model=config.AZURE_OPENAI_DEPLOYMENT,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
    
                temperature=0.1,
            max_tokens=4000,
            )
            msg = response.choices[0].message

        assistant_reply = msg.content or "I processed your request but have no additional information to share."

        # Save to history
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_reply})
        self.sessions[session_id] = history

        return assistant_reply
