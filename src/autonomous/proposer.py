"""
ProposalGeneratorAgent - Converts findings into actionable code change proposals.
"""

import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import difflib

from openai import OpenAI

from .models.findings import Finding
from .models.proposals import Proposal, Alternative


class ProposalGeneratorAgent:
    """
    Generates detailed code change proposals from findings.

    Uses AI (Grok) to:
    - Convert findings into concrete implementation proposals
    - Generate before/after code snippets
    - Estimate risk and effort
    - Provide multiple alternative approaches
    """

    def __init__(self, api_key: str, base_url: str = "https://api.x.ai/v1", model: str = "grok-4-fast-reasoning"):
        """
        Initialize the proposal generator.

        Args:
            api_key: xAI API key
            base_url: API base URL
            model: Model to use (default: grok-4-fast-reasoning)
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def generate_proposal(self, finding: Finding, file_content: Optional[str] = None) -> Proposal:
        """
        Generate a code change proposal from a finding.

        Args:
            finding: The finding to address
            file_content: Full file content for context (optional)

        Returns:
            Proposal with code changes
        """
        # Read file content if not provided
        if file_content is None:
            try:
                file_content = finding.file_path.read_text(encoding='utf-8')
            except Exception as e:
                raise ValueError(f"Could not read file {finding.file_path}: {e}")

        # Build prompt for AI
        prompt = self._build_prompt(finding, file_content)

        # Call AI to generate proposal
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert Python code reviewer and refactoring assistant. "
                        "Generate detailed, actionable code change proposals that fix issues "
                        "while following best practices. Be specific, provide complete code snippets, "
                        "and explain your reasoning."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent output
        )

        # Parse response
        ai_response = response.choices[0].message.content or ""
        proposal_data = self._parse_ai_response(ai_response, finding, file_content)

        return proposal_data

    async def generate_alternatives(self, proposal: Proposal, count: int = 2) -> List[Alternative]:
        """
        Generate alternative approaches to a proposal.

        Args:
            proposal: The original proposal
            count: Number of alternatives to generate

        Returns:
            List of alternative approaches
        """
        prompt = f"""
Given this code change proposal, suggest {count} alternative approaches:

**Original Proposal:**
Title: {proposal.title}
Description: {proposal.description}

**Original Code:**
```python
{proposal.old_code}
```

**Proposed Code:**
```python
{proposal.new_code}
```

For each alternative:
1. Provide a title
2. Explain the approach
3. Show the code
4. List 2-3 pros
5. List 2-3 cons

