# FTL Translator

FTL Translator is a tool for translating Fluent files (.ftl) to other languages using Google Translate.

## Installation

Install the package using pip:

```bash
pip install ftl-translator
```

## Usage

### Translate a file

To translate a file, use the `translate` function:

```python
from ftl_translator import translate, Locale

opts = TranslateOpts(
    locales_dir="path/to/locales",
    origin_locale=Locale.RUSSIAN,
    target_locales=[Locale.ENGLISH, Locale.GERMAN],
)

async def main():
    await translate(opts)

if __name__ == "__main__":
    asyncio.run(main())
```

