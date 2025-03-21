# FTL Translator

FTL Translator is a Python tool designed to facilitate the translation of Fluent files (.ftl) to various languages using both Google Translate and OpenAI's GPT models. This tool is particularly useful for developers and localization teams who need to manage translations efficiently.

## Table of Contents

- [FTL Translator](#ftl-translator)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Translate a file using Google Translate](#translate-a-file-using-google-translate)
    - [Translate a file using OpenAI's GPT](#translate-a-file-using-openais-gpt)
  - [Configuration Options](#configuration-options)
    - [GoogleTranslateOpts](#googletranslateopts)
    - [AiTranslateOpts](#aitranslateopts)
  - [Examples](#examples)
  - [Contributing](#contributing)
  - [License](#license)

## Installation

To install the package, you can use [Poetry](https://python-poetry.org/) (recommended) or install it directly with `pip`. Here’s how to do it with Poetry:

```bash
poetry add git+https://github.com/taimast/ftl-translator.git
```


## Usage

The main functionality of the FTL Translator is provided by the `translate` function, which can be imported from the respective translator module (Google or OpenAI).

### Translate a file using Google Translate

To use Google Translate for file translation, you will need to set up your options with `GoogleTranslateOpts` as shown below:

```python
from ftl_translator.google.translate import GoogleTranslateOpts, translate
from ftl_translator.options import Locale
import asyncio
from pathlib import Path

async def main():
    opts = GoogleTranslateOpts(
        locales_dir=Path("path/to/locales"),
        origin_locale=Locale.RUSSIAN,
        target_locales=[Locale.ENGLISH, Locale.CHINESE],
    )
    await translate(opts)

if __name__ == "__main__":
    asyncio.run(main())
```

### Translate a file using OpenAI's GPT

If you prefer using OpenAI's GPT for translations, you can use the `AiTranslateOpts` like below. Make sure to set your OpenAI API key in an environment variable.

```python
from ftl_translator.ai.translate import AiTranslateOpts, translate
from ftl_translator.options import Locale
import os
import asyncio
from pathlib import Path

async def main():
    opts = AiTranslateOpts(
        api_key=os.environ["OPENAI_API_KEY"],
        locales_dir=Path("path/to/locales"),
        origin_locale=Locale.RUSSIAN,
        target_locales=[Locale.ENGLISH, Locale.CHINESE],
    )
    await translate(opts)

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Options

The following options are available for configuration depending on the translator you choose:

### GoogleTranslateOpts

- `locales_dir`: Path to the directory containing the .ftl files.
- `origin_locale`: Source language (default is `Locale.RUSSIAN`).
- `target_locales`: List of target languages to translate into.
- `translate_batch_size`: Number of messages to translate in a single batch (default is 5).
- `translate_limit`: Maximum number of concurrent translations (default is 4).
- `translate_retry_wait_time`: Time to wait before retrying after a failed request (default is 5 seconds).
- `translate_retry_count`: Number of retry attempts for translation requests (default is 3).

### AiTranslateOpts

- `api_key`: Your OpenAI API key.
- `model`: The model to use (default is `gpt-4o-mini`).
- `system_prompt`: System prompt for the translation model (default is defined in the code).
- `source`: Source language code (default is `ru` for Russian).
- `target`: Target language code (default is `en` for English).
- `check_interval`: Time interval to check for batch job completion (default is 10 seconds).
- `proxy`: Optional proxy for the requests.

## Examples

1. **Translating from Russian to English and Chinese using Google Translate**:
   Create a file named `google.py` and paste the following:

   ```python
   import asyncio
   from ftl_translator.google.translate import GoogleTranslateOpts, translate
   from ftl_translator.options import Locale
   from pathlib import Path
   import logging

   logging.basicConfig(level=logging.DEBUG)

   async def main():
       opts = GoogleTranslateOpts(
           locales_dir=Path("locales"),
           origin_locale=Locale.RUSSIAN,
           target_locales=[Locale.ENGLISH, Locale.CHINESE],
       )
       await translate(opts)

   if __name__ == "__main__":
       asyncio.run(main())
   ```

2. **Translating from Russian to English and Chinese using OpenAI's GPT**:
   Create a file named `gpt.py` and use the following code:

   ```python
   import asyncio
   import os
   from ftl_translator.ai.translate import AiTranslateOpts, translate
   from ftl_translator.options import Locale
   from pathlib import Path
   import logging

   logging.basicConfig(level=logging.DEBUG)

   async def main():
       opts = AiTranslateOpts(
           api_key=os.environ["OPENAI_API_KEY"],
           locales_dir=Path("locales"),
           origin_locale=Locale.RUSSIAN,
           target_locales=[Locale.ENGLISH, Locale.CHINESE],
       )
       await translate(opts)

   if __name__ == "__main__":
       asyncio.run(main())
   ```

## Contributing

Contributions are welcome! If you’d like to contribute to the FTL Translator project, please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