Format each alternative clearly.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert Python developer providing alternative solutions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )

        # Parse alternatives (simplified - would need better parsing)
        alternatives = []
        # TODO: Implement proper parsing of alternatives
        # For now, return placeholder
        return alternatives

    def _build_prompt(self, finding: Finding, file_content: str) -> str:
        """Build the prompt for AI to generate proposal."""
        lines = file_content.splitlines()

        # Get context around the issue (10 lines before and after)
        start_line = max(0, finding.line_number - 10)
        end_line = min(len(lines), finding.line_number + 10)
        context = '\n'.join(lines[start_line:end_line])

        prompt = f"""
Analyze this code issue and generate a detailed fix proposal.

**Finding:**
- ID: {finding.finding_id}
- Severity: {finding.severity}
- Category: {finding.category}
- File: {finding.file_path.name}
- Line: {finding.line_number}

**Issue:**
{finding.description}

**Recommendation:**
{finding.recommendation}

**Code Context (lines {start_line + 1}-{end_line}):**
```python
{context}
```

**Generate a proposal with:**

1. **Title**: Brief, action-oriented title (e.g., "Add timeout handling to API calls")

2. **Description**: 2-3 sentences explaining the fix

3. **Old Code**: The exact code that needs to be changed (copy from context)

4. **New Code**: The fixed code with improvements

5. **Risk Level**: Assess as "low", "medium", "high", or "critical"
   - low: Safe changes (formatting, comments, simple additions)
   - medium: Logic changes with good test coverage
   - high: Breaking changes or complex refactors
   - critical: Major architectural changes

6. **Estimated Effort**: Time estimate (e.g., "5 minutes", "1 hour")

7. **Breaking Change**: true/false - Does this break existing API?

8. **Rationale**: Why this fix is necessary (2-3 sentences)

9. **Benefits**: List 2-4 benefits of this change

10. **Risks**: List 1-3 potential risks or gotchas

11. **Test Strategy**: How to test this change

Format your response as:

---PROPOSAL---
TITLE: [title]
DESCRIPTION: [description]
RISK_LEVEL: [low|medium|high|critical]
EFFORT: [estimate]
BREAKING: [true|false]

OLD_CODE:
```python
[old code]
```

NEW_CODE:
```python
[new code]
```

RATIONALE:
[rationale]

BENEFITS:
- [benefit 1]
- [benefit 2]
...

RISKS:
- [risk 1]
- [risk 2]
...

TEST_STRATEGY:
[test strategy]
---END---
"""
        return prompt

    def _parse_ai_response(self, ai_response: str, finding: Finding, file_content: str) -> Proposal:
        """Parse AI response into a Proposal object."""
        # Extract sections from response
        sections = {}
        current_section = None
        content = []

        lines = ai_response.split('\n')
        for line in lines:
            line = line.strip()

            # Check for section markers
            if line.startswith('TITLE:'):
                current_section = 'title'
                sections['title'] = line.replace('TITLE:', '').strip()
            elif line.startswith('DESCRIPTION:'):
                current_section = 'description'
                sections['description'] = line.replace('DESCRIPTION:', '').strip()
            elif line.startswith('RISK_LEVEL:'):
                sections['risk_level'] = line.replace('RISK_LEVEL:', '').strip()
            elif line.startswith('EFFORT:'):
                sections['effort'] = line.replace('EFFORT:', '').strip()
            elif line.startswith('BREAKING:'):
                sections['breaking'] = line.replace('BREAKING:', '').strip().lower() == 'true'
            elif line.startswith('OLD_CODE:'):
                current_section = 'old_code'
                content = []
            elif line.startswith('NEW_CODE:'):
                if current_section == 'old_code':
                    sections['old_code'] = '\n'.join(content).strip()
                current_section = 'new_code'
                content = []
            elif line.startswith('RATIONALE:'):
                if current_section == 'new_code':
                    sections['new_code'] = '\n'.join(content).strip()
                current_section = 'rationale'
                content = []
            elif line.startswith('BENEFITS:'):
                if current_section == 'rationale':
                    sections['rationale'] = '\n'.join(content).strip()
                current_section = 'benefits'
                content = []
            elif line.startswith('RISKS:'):
                if current_section == 'benefits':
                    sections['benefits'] = [l.strip('- ') for l in content if l.strip()]
                current_section = 'risks'
                content = []
            elif line.startswith('TEST_STRATEGY:'):
                if current_section == 'risks':
                    sections['risks'] = [l.strip('- ') for l in content if l.strip()]
                current_section = 'test_strategy'
                content = []
            elif line == '---END---':
                if current_section == 'test_strategy':
                    sections['test_strategy'] = '\n'.join(content).strip()
                break
            elif current_section and line and not line.startswith('```'):
                content.append(line)

        # Clean up code blocks (remove ```python markers)
        old_code = sections.get('old_code', finding.code_snippet).replace('```python', '').replace('```', '').strip()
        new_code = sections.get('new_code', old_code).replace('```python', '').replace('```', '').strip()

        # Generate diff
        diff = self._generate_diff(old_code, new_code)

        # Create proposal
        proposal = Proposal(
            proposal_id=self._generate_id(),
            finding_id=finding.finding_id,
            title=sections.get('title', f"Fix {finding.category} issue in {finding.file_path.name}"),
            description=sections.get('description', finding.description),
            file_path=finding.file_path,
            old_code=old_code,
            new_code=new_code,
            diff=diff,
            risk_level=self._normalize_risk_level(sections.get('risk_level', 'medium')),
            estimated_effort=sections.get('effort', 'Unknown'),
            breaking_change=sections.get('breaking', False),
            rationale=sections.get('rationale', finding.recommendation),
            benefits=sections.get('benefits', []),
            risks=sections.get('risks', []),
            test_strategy=sections.get('test_strategy', 'Run existing test suite'),
        )

        return proposal

    def _generate_diff(self, old_code: str, new_code: str) -> str:
        """Generate unified diff between old and new code."""
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='old',
            tofile='new',
            lineterm=''
        )

        return ''.join(diff)

    def _normalize_risk_level(self, risk_str: str) -> str:
        """Normalize risk level string."""
        risk_str = risk_str.lower().strip()
        if risk_str in ['low', 'medium', 'high', 'critical']:
            return risk_str
        return 'medium'

    def _generate_id(self) -> str:
        """Generate unique proposal ID."""
        return f"proposal_{uuid.uuid4().hex[:12]}"
