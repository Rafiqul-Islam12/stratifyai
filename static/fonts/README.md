# Inter (optional, self-hosted)

The UI works with the system font stack. To use Inter, put these files here:

- `Inter-Regular.woff2`
- `Inter-Medium.woff2`
- `Inter-SemiBold.woff2`
- `Inter-Bold.woff2`

Source: the official Inter release (https://rsms.me/inter/), SIL Open Font License 1.1.
Then in `.streamlit/config.toml` set `font = "Inter"` and uncomment the `[[theme.fontFaces]]` blocks
(add a block for weight 700). `app/styles.css` already lists Inter first in `--font-sans`.
