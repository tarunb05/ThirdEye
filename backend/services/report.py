from jinja2 import Template

def generate_report_json(analysis: dict) -> dict:
    '''Generate JSON report'''
    return analysis

def generate_report_markdown(analysis: dict) -> str:
    '''Generate Markdown report'''
    md = f\"\"\"# ThirdEye Analysis Report

## Summary
{analysis.get('summary', 'N/A')}

## Vulnerabilities
{'No vulnerabilities found.' if not analysis.get('vulnerabilities') else 'See details above.'}

## Verdict
{analysis.get('final_verdict', 'UNKNOWN')}
\"\"\"
    return md

def generate_report_pdf(analysis: dict) -> bytes:
    '''Generate PDF report using Weasyprint'''
    # TODO: Implement Jinja2 template + Weasyprint
    return b''
