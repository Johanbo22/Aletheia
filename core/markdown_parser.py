import re
from enum import Enum
import logging

class ParseMode(Enum):
    """Defines the operational mode for the changelog parser."""
    Fixes = "fixes"
    History = "history"

class ChangelogSection(Enum):
    """Defines the relevant sections to extract from a changelog."""
    Fixed = "Fixed"
    Changed = "Changed"

def parse_changelog(text: str, mode: ParseMode, application_version: str) -> str:
    """Parses a raw markdown text into HTML based on the requested ParseMode."""
    html_output: str = "<style>h2 {color: #2c3e50;} h3 {color: #2980b9;} ul {line-height: 1.6;}</style>"
    
    if not text.strip():
        return "<p>No changelog data provided.</p>"
    
    try:
        sections: list[str] = [sec for sec in re.split(r'(?:^|\n)## ', text) if sec.strip()]
        
        if not sections:
            return "<p>No changelog data found.</p>"
        
        valid_versions: list[str] = [sec for sec in sections if not sec.startswith("#")]
        
        if not valid_versions:
            return "<p>No version information found.</p>"
        
        latest_section: str = valid_versions[0]
        past_sections: list[str] = valid_versions[1:]
        
        if mode == ParseMode.Fixes:
            html_output += _parse_latest_fixes(latest_section, application_version)
        elif mode == ParseMode.History:
            html_output += _parse_version_history(past_sections)
        
        return html_output
    except Exception as error:
        logging.error(f"Failed to parse changelog: {error}", exc_info=True)
        return "<p>Error parsing changelog data.</p>"

def _parse_latest_fixes(latest_section: str, application_version: str) -> str:
    """Extracts only the 'Fixed' and 'Changed' subsections from the latest version."""
    html_output: str = f"<h2>Latest Changes and Fixes - v{application_version}</h2>"
    sub_sections: list[str] = re.split(r'(?:^|\n)### ', latest_section)
    found_relevant: bool = False
    
    target_headers: list[str] = [section.value for section in ChangelogSection]
    
    for sub in sub_sections:
        header_match = re.match(r'^([A-Za-z ]+)\s*(?:\n|$)', sub)
        if header_match:
            header: str = header_match.group(1).strip()
            if header in target_headers:
                found_relevant = True
                body_start_index: int = len(header_match.group(0))
                body: str = sub[body_start_index:].strip()
                
                html_output += f"<h3>{header}</h3>"
                html_output += _markdown_list_to_html(body)
    
    if not found_relevant:
        html_output += "<p>No bug fixes or changes listed for the latest version.</p>"
    
    return html_output

def _parse_version_history(past_sections: list[str]) -> str:
    """Extracts the full version history for older releases."""
    html_output: str = "<h2>Version History</h2>"
    
    if not past_sections:
        return html_output + "<p>No past versions found.</p>"
    
    for version_text in past_sections:
        lines: list[str] = version_text.split("\n")
        if not lines:
            continue
        
        version_title: str = lines[0].strip()
        html_output += f"<hr><h3>{version_title}</h3>"
        
        body: str = "\n".join(lines[1:])
        html_output += _markdown_list_to_html(body)
    
    return html_output

def _markdown_list_to_html(text: str) -> str:
    """Helper function to convert markdown bullet list to HTML li element"""
    lines: list[str] = text.split("\n")
    html: str = ""
    in_list: bool = False
    
    for line in lines:
        stripped: str = line.strip()
        is_list_item: bool = stripped.startswith("- ") or stripped.startswith("* ")
        
        if not is_list_item and in_list:
            html += "</ul>"
            in_list = False
        
        if is_list_item:
            if not in_list:
                html += "<ul>"
                in_list = True
            
            content: str = stripped[2:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            html += f"<li>{content}</li>"
            
        elif stripped.startswith("### "):
            header_text: str = stripped[4:].strip()
            html += f"<h4>{header_text}</h4>"
        elif not stripped:
            continue
        else:
            html += f"<p>{stripped}</p>"
    if in_list:
        html += "</ul>"
    
    return html