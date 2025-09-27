# HDL Pool Tracker

ELO Tracker for pool games

## Getting started

### Setup virtual environment

Create a virtual enviroment for dev (at project root) and activate

Windows:

```bash
  py -m venv .venv
  .venv\Scripts\activate.bat
```

Linux/MacOS:

```bash
  python -m venv .venv
  source .venv/bin/activate
```
Note: If Tkinter does not work properly on MacOS use the helper script `macos_install_python_tk.sh` to reinstall python with an updated version of Tk

### Install dependencies

Use pip to install dependencies listed in requirements.txt

```bash
  pip install -r requirements.txt
```

### Running the code

Use the virtual environment to run `main.py`

```bash
  python main.py
```

If no database file is created, a blank one will automatically be created

## Building the binary

To build the app for windows, use the helper scipt `build_win.bat`

A main.exe binary will be generated inside the dist folder
