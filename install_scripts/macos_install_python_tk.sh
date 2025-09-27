#!/bin/bash
set -e

# 1. Install/upgrade Homebrew Tcl/Tk
echo "Installing/upgrading Tcl/Tk via Homebrew..."
brew install tcl-tk || brew upgrade tcl-tk

# 2. Get the Homebrew path
TCLTK_PREFIX=$(brew --prefix tcl-tk)
echo "Homebrew Tcl/Tk path: $TCLTK_PREFIX"

# 3. Export environment variables so Python build uses Homebrew Tcl/Tk
export PATH="$TCLTK_PREFIX/bin:$PATH"
export LDFLAGS="-L$TCLTK_PREFIX/lib"
export CPPFLAGS="-I$TCLTK_PREFIX/include"
export PKG_CONFIG_PATH="$TCLTK_PREFIX/lib/pkgconfig"

# 4. Update pyenv and install latest Python
echo "Updating pyenv..."
brew install pyenv || brew upgrade pyenv

LATEST_PYTHON=$(pyenv install --list | grep -E '^\s*[0-9]+\.[0-9]+\.[0-9]+$' | tail -1 | tr -d ' ')
echo "Latest Python version: $LATEST_PYTHON"

echo "Installing Python $LATEST_PYTHON with Tk support..."
env PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I$TCLTK_PREFIX/include' --with-tcltk-libs='-L$TCLTK_PREFIX/lib -ltcl8.6 -ltk8.6'" \
    pyenv install -s $LATEST_PYTHON

pyenv global $LATEST_PYTHON
echo "Python version set to $(python3 --version)"

# 5. Verify Tkinter is using the correct Tcl/Tk version
echo "Verifying Tkinter Tcl/Tk version..."
python3 - <<END
import tkinter
root = tkinter.Tk()
print("Tk version:", root.tk.call("info", "patchlevel"))
root.destroy()
END

echo "✅ Python and Tkinter are ready!"

