#!/usr/bin/env python3
"""
Generate PandaDoc proposals from sales call transcripts or descriptions.

Usage:
    python execution/generate_pandadoc.py \
        --input "Sales call transcript or description here" \
        [--template-id TEMPLATE_ID] \
        [--interactive] \
        [--save-only]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Default sender information (hardcoded per requirements)
DEFAULT_SENDER = {
    "Sender.Company": "Readymation",
    "Sender.FirstName": "Heinz",
    "Sender.LastName": "Veintimilla",
    "Sender.Email": "heinz@readymation.com"
}


def extract_proposal_data(input_text: str, openrouter_api_key: str) -> Dict[str, Optional[str]]:
    """
    Extract proposal fields from input text using Claude via OpenRouter.

    Args:
        input_text: Sales call transcript or description
        openrouter_api_key: OpenRouter API key

    Returns:
        Dictionary with all proposal fields (23 total)
    """
    print("Extracting proposal data from input text...")

    # Enhanced system prompt for natural, human-like extraction
    system_prompt = """You are an expert business proposal writer who excels at understanding client needs from conversations.

Your task: Extract proposal information from sales call notes and create professional, compelling proposal content.

When writing descriptions:
- Use clear, professional business language
- Write in second person ("you need", "your team") for client-facing content
- Be specific and actionable
- Highlight business value and outcomes
- Keep titles concise (3-7 words)
- Make descriptions substantive (2-4 sentences)

Extract these fields from the conversation:

**Client Information:**
- Client.Company: Company name
- Client.FirstName: Client's first name
- Client.LastName: Client's last name

**Proposal Content:**
- ProposalTitle: Compelling title for the proposal (e.g., "Marketing Automation Solution for Ambition Fitness")
- ProblemTitle: Clear problem statement (e.g., "Manual Data Entry Bottleneck")
- ProblemDescription: 2-3 sentences describing the client's challenge, its impact, and why it matters
- SolutionTitle: Clear solution statement (e.g., "Automated Client Onboarding System")
- SolutionDescription: 2-3 sentences describing the proposed solution, key features, and expected benefits
- ScopeOfWork: Detailed scope covering what will be delivered

**Project Structure:**
- Task1Name through Task4Name: Clear task names (e.g., "Discovery & Requirements Analysis")
- Task1Duration through Task4Duration: Time estimates (e.g., "1 week", "3 days", "2 weeks")
- TotalProjectDuration: Overall timeline

**Commercial Terms:**
- PaymentTerms: Payment structure and terms

Return ONLY a valid JSON object with these exact field names. Use null for fields not mentioned in the input.
Make the content professional, clear, and compelling - as if writing for a real client proposal."""

    user_prompt = f"""Extract and enhance proposal data from this sales call information:

{input_text}

