# Generate PandaDoc Proposal Directive

## Goal
Generate PandaDoc proposals from sales call transcripts or direct descriptions by extracting proposal data using AI and populating a PandaDoc template via API.

## Inputs
- `input_text` (string, required): Sales call transcript or typed description of the proposal
- `template_id` (string, optional): PandaDoc template UUID (defaults to PANDADOC_TEMPLATE_ID env var)
- `interactive` (boolean, optional): Whether to prompt for missing required fields (default: false)
- `save_only` (boolean, optional): Only extract/save data without creating document (default: false)

## Tools/Scripts
- **Primary**: `execution/generate_pandadoc.py`

## Process
1. Parse input text using Claude API to extract structured proposal data
2. Save extracted data to `.tmp/extracted_proposal_data_<timestamp>.json`
3. Validate required fields (Client.Company, Client.FirstName, Client.LastName, ProposalTitle)
4. If fields missing and `--interactive` flag set: prompt user for missing data
5. Call PandaDoc API to create document from template with extracted fields
6. Return PandaDoc document URL

## Execution Example

### Basic usage:
```bash
python execution/generate_pandadoc.py \
  --input "Sales call with Guil Netto from Ambition Fitness..."
```

### With interactive mode (prompts for missing fields):
```bash
python execution/generate_pandadoc.py \
  --input "$(cat transcript.txt)" \
  --interactive
```

### Test extraction without creating document:
```bash
python execution/generate_pandadoc.py \
  --input "Sales call details..." \
  --save-only
```

### With custom template:
```bash
python execution/generate_pandadoc.py \
  --input "Proposal details..." \
  --template-id "uEMWZwggbGq9EzWyHr4kH4"
```

## Outputs
- **Intermediate**: `.tmp/extracted_proposal_data_<timestamp>.json` - Extracted field data
- **Deliverable**: PandaDoc proposal URL (https://app.pandadoc.com/a/#/documents/...)

## Extracted Fields (23 total)

### Client Information
- `Client.Company`: Company name
- `Client.FirstName`: Client's first name
- `Client.LastName`: Client's last name

### Proposal Details
- `ProposalTitle`: Title for the proposal
- `ProblemTitle`: Brief problem/challenge title
- `ProblemDescription`: Detailed problem description
- `SolutionTitle`: Brief solution title
- `SolutionDescription`: Detailed solution description
- `ScopeOfWork`: Scope of work details
- `PaymentTerms`: Payment terms and conditions

### Tasks (up to 4)
- `Task1Name` through `Task4Name`: Task names
- `Task1Duration` through `Task4Duration`: Task durations (e.g., "1 week", "3 days")
- `TotalProjectDuration`: Total project timeline

### Sender Information (Auto-filled)
- `Sender.Company`: Readymation (hardcoded)
- `Sender.FirstName`: Heinz (hardcoded)
- `Sender.LastName`: Veintimilla (hardcoded)
- `Sender.Email`: heinz@readymation.com (hardcoded)

## Edge Cases & Learnings

### Incomplete Input Text
- **Issue**: Sales call transcript missing key details (client name, project scope, etc.)
- **Solution**: Use `--interactive` flag to prompt for missing required fields
- **Required fields**: Client.Company, Client.FirstName, Client.LastName, ProposalTitle

### Ambiguous Task Information
- **Issue**: Input mentions tasks but doesn't clearly separate them or provide durations
- **Example**: "We'll do discovery, build it, test, and train them"
- **Solution**: AI will attempt to parse into Task1-4, but may need manual review
- **Tip**: Provide structured task info: "Task 1: Discovery (1 week), Task 2: Build (2 weeks)"

### Template Field Mismatch
- **Issue**: PandaDoc template expects different field names than extracted
- **Check**: Verify template uses exact field names (e.g., "Client.Company" not "ClientCompany")
- **Solution**: Update template field names to match the 23 fields listed above

### API Rate Limits
- **PandaDoc**: 300 requests per minute
- **Anthropic**: Depends on plan tier
- **Solution**: Script handles errors gracefully, retry after brief delay if needed

### Missing Optional Fields
- **Behavior**: Optional fields (tasks, payment terms) can be None/null
- **PandaDoc**: Will show empty or default values in generated document
- **Recommendation**: Review generated proposal and fill in manually if needed

## Error Handling

### Missing API Keys
- **Error**: "ANTHROPIC_API_KEY not found in environment"
- **Fix**: Add to `.env` file or export as environment variable
- **Same for**: PANDADOC_API_KEY, PANDADOC_TEMPLATE_ID

### Invalid Template ID
- **Error**: PandaDoc API returns 404 or "Template not found"
- **Fix**: Verify template ID in PandaDoc dashboard
- **Check**: Template must be active and accessible with API key

### Malformed Input Text
- **Error**: Claude extraction returns empty/null fields
- **Fix**: Provide more detailed input with clear client info and project details
- **Tip**: Use `--save-only` to test extraction without creating document

### PandaDoc API Errors
- **401 Unauthorized**: Invalid API key
- **403 Forbidden**: API key lacks permissions
- **429 Too Many Requests**: Rate limit exceeded, wait and retry
- **500 Server Error**: PandaDoc service issue, retry after delay

## Testing

### Test extraction only:
```bash
python execution/generate_pandadoc.py \
  --input "Test with Guil Netto from Ambition Fitness. Need automation for client onboarding. Will take 4 weeks total." \
  --save-only
```

Check `.tmp/extracted_proposal_data_*.json` to verify extracted fields.

### Test with sample data:
```bash
python execution/generate_pandadoc.py \
  --input "Had a great call with Guil Netto from Ambition Fitness. They need help automating their client onboarding process. Main problem: manual data entry taking 10 hours/week. Solution: Build custom automation with Zapier integration. Tasks: 1) Discovery & design (1 week), 2) Build automation (2 weeks), 3) Testing (1 week), 4) Training (3 days). Payment: 50% upfront, 50% on completion." \
  --interactive
```

Should extract all fields and create a complete proposal.

## Environment Setup

Required in `.env`:
```bash
OPENROUTER_API_KEY=your_openrouter_key_here
PANDADOC_API_KEY=your_pandadoc_api_key_here
PANDADOC_TEMPLATE_ID=your_template_id_here
```

Get credentials:
- **OpenRouter API**: https://openrouter.ai/keys (uses Claude Sonnet 4 for best-in-class extraction)
- **PandaDoc API**: https://app.pandadoc.com/a/#/settings/integrations/api

## Tips for Better Extraction

1. **Be specific about client info**: Include full name and company clearly
2. **Structure tasks clearly**: Number them or use bullet points
3. **Include durations**: Specify task lengths (days, weeks, months)
4. **State payment terms explicitly**: Mention percentages, milestones, timing
5. **Describe problem and solution**: Separate the challenge from the fix

### Good Input Example:
```
Client: Guil Netto from Ambition Fitness

Problem: They're spending 10 hours per week on manual client onboarding data entry, leading to errors and delays.

Solution: Custom Zapier automation to connect their CRM, email, and scheduling systems for automatic data flow.

Scope:
- Task 1: Discovery & requirements (1 week)
- Task 2: Build automation workflows (2 weeks)
- Task 3: Testing & QA (1 week)
- Task 4: Training & handoff (3 days)
Total: 5 weeks

Payment: 50% upfront, 50% upon completion
```

## Last Updated
2026-01-07 - Initial creation
