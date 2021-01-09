# Bitcoin Pricing Analysis.

This repo is a non financial person's attempt at modelling bitcoin prices over time using time series ML techniques.

## Data

Bitcoin data from the Bitstamp exchange is accessed from Kaggle [here](https://www.kaggle.com/mczielinski/bitcoin-historical-data). Download the CSV file and put into the `data/` folder.

## Environment

### Windows only currently
Create the `conda` environment using from the root of the cloned project:

```bash
$ conda env create
```

Install `TA-Lib` python bindings by visiting: 
https://www.lfd.uci.edu/~gohlke/pythonlibs/

Download File: TA_Lib‑0.4.19‑cp38‑cp38‑win_amd64.whl

Then:
```bash
$ conda activate bitcoin
$ pip install TA_Lib‑0.4.19‑cp38‑cp38‑win_amd64.whl
```

