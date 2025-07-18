# SEC EDGAR MCP Enhanced - Team Usage Guide

## Overview

This is our enhanced fork of the SEC EDGAR MCP server with significant new capabilities for cross-company insider analysis, institutional holdings tracking, and comprehensive financial data extraction.

## Installation for Team Members

### Using with Claude Desktop

1. Update your Claude Desktop MCP configuration file:

```json
{
  "sec-edgar-mcp-enhanced": {
    "command": "npx",
    "args": [
      "mcp-install",
      "https://github.com/houseworthe/sec-edgar-mcp",
      "--branch", "main",
      "--name", "SEC EDGAR Enhanced"
    ],
    "env": {
      "SEC_EDGAR_USER_AGENT": "Your Name (your.email@company.com)"
    }
  }
}
```

### Using with Cline or other MCP clients

```bash
# Clone the enhanced fork
git clone https://github.com/houseworthe/sec-edgar-mcp
cd sec-edgar-mcp

# Install dependencies
pip install -e .

# Set your user agent
export SEC_EDGAR_USER_AGENT="Your Name (your.email@company.com)"
```

## New Features in Our Fork

### 1. Cross-Company Insider Search
- **Tool**: `get_all_insider_companies`
- **Purpose**: Find ALL companies where a person serves or served as an insider
- **Example**: Find all board positions for "Warren Buffett" across all public companies

### 2. Advanced Insider Trading Analysis
- **Tool**: `get_insider_transactions`
- **Purpose**: Detailed Form 4 transaction analysis with pattern detection
- **Tool**: `analyze_insider_patterns`
- **Purpose**: Buy/sell ratios, seasonal trends, top insider identification

### 3. Institutional Holdings
- **Tool**: `get_13f_holdings`
- **Purpose**: Parse 13F-HR filings for institutional positions
- **Tool**: `get_ownership_changes`
- **Purpose**: Track quarter-over-quarter changes

### 4. Comprehensive Reports
- **Tool**: `generate_comprehensive_insider_report`
- **Purpose**: Multi-source analysis combining Form 4s, proxy statements, and more
- **Example**: Complete career history and activity analysis for any insider

### 5. Natural Language Interface
- **Tool**: `answer_ownership_question`
- **Example**: "How many shares of Apple does Tim Cook own?"
- **Tool**: `answer_sales_question`
- **Example**: "How much revenue did Tesla generate from China in 2023?"

## Example Queries

### Finding Cross-Company Connections
```
"Find all companies where Gale Klappa serves as a board member"
"Show me Warren Buffett's insider activity across all companies"
```

### Analyzing Insider Trading
```
"Show me all insider sales at Microsoft in the last 90 days"
"Analyze insider trading patterns at Tesla over the past year"
```

### Institutional Analysis
```
"Which institutions increased their Apple holdings last quarter?"
"Show me Berkshire Hathaway's 13F holdings"
```

### Comprehensive Reports
```
"Generate a complete profile for Elon Musk's insider activity"
"Compare insider activity between Apple and Microsoft executives"
```

## Rate Limiting

The enhanced tools respect SEC rate limits:
- 10 requests per second maximum
- Automatic retry with exponential backoff
- Concurrent request management for bulk operations

## Support

For issues specific to our enhancements:
- Create an issue at: https://github.com/houseworthe/sec-edgar-mcp/issues
- Tag with `enhancement` for new feature requests
- Tag with `bug` for issues with existing enhanced features

## Contributing

We plan to contribute these enhancements back to the upstream project. If you make improvements:
1. Create a feature branch
2. Test thoroughly
3. Submit a PR to our fork first
4. We'll coordinate upstream contributions

## Credits

- Original SEC EDGAR MCP by Stefano Amorelli
- Enhanced features developed by our team
- Built on the secedgar Python SDK