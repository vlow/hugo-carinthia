# Library Image Generator Tool

A Python tool that generates SVG cover and banner images for books in a Hugo library feature. Takes an ISBN as input and creates themed SVG images using multimodal LLMs.

## Features

- **Multi-source book lookup**: Retrieves book metadata from Google Books API and Goodreads
- **Multi-source cover lookup**: Downloads cover images from Google Books, Goodreads, or generates AI covers as fallback
- **Dual LLM support**: Supports both OpenAI GPT-4 and Anthropic Claude for SVG generation
- **Two image formats**: Generates both 236x327px cover images and 1024x200px banner images
- **JSON metadata output**: Outputs complete book metadata in JSON format

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up API keys as environment variables:
```bash
export OPENAI_API_KEY="your_openai_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

Note: You need at least one API key. If you only have one, use `--model` to specify which one to use.

## Usage

### Basic Usage
```bash
python main.py 9780143034903
```
This will use GPT-4 by default and generate two SVG files plus JSON metadata.

### Specify Model
```bash
# Use Claude
python main.py 9780143034903 --model claude

# Use both models (generates 4 SVG files total)
python main.py 9780143034903 --model gpt-5 --model claude
```

### Output Files

For ISBN `9780143034903`, the tool generates:
- `9780143034903_cover.svg` - 236x327px cover image for library list view
- `9780143034903_banner.svg` - 1024x200px banner image for book detail page
- If multiple models used: `9780143034903_cover_gpt-5.svg`, `9780143034903_cover_claude.svg`, etc.
- JSON metadata printed to stdout

## Architecture

### Content Lookup Services
- **GoogleBooksService**: Uses Google Books API for book metadata
- **GoodreadsScraperService**: Web scrapes Goodreads for book information
- **ContentLookupService**: Tries sources in order until one succeeds

### Cover Lookup Services  
- **GoogleBooksCoverService**: Downloads covers from Google Books API
- **GoodreadsCoverService**: Downloads covers from Goodreads
- **AICoverGeneratorService**: Generates covers using AI as fallback
- **CoverLookupService**: Tries sources in order until one succeeds

### LLM Services
- **OpenAIService**: Uses GPT-4 with vision for SVG generation and DALL-E for cover generation
- **ClaudeService**: Uses Claude 3.5 Sonnet with vision for SVG generation
- **LLMService**: Factory for creating appropriate service instances

## Customization

### Prompt Templates
Edit files in the `prompts/` directory to customize SVG generation:
- `cover_svg_prompt.txt` - For 236x327px cover images
- `banner_svg_prompt.txt` - For 1024x200px banner images  
- `cover_generation_prompt.txt` - For AI-generated fallback covers

### Adding New Services
Implement the appropriate interfaces:
- `ContentLookupInterface` for new book metadata sources
- `CoverLookupInterface` for new cover image sources
- `LLMInterface` for new AI service providers

## Error Handling

The tool gracefully handles various error conditions:
- Missing or invalid ISBNs
- Network connectivity issues
- API rate limits or errors
- Missing API keys
- Failed image downloads

It tries multiple sources and provides informative error messages when all sources fail.

## Requirements

- Python 3.8+
- API keys for OpenAI and/or Anthropic (at least one required)
- Internet connection for API calls and web scraping