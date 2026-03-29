# 01_llv_code

AI-generated code projects repository. Maintained by OpenClaw

## Projects

| Project | Description |
|---------|-------------|
| **pro1** | Financial management tools — FastAPI backend with static frontend, supports A-stock indices, calculator, charts |
| **pro2** | Paper visualization — generates visualization graphs based on GB/T 13745-2009 Chinese academic classification |
| **pro3** | Linux system monitoring dashboard — real-time CPU/memory monitoring with web UI |
| **pro4** | Whisper voice-to-text batch transcription — batch audio to text using OpenAI Whisper |
| **drafts** | Miscellaneous code snippets and experiments |

## Directory Structure

```
01_llv_code/
├── pro1/              # Financial management system
│   └── financial_management_tools/
│       ├── main.py            # FastAPI entry point
│       ├── static/            # Frontend (HTML/JS/CSS)
│       ├── doc/                # Architecture & dev docs
│       └── tests/              # Unit tests
├── pro2/              # Paper visualization
│   ├── app.py                 # Main application
│   ├── subjects.py            # Subject classification logic
│   └── static/                # Web assets
├── pro3/              # Linux system monitor
│   ├── app.py                 # Monitoring web server
│   ├── test_*.py               # Basic unit tests
│   ├── build.sh               # Build script
│   └── doc/                   # Documentation
├── pro4/              # Whisper batch transcription
│   ├── main.py                 # Entry point
│   ├── transcribe.py           # Transcription logic
│   ├── converter.py            # Audio conversion
│   └── whisper_models/          # Model cache
└── drafts/           # Experimental snippets
```

## Note

This is a monorepo of independently generated projects. Each `proN` folder is a self-contained project. `drafts/` contains standalone snippets without a full project structure.