Return a JSON object with all fields. Make descriptions professional and client-ready."""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            },
            timeout=30
        )
        response.raise_for_status()

        # Extract JSON from OpenRouter response
        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Try to parse JSON from response
        # Claude might wrap it in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        extracted_data = json.loads(content)

        # Flatten nested structure if present (e.g., {"Client": {"Company": "X"}} -> {"Client.Company": "X"})
        flattened = {}
        for key, value in extracted_data.items():
            if isinstance(value, dict):
                # Flatten nested dict
                for nested_key, nested_value in value.items():
                    flattened[f"{key}.{nested_key}"] = nested_value
            else:
                flattened[key] = value

        # Add default sender information
        flattened.update(DEFAULT_SENDER)

        print(f"Successfully extracted {len([v for v in flattened.values() if v])} fields")
        return flattened

    except Exception as e:
        print(f"Error during extraction: {e}")
        # Return minimal structure on error
        return {
            "Client.Company": None,
            "Client.FirstName": None,
            "Client.LastName": None,
            "ProposalTitle": None,
            "ProblemTitle": None,
            "ProblemDescription": None,
            "SolutionTitle": None,
            "SolutionDescription": None,
            "ScopeOfWork": None,
            "PaymentTerms": None,
            "Task1Name": None,
            "Task1Duration": None,
            "Task2Name": None,
            "Task2Duration": None,
            "Task3Name": None,
            "Task3Duration": None,
            "Task4Name": None,
            "Task4Duration": None,
            "TotalProjectDuration": None,
            **DEFAULT_SENDER
        }


def validate_required_fields(data: Dict[str, Optional[str]]) -> List[str]:
    """
    Check which required fields are missing or None.

    Args:
        data: Extracted proposal data

    Returns:
        List of missing field names
    """
    # Define required fields (excluding sender fields which are hardcoded)
    required = [
        "Client.Company",
        "Client.FirstName",
        "Client.LastName",
        "ProposalTitle"
    ]

    missing = []
    for field in required:
        if not data.get(field):
            missing.append(field)

    return missing


def prompt_for_missing_fields(data: Dict[str, Optional[str]], missing: List[str]) -> Dict[str, Optional[str]]:
    """
    Interactively prompt user to fill in missing required fields.

    Args:
        data: Extracted proposal data
        missing: List of missing field names

    Returns:
        Updated data dictionary
    """
    print("\n" + "="*60)
    print("Missing Required Fields")
    print("="*60)
    print("The following fields could not be extracted and are required:")
    print()

    for field in missing:
        value = input(f"{field}: ").strip()
        if value:
            data[field] = value

    print()
    return data


def save_extracted_data(data: Dict[str, Optional[str]], output_dir: str = ".tmp") -> str:
    """
    Save extracted data to JSON file.

    Args:
        data: Extracted proposal data
        output_dir: Directory to save to

    Returns:
        Path to saved file
    """
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(output_dir) / f'extracted_proposal_data_{timestamp}.json'

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved extracted data to: {output_path}")
    return str(output_path)


def create_pandadoc_document(
    template_id: str,
    field_data: Dict[str, Optional[str]],
    api_key: str
) -> str:
    """
    Create PandaDoc document from template using API.

    Args:
        template_id: PandaDoc template UUID
        field_data: Proposal field data
        api_key: PandaDoc API key

    Returns:
        Document URL
    """
    print("Creating PandaDoc document...")

    # Build tokens array for template fields
    tokens = []
    for field_name, field_value in field_data.items():
        if field_value:  # Only include non-None values
            tokens.append({
                "name": field_name,
                "value": str(field_value)
            })

    # Prepare API request
    url = "https://api.pandadoc.com/public/v1/documents"
    headers = {
        "Authorization": f"API-Key {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "template_uuid": template_id,
        "name": field_data.get("ProposalTitle", "Proposal"),
        "tokens": tokens
    }

    # Optional: Add recipient if client email is available
    if field_data.get("Client.Email"):
        payload["recipients"] = [{
            "email": field_data["Client.Email"],
            "first_name": field_data.get("Client.FirstName", ""),
            "last_name": field_data.get("Client.LastName", ""),
            "role": "Client"
        }]

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        document_id = result.get("id")
        document_url = f"https://app.pandadoc.com/a/#/documents/{document_id}"

        print(f"Document created successfully!")
        print(f"Document ID: {document_id}")
        return document_url

    except requests.exceptions.RequestException as e:
        print(f"Error creating PandaDoc document: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def main():
    """Main execution flow."""
    parser = argparse.ArgumentParser(
        description='Generate PandaDoc proposals from text input'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Sales call transcript or description'
    )
    parser.add_argument(
        '--template-id',
        help='PandaDoc template ID (or set PANDADOC_TEMPLATE_ID env var)'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Prompt for missing required fields'
    )
    parser.add_argument(
        '--save-only',
        action='store_true',
        help='Only extract and save data, do not create PandaDoc document'
    )

    args = parser.parse_args()

    # Get API keys from environment
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    pandadoc_key = os.getenv('PANDADOC_API_KEY')
    template_id = args.template_id or os.getenv('PANDADOC_TEMPLATE_ID')

    if not openrouter_key:
        print("Error: OPENROUTER_API_KEY not found in environment")
        print("Get your key from: https://openrouter.ai/keys")
        return 1

    if not args.save_only:
        if not pandadoc_key:
            print("Error: PANDADOC_API_KEY not found in environment")
            return 1
        if not template_id:
            print("Error: --template-id required or set PANDADOC_TEMPLATE_ID env var")
            return 1

    try:
        # Step 1: Extract data from input
        extracted_data = extract_proposal_data(args.input, openrouter_key)

        # Step 2: Save intermediate data
        json_path = save_extracted_data(extracted_data)

        # Step 3: Validate required fields
        missing_fields = validate_required_fields(extracted_data)

        if missing_fields:
            if args.interactive:
                # Prompt user for missing fields
                extracted_data = prompt_for_missing_fields(extracted_data, missing_fields)
                # Re-save with complete data
                json_path = save_extracted_data(extracted_data)
            else:
                print(f"\nWarning: Missing {len(missing_fields)} required field(s):")
                for field in missing_fields:
                    print(f"  - {field}")
                print("\nUse --interactive flag to fill in missing fields")

        # Step 4: Create PandaDoc document (unless save-only mode)
        if args.save_only:
            print(f"\nExtraction complete. Data saved to: {json_path}")
            print("Skipping PandaDoc document creation (--save-only mode)")
            return 0

        document_url = create_pandadoc_document(
            template_id,
            extracted_data,
            pandadoc_key
        )

        print("\n" + "="*60)
        print("Success!")
        print("="*60)
        print(f"Proposal URL: {document_url}")
        print(f"Extracted data: {json_path}")
        print()

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
