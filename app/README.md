# PTTI webapp

This folder contains the code for running the PTTI webapp.
  
## Installation

In addition to the PTTI installation instructions, you will also
need to install [Streamlit]:

```sh
pip install streamlit
```

## Basic usage

Streamlit apps run through the web browser. To launch, simply run

```sh
streamlit run ptti_app.py
```

and a new browser window with the app should launch.

[Streamlit]: https://www.streamlit.io/

## Troubleshooting

- On Ubuntu, `streamlit` may fail with `Illegal instruction (core dumped)`. This can happen if the `pyarrow` module was not compiled correctly. A possible fix is `pip uninstall pyarrow` followed by `conda install pyarrow`
